"""Administrator-only endpoints: user management and the security audit trail."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select

from app.core.security import get_password_hash, password_policy_errors
from app.db.dependencies import get_auth_service, require_admin
from app.models.user import SecurityAuditLog, User
from app.schemas.common import OffsetPage
from app.schemas.user import AdminUserCreate, AdminUserRead, AdminUserUpdate, AuditEventRead
from app.services import security_audit as audit
from app.services.auth import AuthService

router = APIRouter()


@router.get("/users", response_model=list[AdminUserRead], summary="List user accounts")
async def list_users(
    _admin: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[User]:
    result = await auth_service.session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@router.post(
    "/users",
    response_model=AdminUserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account",
    description="The only way to create accounts: public sign-up is disabled.",
)
async def create_user(
    payload: AdminUserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    email = payload.email.strip().lower()
    exists = await auth_service.session.scalar(select(User.id).where(func.lower(User.email) == email))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una cuenta con ese correo.")
    errors = password_policy_errors(payload.password, email=email)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"password": errors})
    user = User(
        email=email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        job_title=payload.job_title,
        role=payload.role,
        password_changed_at=datetime.now().astimezone(),
    )
    auth_service.session.add(user)
    await auth_service.session.commit()
    await auth_service.session.refresh(user)
    await audit.record(
        audit.USER_CREATED, request=request, user_id=admin.id, email=admin.email,
        detail={"target": email, "role": payload.role},
    )
    return user


@router.patch("/users/{user_id}", response_model=AdminUserRead, summary="Update a user account")
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    user = await auth_service.session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    changes = payload.model_dump(exclude_unset=True)
    if user.id == admin.id and (changes.get("role") == "analyst" or changes.get("is_active") is False):
        # Prevents locking the platform out of its last administrator by accident.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.",
        )

    for field in ("full_name", "job_title", "role", "is_active"):
        if field in changes:
            setattr(user, field, changes[field])
    if changes.get("unlock"):
        user.failed_login_attempts = 0
        user.locked_until = None
    if changes.get("reset_mfa"):
        user.mfa_enabled = False
        user.mfa_secret_encrypted = None
    await auth_service.session.commit()
    if changes.get("revoke_sessions") or changes.get("is_active") is False or "role" in changes:
        await auth_service.revoke_all_sessions(user.id, reason="admin_action")
    await auth_service.session.refresh(user)
    await audit.record(
        audit.USER_UPDATED, request=request, user_id=admin.id, email=admin.email,
        detail={"target": user.email, "changes": sorted(changes)},
    )
    return user


@router.get("/audit", response_model=OffsetPage[AuditEventRead], summary="Security audit trail")
async def audit_log(
    _admin: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event: str | None = Query(None, max_length=64),
    success: bool | None = Query(None),
    q: str | None = Query(None, max_length=200, description="Email or IP contains."),
) -> OffsetPage[AuditEventRead]:
    statement = select(SecurityAuditLog)
    if event:
        statement = statement.where(SecurityAuditLog.event == event)
    if success is not None:
        statement = statement.where(SecurityAuditLog.success.is_(success))
    if q:
        pattern = f"%{q.strip().replace('%', '').replace('_', '')}%"
        statement = statement.where(
            SecurityAuditLog.actor_email.ilike(pattern) | SecurityAuditLog.ip_address.ilike(pattern)
        )
    total = await auth_service.session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = await auth_service.session.execute(
        statement.order_by(desc(SecurityAuditLog.created_at)).offset(offset).limit(limit)
    )
    return OffsetPage(
        data=[AuditEventRead.model_validate(r) for r in rows.scalars().all()],
        total=total or 0,
        offset=offset,
        limit=limit,
    )
