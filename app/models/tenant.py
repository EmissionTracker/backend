"""Core multi-tenancy models.

Hierarchy:
  Company  (one per customer organisation)
    ├── User          (linked to a Cognito sub)
    ├── Role          (named permission bundle, scoped to a company)
    │     └── RolePermission  (many-to-many)
    └── UserRole      (assigns roles to users within a company)

Permission names follow the pattern  "<resource>:<action>",
e.g. "settings:read", "emissions:write", "users:manage".
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # URL-safe identifier, e.g. "acme-corp"
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    users: Mapped[list["User"]] = relationship(back_populates="company")
    roles: Mapped[list["Role"]] = relationship(back_populates="company")


class User(TenantMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The 'sub' claim from the Cognito JWT — globally unique across all users.
    cognito_sub: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    company: Mapped["Company"] = relationship(back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")


class Permission(Base):
    """Global catalogue of permission strings.  Not scoped to a company."""

    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # e.g. "settings:read"
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission"
    )


class Role(TenantMixin, Base):
    """Named role scoped to a company.  Each company can define its own roles."""

    __tablename__ = "roles"
    __table_args__ = (
        # Role names must be unique within a company.
        UniqueConstraint("company_id", "name", name="uq_roles_company_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    company: Mapped["Company"] = relationship(back_populates="roles")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role")


class RolePermission(Base):
    """Many-to-many: which permissions a role grants."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")


class UserRole(TenantMixin, Base):
    """Assigns a role to a user within a company."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")
