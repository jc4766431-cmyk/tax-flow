import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class StaffRead(BaseModel):
    """Row shape for GET /users (firm staff listing). Deliberately narrower
    than auth.py's UserRead (no firm_id/is_email_verified/two_factor_enabled)
    since this is a team-roster view, not an auth-flow response — firm_id is
    already implied by the query's own firm_id param, and the 2FA/verification
    fields aren't relevant to a staff table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
