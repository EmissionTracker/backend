"""FastAPI dependencies shared across routers."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.cognito import CurrentUser
from app.database import get_db
from app.models.tenant import User


async def get_tenant_db(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session with Row Level Security activated.

    Sets the PostgreSQL session variable ``app.current_company_id`` to the
    company that owns the authenticated user.  All RLS policies on tenant
    tables reference this variable, so every query in the request
    automatically sees only that company's rows.

    Raises 401 if the Cognito sub has no matching user record (i.e. the user
    was created in Cognito but has not yet been provisioned in the database).
    """
    cognito_sub = current_user.get("sub")
    result = await db.execute(select(User).where(User.cognito_sub == cognito_sub))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not provisioned. Contact your administrator.",
        )

    # SET LOCAL is scoped to the current transaction and is automatically
    # cleared when the session is returned to the pool.
    await db.execute(
        text("SET LOCAL app.current_company_id = :cid"),
        {"cid": str(user.company_id)},
    )

    yield db


TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]
