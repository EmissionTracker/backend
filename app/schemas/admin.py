import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


# --- Request schemas ---

class CreateCompanyRequest(BaseModel):
    name: str
    slug: str  # URL-safe, e.g. "acme-corp"


class ProvisionUserRequest(BaseModel):
    cognito_sub: str
    email: EmailStr


# --- Response schemas ---

class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    cognito_sub: str
    company_id: uuid.UUID
    is_active: bool
    is_superadmin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
