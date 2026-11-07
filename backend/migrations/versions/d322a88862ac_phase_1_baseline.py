"""phase 1 baseline — identity, sessions, API keys, credentials, audit, usage

Revision ID: d322a88862ac
Revises:

Notes:
* Timestamps are stored as naive UTC by ``app.db.types.TZDateTime``; the DDL type is a plain
  ``DATETIME`` so this revision is portable across PostgreSQL and SQLite.
* ``render_as_batch=True`` is enabled for SQLite in ``migrations/env.py``; on PostgreSQL the
  batch blocks execute inline.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd322a88862ac'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=True),
    sa.Column('actor_email', sa.String(length=320), nullable=False),
    sa.Column('actor_type', sa.String(length=32), nullable=False),
    sa.Column('action', sa.String(length=80), nullable=False),
    sa.Column('outcome', sa.String(length=32), nullable=False),
    sa.Column('resource_type', sa.String(length=80), nullable=False),
    sa.Column('resource_id', sa.String(length=64), nullable=False),
    sa.Column('ip_address', sa.String(length=64), nullable=False),
    sa.Column('user_agent', sa.String(length=512), nullable=False),
    sa.Column('request_id', sa.String(length=64), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_actor_id'), ['actor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)

    op.create_table('roles',
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('is_system', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles'))
    )
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_roles_name'), ['name'], unique=True)

    op.create_table('usage_events',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('api_key_id', sa.String(length=36), nullable=True),
    sa.Column('conversation_id', sa.String(length=36), nullable=True),
    sa.Column('agent_id', sa.String(length=36), nullable=True),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('model', sa.String(length=120), nullable=False),
    sa.Column('operation', sa.String(length=64), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('total_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_usd', sa.Float(), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('error_code', sa.String(length=64), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usage_events'))
    )
    with op.batch_alter_table('usage_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_usage_events_conversation_id'), ['conversation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_usage_events_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_usage_events_model'), ['model'], unique=False)
        batch_op.create_index(batch_op.f('ix_usage_events_provider'), ['provider'], unique=False)
        batch_op.create_index(batch_op.f('ix_usage_events_user_id'), ['user_id'], unique=False)

    op.create_table('users',
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=512), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_superuser', sa.Boolean(), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.Column('failed_login_count', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(), nullable=True),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('api_keys',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('prefix', sa.String(length=16), nullable=False),
    sa.Column('hashed_key', sa.String(length=128), nullable=False),
    sa.Column('scopes', sa.JSON(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('last_used_at', sa.DateTime(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_api_keys_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_keys')),
    sa.UniqueConstraint('hashed_key', name=op.f('uq_api_keys_hashed_key'))
    )
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_api_keys_prefix'), ['prefix'], unique=False)
        batch_op.create_index(batch_op.f('ix_api_keys_user_id'), ['user_id'], unique=False)

    op.create_table('provider_credentials',
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('encrypted_value', sa.Text(), nullable=False),
    sa.Column('masked_value', sa.String(length=64), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_verified_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_provider_credentials_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_credentials'))
    )
    with op.batch_alter_table('provider_credentials', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_provider_credentials_provider'), ['provider'], unique=False)
        batch_op.create_index(batch_op.f('ix_provider_credentials_user_id'), ['user_id'], unique=False)

    op.create_table('refresh_tokens',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('family_id', sa.String(length=36), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('replaced_by', sa.String(length=36), nullable=True),
    sa.Column('used', sa.Boolean(), nullable=False),
    sa.Column('user_agent', sa.String(length=512), nullable=False),
    sa.Column('ip_address', sa.String(length=64), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens'))
    )
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_refresh_tokens_family_id'), ['family_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_refresh_tokens_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_refresh_tokens_user_id'), ['user_id'], unique=False)

    op.create_table('user_roles',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('role_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles'))
    )


def downgrade() -> None:
    op.drop_table('user_roles')
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_token_hash'))
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_family_id'))

    op.drop_table('refresh_tokens')
    with op.batch_alter_table('provider_credentials', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_provider_credentials_user_id'))
        batch_op.drop_index(batch_op.f('ix_provider_credentials_provider'))

    op.drop_table('provider_credentials')
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_api_keys_user_id'))
        batch_op.drop_index(batch_op.f('ix_api_keys_prefix'))

    op.drop_table('api_keys')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    with op.batch_alter_table('usage_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usage_events_user_id'))
        batch_op.drop_index(batch_op.f('ix_usage_events_provider'))
        batch_op.drop_index(batch_op.f('ix_usage_events_model'))
        batch_op.drop_index(batch_op.f('ix_usage_events_created_at'))
        batch_op.drop_index(batch_op.f('ix_usage_events_conversation_id'))

    op.drop_table('usage_events')
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_roles_name'))

    op.drop_table('roles')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_actor_id'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_action'))

    op.drop_table('audit_logs')
