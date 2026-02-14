# Import all models here so Alembic can detect them for autogenerate
from app.models.tenant import (  # noqa: F401
    Company,
    User,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
