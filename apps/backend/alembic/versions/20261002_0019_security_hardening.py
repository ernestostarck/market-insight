"""security hardening: user profile/roles/MFA/lockout, sessions and audit log

Revision ID: 20261002_0019
Revises: 20260921_0018
Create Date: 2026-10-02

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261002_0019"
down_revision = "20260921_0018"
branch_labels = None
depends_on = None

_SCHEMA = "security"


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="analyst"))
    op.add_column(
        "users",
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_ip", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_check_constraint("ck_users_role", "users", "role IN ('admin', 'analyst')")
    # Accounts that exist before this migration were created by the platform owner:
    # they become administrators so someone can manage users once public sign-up closes.
    op.execute("UPDATE users SET role = 'admin'")

    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("previous_token_hash", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(64), nullable=True),
        schema=_SCHEMA,
    )
    op.create_index("ix_security_user_sessions_user_id", "user_sessions", ["user_id"], schema=_SCHEMA)
    op.create_index(
        "ix_security_user_sessions_previous_token_hash", "user_sessions", ["previous_token_hash"], schema=_SCHEMA
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        schema=_SCHEMA,
    )
    op.create_index("ix_security_audit_log_created_at", "audit_log", ["created_at"], schema=_SCHEMA)
    op.create_index("ix_security_audit_log_event", "audit_log", ["event"], schema=_SCHEMA)
    op.create_index("ix_security_audit_log_user_id", "audit_log", ["user_id"], schema=_SCHEMA)
    op.create_index("ix_security_audit_log_ip_address", "audit_log", ["ip_address"], schema=_SCHEMA)

    # Least privilege for the application role: it can manage sessions, but can only
    # read and append to the audit trail — never rewrite or delete it.
    op.execute(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO market_insight_app, market_insight_admin")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {_SCHEMA}.user_sessions TO market_insight_app")
    op.execute(f"GRANT SELECT, INSERT ON {_SCHEMA}.audit_log TO market_insight_app")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {_SCHEMA} TO market_insight_app")
    op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {_SCHEMA} TO market_insight_admin")

    # Tamper resistance: the audit trail is append-only, even for someone holding the
    # application's database credentials.
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_SCHEMA}.audit_log_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'security.audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON {_SCHEMA}.audit_log
        FOR EACH ROW EXECUTE FUNCTION {_SCHEMA}.audit_log_append_only();
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS audit_log_no_update_delete ON {_SCHEMA}.audit_log")
    op.execute(f"DROP FUNCTION IF EXISTS {_SCHEMA}.audit_log_append_only()")
    op.drop_table("audit_log", schema=_SCHEMA)
    op.drop_table("user_sessions", schema=_SCHEMA)
    op.drop_constraint("ck_users_role", "users", type_="check")
    for column in (
        "mfa_enabled",
        "mfa_secret_encrypted",
        "password_changed_at",
        "last_login_ip",
        "last_login_at",
        "locked_until",
        "failed_login_attempts",
        "token_version",
        "preferences",
        "role",
        "job_title",
        "full_name",
    ):
        op.drop_column("users", column)
