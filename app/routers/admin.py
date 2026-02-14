"""Super-admin endpoints — company and user provisioning.

All routes require the caller to be a provisioned super-admin user
(is_superadmin=True in the users table).  RLS is not activated for
these routes because super-admins operate across all tenants.
"""

import uuid

import boto3
import botocore.exceptions
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.dependencies import require_superadmin
from app.models.tenant import Company, User
from app.schemas.admin import (
    CompanyResponse,
    CreateCompanyRequest,
    ProvisionUserRequest,
    UserResponse,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_superadmin)],
)


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[Company]:
    """List all tenant companies."""
    result = await db.execute(select(Company).order_by(Company.name))
    return list(result.scalars().all())


@router.post(
    "/companies",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_company(
    body: CreateCompanyRequest,
    db: AsyncSession = Depends(get_db),
) -> Company:
    """Create a new tenant company."""

    # Check slug uniqueness
    existing = await db.execute(select(Company).where(Company.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A company with slug '{body.slug}' already exists.",
        )

    company = Company(id=uuid.uuid4(), name=body.name, slug=body.slug)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.post(
    "/companies/{company_id}/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_user(
    company_id: uuid.UUID,
    body: ProvisionUserRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Provision a Cognito user into a company.

    Links a Cognito sub + email to the given company so the user can
    authenticate and have RLS applied to their requests.
    """

    # Verify company exists
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found.",
        )

    # Verify the cognito_sub exists in Cognito
    cognito = boto3.client("cognito-idp", region_name=settings.cognito_region)
    try:
        cognito.admin_get_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=body.cognito_sub,
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "UserNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cognito user '{body.cognito_sub}' not found in user pool.",
            )
        raise

    # Check cognito_sub is not already provisioned
    existing = await db.execute(
        select(User).where(User.cognito_sub == body.cognito_sub)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with cognito_sub '{body.cognito_sub}' is already provisioned.",
        )

    user = User(
        id=uuid.uuid4(),
        cognito_sub=body.cognito_sub,
        email=body.email,
        company_id=company_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
