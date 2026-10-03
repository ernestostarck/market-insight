import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import desc, select

from app.core.openapi import AUTH_ERROR_RESPONSES
from app.core.security import password_policy_errors
from app.core.settings import get_settings
from app.db.dependencies import get_auth_service, get_current_user
from app.models.user import SecurityAuditLog
from app.models.user import User as UserModel
from app.schemas.user import (
    AuditEventRead,
    LoginResponse,
    MfaCode,
    MfaDisable,
    MfaSetupResponse,
    MfaVerify,
    PasswordChange,
    PasswordPolicyCheck,
    ProfileUpdate,
    SessionRead,
    UserPreferences,
    UserProfile,
)
from app.services import security_audit as audit
from app.services.auth import AuthService, IssuedSession, MfaChallenge

router = APIRouter()

REFRESH_COOKIE = "mi_refresh"


def _set_refresh_cookie(response: Response, issued: IssuedSession) -> None:
    settings = get_settings()
    # httpOnly: unreachable from JavaScript (XSS can't steal it); SameSite=Strict + the
    # narrow path keep it off every request except the auth endpoints themselves.
    response.set_cookie(
        REFRESH_COOKIE,
        issued.refresh_token,
        max_age=settings.session_max_hours * 3600,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path=f"{settings.api_v1_prefix}/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(REFRESH_COOKIE, path=f"{settings.api_v1_prefix}/auth")


def _session_response(response: Response, issued: IssuedSession) -> LoginResponse:
    _set_refresh_cookie(response, issued)
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(
        access_token=issued.access_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post(
    "/register",
    status_code=status.HTTP_403_FORBIDDEN,
    summary="Public sign-up (disabled)",
    description="Public registration is closed: accounts are created by an administrator "
    "through `POST /admin/users`.",
    include_in_schema=False,
)
async def register() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="El registro público está deshabilitado. Pide una cuenta a un administrador.",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in",
    description=(
        "OAuth2 password form (`username` = email, `password`). Returns a 15-minute access "
        "token and sets an httpOnly refresh cookie, or `mfa_required` + `mfa_token` when the "
        "account has MFA enabled. Repeated failures lock the account with exponential backoff."
    ),
    responses={401: {"description": "Incorrect email or password."}, 423: {"description": "Account locked."}},
)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    result = await auth_service.authenticate(form_data.username, form_data.password, request)
    if isinstance(result, MfaChallenge):
        response.headers["Cache-Control"] = "no-store"
        return LoginResponse(mfa_required=True, mfa_token=result.mfa_token)
    return _session_response(response, result)


@router.post("/mfa/verify", response_model=LoginResponse, summary="Complete an MFA login")
async def mfa_verify(
    payload: MfaVerify,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    issued = await auth_service.verify_mfa_challenge(payload.mfa_token, payload.code, request)
    return _session_response(response, issued)


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Rotate the refresh cookie and get a new access token",
    description="Each refresh token works once; replaying an already-rotated one revokes "
    "every session of the account (stolen-token detection).",
)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE),
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse | JSONResponse:
    try:
        issued = await auth_service.refresh(refresh_token, request)
    except HTTPException as exc:
        # Raising would discard the cookie deletion: build the error response ourselves.
        error = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
        _clear_refresh_cookie(error)
        return error
    return _session_response(response, issued)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out this device")
async def logout(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    session_id = getattr(request.state, "session_id", None)
    if session_id:
        await auth_service.revoke_session(session_id, user_id=current_user.id, reason="logout")
    await audit.record(audit.LOGOUT, request=request, user_id=current_user.id, email=current_user.email)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out every device")
async def logout_all(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.revoke_all_sessions(current_user.id, reason="logout_all")
    await audit.record(audit.LOGOUT_ALL, request=request, user_id=current_user.id, email=current_user.email)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


# -- Profile ----------------------------------------------------------------------------

@router.get("/me", response_model=UserProfile, summary="Get the current user", responses=AUTH_ERROR_RESPONSES)
async def read_current_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    return current_user


@router.patch("/me", response_model=UserProfile, summary="Update my profile")
async def update_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(current_user, field, value.strip() if isinstance(value, str) else value)
    await auth_service.session.commit()
    await auth_service.session.refresh(current_user)
    await audit.record(
        audit.PROFILE_UPDATED, request=request, user_id=current_user.id, email=current_user.email,
        detail={"fields": sorted(changes)},
    )
    return current_user


@router.put("/me/preferences", response_model=UserProfile, summary="Replace my preferences")
async def update_preferences(
    payload: UserPreferences,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel:
    current_user.preferences = payload.model_dump()
    await auth_service.session.commit()
    await auth_service.session.refresh(current_user)
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Change my password")
async def change_password(
    payload: PasswordChange,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.change_password(
        current_user,
        payload.current_password,
        payload.new_password,
        request,
        keep_session=getattr(request.state, "session_id", None),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-policy", summary="Check a candidate password against the policy")
async def check_password_policy(
    payload: PasswordPolicyCheck, current_user: UserModel = Depends(get_current_user)
) -> dict[str, list[str]]:
    return {"errors": password_policy_errors(payload.password, email=current_user.email)}


# -- MFA --------------------------------------------------------------------------------

@router.post("/me/mfa/setup", response_model=MfaSetupResponse, summary="Start MFA enrolment")
async def mfa_setup(
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> MfaSetupResponse:
    secret, uri = await auth_service.start_mfa_setup(current_user)
    return MfaSetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/me/mfa/enable", response_model=UserProfile, summary="Confirm MFA with a first code")
async def mfa_enable(
    payload: MfaCode,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel:
    await auth_service.enable_mfa(current_user, payload.code, request)
    return current_user


@router.post("/me/mfa/disable", response_model=UserProfile, summary="Turn MFA off")
async def mfa_disable(
    payload: MfaDisable,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel:
    await auth_service.disable_mfa(current_user, payload.password, payload.code, request)
    return current_user


# -- Sessions & activity ----------------------------------------------------------------

@router.get("/me/sessions", response_model=list[SessionRead], summary="My signed-in devices")
async def my_sessions(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[SessionRead]:
    current_id = getattr(request.state, "session_id", None)
    return [
        SessionRead.model_validate(s).model_copy(update={"current": s.id == current_id})
        for s in await auth_service.active_sessions(current_user.id)
    ]


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out a device")
async def revoke_my_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    if not await auth_service.revoke_session(session_id, user_id=current_user.id, reason="revoked_by_user"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada.")
    await audit.record(
        audit.SESSION_REVOKED, request=request, user_id=current_user.id, email=current_user.email,
        detail={"session_id": str(session_id)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/activity", response_model=list[AuditEventRead], summary="My recent security activity")
async def my_activity(
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[SecurityAuditLog]:
    result = await auth_service.session.execute(
        select(SecurityAuditLog)
        .where(SecurityAuditLog.user_id == current_user.id)
        .order_by(desc(SecurityAuditLog.created_at))
        .limit(30)
    )
    return list(result.scalars().all())
