#!/usr/bin/env python3
"""DIVU AI operator CLI.

Usage (from ``backend/``)::

    python manage.py check-config
    python manage.py create-admin --email you@example.com --password 'Strong!Passphrase'
    python manage.py seed
    python manage.py db-upgrade
    python manage.py db-revision "add conversations"
    python manage.py run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from getpass import getpass

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.errors import ConflictError
from app.core.logging import configure_logging
from app.db.models.user import User
from app.db.session import create_engine, dispose_engine, get_engine, get_session_factory
from app.services.user_service import UserService

EXIT_OK = 0
EXIT_ERROR = 1


def _settings() -> Settings:
    return get_settings()


async def _bootstrap_schema(settings: Settings) -> None:
    """Ensure tables exist before user management commands (dev/CI convenience)."""
    from app.db.base import Base

    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def create_admin(email: str, password: str, full_name: str = "Administrator") -> int:
    settings = _settings()
    configure_logging(settings)
    await _bootstrap_schema(settings)

    factory = get_session_factory()
    async with factory() as session:
        service = UserService(session)
        existing = await service.get_by_email(email)
        if existing is not None:
            await service.set_roles(existing, ["admin"])
            await session.commit()
            print(f"User {email} already existed — granted the 'admin' role.")
            return EXIT_OK
        user = await service.create_user(email=email, password=password, full_name=full_name)
        await service.set_roles(user, ["admin"])
        await session.commit()
        print(f"Administrator created: {user.email} (id={user.id})")
    await dispose_engine()
    return EXIT_OK


async def promote(email: str) -> int:
    settings = _settings()
    configure_logging(settings)
    factory = get_session_factory()
    async with factory() as session:
        service = UserService(session)
        user = await service.get_by_email(email)
        if user is None:
            print(f"No such user: {email}", file=sys.stderr)
            return EXIT_ERROR
        await service.set_roles(user, ["admin"])
        await session.commit()
        print(f"{email} now has roles: {user.role_names}")
    await dispose_engine()
    return EXIT_OK


async def seed() -> int:
    """Create default roles and demo accounts. Development only."""
    settings = _settings()
    if settings.is_production:
        print("Refusing to seed a production database.", file=sys.stderr)
        return EXIT_ERROR
    configure_logging(settings)
    await _bootstrap_schema(settings)

    factory = get_session_factory()
    async with factory() as session:
        service = UserService(session)
        created_roles = await service.ensure_default_roles()
        print(f"Roles ensured ({len(created_roles)} newly created).")

        demo_email = os.environ.get("DIVU_SEED_EMAIL", "demo@divu.ai")
        demo_password = os.environ.get("DIVU_SEED_PASSWORD", "Demo!Passphrase1")
        user = await service.get_by_email(demo_email)
        if user is None:
            user = await service.create_user(
                email=demo_email, password=demo_password, full_name="Demo User"
            )
            print(f"Demo user created: {demo_email} / {demo_password}")
        else:
            print(f"Demo user already present: {demo_email}")
        await session.commit()

        users = (await session.execute(select(User))).scalars().all()
        print(f"Total users: {len(users)}")
    await dispose_engine()
    return EXIT_OK


def check_config() -> int:
    """Validate configuration and print a redacted summary."""
    try:
        settings = _settings()
    except Exception as exc:  # pydantic ValidationError and friends
        print(f"Configuration is invalid: {exc}", file=sys.stderr)
        return EXIT_ERROR

    problems: list[str] = []
    if settings.app_env in {"development", "test"} and not settings.secret_key:
        problems.append("secret_key is empty")
    if settings.is_production:
        if not settings.encryption_key:
            problems.append("encryption_key is required in production")
        if settings.allow_public_registration:
            problems.append("public registration must be disabled in production")
    if not settings.db_is_postgres and settings.app_env == "production":
        problems.append("production deployments must use PostgreSQL")

    print(f"DIVU AI configuration check — environment: {settings.app_env}")
    print(f"  database        : {'postgres' if settings.db_is_postgres else 'sqlite'}")
    print(f"  cache           : {settings.cache_backend}")
    print(f"  storage         : {settings.object_storage_backend}")
    print(f"  providers       : {', '.join(settings.configured_providers())}")
    print(f"  secret key      : {'set' if settings.secret_key else 'MISSING'}")
    print(f"  encryption key  : {'set' if settings.encryption_key else 'derived (dev only)'}")
    print(f"  rate limiting   : {'on' if settings.rate_limit_enabled else 'off'}")
    for problem in problems:
        print(f"  problem         : {problem}", file=sys.stderr)
    return EXIT_ERROR if problems else EXIT_OK


def alembic(*args: str) -> int:
    command = [sys.executable, "-m", "alembic", *args]
    completed = subprocess.run(command, check=False)
    return completed.returncode


def run_server(host: str, port: int, reload: bool) -> int:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        command.append("--reload")
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DIVU AI backend management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-config", help="validate configuration and print a summary").set_defaults(
        func=lambda args: check_config()
    )

    admin = subparsers.add_parser("create-admin", help="create an administrator account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", default=None, help="omit to be prompted securely")
    admin.add_argument("--full-name", default="Administrator")
    admin.set_defaults(
        func=lambda args: asyncio.run(
            create_admin(args.email, args.password or getpass("Password: "), args.full_name)
        )
    )

    promote_parser = subparsers.add_parser("promote", help="grant the admin role to a user")
    promote_parser.add_argument("--email", required=True)
    promote_parser.set_defaults(func=lambda args: asyncio.run(promote(args.email)))

    subparsers.add_parser("seed", help="create default roles and a demo user (dev only)").set_defaults(
        func=lambda args: asyncio.run(seed())
    )

    upgrade = subparsers.add_parser("db-upgrade", help="apply migrations")
    upgrade.add_argument("--revision", default="head")
    upgrade.set_defaults(func=lambda args: alembic("upgrade", args.revision))

    downgrade = subparsers.add_parser("db-downgrade", help="roll back migrations")
    downgrade.add_argument("--revision", default="-1")
    downgrade.set_defaults(func=lambda args: alembic("downgrade", args.revision))

    revision = subparsers.add_parser("db-revision", help="autogenerate a migration")
    revision.add_argument("message")
    revision.set_defaults(func=lambda args: alembic("revision", "--autogenerate", "-m", args.message))

    history = subparsers.add_parser("db-history", help="show migration history")
    history.set_defaults(func=lambda args: alembic("history"))

    current = subparsers.add_parser("db-current", help="show the current revision")
    current.set_defaults(func=lambda args: alembic("current"))

    run_parser = subparsers.add_parser("run", help="run the API server")
    run_parser.add_argument("--host", default="0.0.0.0")
    run_parser.add_argument("--port", type=int, default=8000)
    run_parser.add_argument("--reload", action="store_true")
    run_parser.set_defaults(func=lambda args: run_server(args.host, args.port, args.reload))

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ConflictError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
