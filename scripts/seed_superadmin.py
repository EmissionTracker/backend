"""Bootstrap script: promote an existing Cognito user to super-admin.

Usage:
    uv run python scripts/seed_superadmin.py <cognito_sub> <email>

Run this once after the first deployment to create the initial super-admin.
The user must already exist in Cognito.  This script inserts a row into the
users table with is_superadmin=True and no company_id requirement.

Because super-admins are not tied to a company, we use a sentinel NULL
company_id — but the users table has company_id NOT NULL.  To work around
this, the script inserts directly and temporarily bypasses the constraint
by creating a "platform" company that owns super-admin accounts.
"""

import asyncio
import selectors
import sys
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.tenant import Company, User

PLATFORM_COMPANY_SLUG = "__platform__"
PLATFORM_COMPANY_NAME = "Platform (internal)"


async def seed(cognito_sub: str, email: str) -> None:
    async with AsyncSessionLocal() as db:
        # Get or create the internal platform company
        result = await db.execute(
            select(Company).where(Company.slug == PLATFORM_COMPANY_SLUG)
        )
        platform = result.scalar_one_or_none()
        if platform is None:
            platform = Company(
                id=uuid.uuid4(),
                name=PLATFORM_COMPANY_NAME,
                slug=PLATFORM_COMPANY_SLUG,
            )
            db.add(platform)
            await db.flush()

        # Check if user already exists
        result = await db.execute(
            select(User).where(User.cognito_sub == cognito_sub)
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.is_superadmin:
                print(f"User {email} is already a super-admin.")
            else:
                existing.is_superadmin = True
                await db.commit()
                print(f"User {email} promoted to super-admin.")
            return

        user = User(
            id=uuid.uuid4(),
            cognito_sub=cognito_sub,
            email=email,
            company_id=platform.id,
            is_superadmin=True,
        )
        db.add(user)
        await db.commit()
        print(f"Super-admin created: {email} (sub={cognito_sub})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: uv run python scripts/seed_superadmin.py <cognito_sub> <email>")
        sys.exit(1)

    asyncio.run(seed(sys.argv[1], sys.argv[2]))
