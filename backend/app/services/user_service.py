"""User and role management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.ids import new_id, utcnow
from app.db.models.user import Role, User, user_roles
from app.schemas.common import Page
from app.security.passwords import hash_password, validate_password_strength

DEFAULT_ROLES: dict[str, str] = {
    "admin": "Full platform administration, including security and add-on approval.",
    "developer": "Can create agents, tools, workflows and add-ons in the Developer Studio.",
    "user": "Standard end-user access to chat, research and personal memory.",
    "viewer": "Read-only access to shared workspaces.",
}


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---------------- Roles ----------------
    async def ensure_default_roles(self) -> list[Role]:
        """Create the built-in roles if they are missing. Idempotent."""
        created: list[Role] = []
        for name, description in DEFAULT_ROLES.items():
            role = (
                await self._session.execute(select(Role).where(Role.name == name))
            ).scalar_one_or_none()
            if role is None:
                role = Role(id=new_id(), name=name, description=description, is_system=True)
                self._session.add(role)
                created.append(role)
        if created:
            await self._session.flush()
        return created

    async def get_role(self, name: str) -> Role:
        role = (
            await self._session.execute(select(Role).where(Role.name == name))
        ).scalar_one_or_none()
        if role is None:
            raise NotFoundError(f"Role '{name}' does not exist.")
        return role

    async def list_roles(self) -> list[Role]:
        return list((await self._session.execute(select(Role).order_by(Role.name))).scalars().all())

    async def set_roles(self, user: User, role_names: list[str]) -> User:
        known = {role.name: role for role in await self.list_roles()}
        selected: list[Role] = []
        for name in role_names:
            if name not in known:
                raise ValidationFailedError(
                    f"Unknown role '{name}'.",
                    details={"known_roles": sorted(known)},
                )
            selected.append(known[name])
        # The association table is written directly: assigning to ``user.roles`` would trigger a
        # lazy load of the previous collection, which is not allowed in an async context.
        await self._session.execute(user_roles.delete().where(user_roles.c.user_id == user.id))
        for role in selected:
            await self._session.execute(
                user_roles.insert().values(user_id=user.id, role_id=role.id)
            )
        await self._session.flush()
        await self._session.refresh(user, attribute_names=["roles"])
        return user

    # ---------------- Users ----------------
    async def get_by_id(self, user_id: str) -> User:
        user = await self._session.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )
        return result.scalars().first()

    async def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str = "",
        role_names: list[str] | None = None,
        is_superuser: bool = False,
    ) -> User:
        email = email.strip().lower()
        if await self.get_by_email(email):
            raise ConflictError("An account with this email address already exists.")

        problems = validate_password_strength(password)
        if problems:
            raise ValidationFailedError(
                "The password does not meet the policy.", details={"problems": problems}
            )

        user = User(
            id=new_id(),
            email=email,
            full_name=full_name.strip(),
            hashed_password=hash_password(password),
            is_superuser=is_superuser,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self._session.add(user)
        await self._session.flush()

        await self.ensure_default_roles()
        names = role_names or (["admin"] if is_superuser else ["user"])
        await self.set_roles(user, names)
        return user

    async def list_users(
        self, *, page: int = 1, page_size: int = 50, query: str = ""
    ) -> Page[User]:
        statement = select(User)
        if query:
            pattern = f"%{query.lower()}%"
            statement = statement.where(
                func.lower(User.email).like(pattern) | func.lower(User.full_name).like(pattern)
            )
        total = (
            await self._session.execute(select(func.count()).select_from(statement.subquery()))
        ).scalar_one()
        rows = await self._session.execute(
            statement.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return Page[User](
            items=list(rows.scalars().unique().all()),
            page=page,
            page_size=page_size,
            total=int(total),
        )

    async def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = bool(is_active)
        self._session.add(user)
        await self._session.flush()
        return user

    async def delete_user(self, user: User) -> None:
        """Hard delete with explicit cascade of the association rows (FK-safe on SQLite)."""
        await self._session.execute(user_roles.delete().where(user_roles.c.user_id == user.id))
        await self._session.delete(user)
        await self._session.flush()
