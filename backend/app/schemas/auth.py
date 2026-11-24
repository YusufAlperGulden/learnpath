"""Authentication and user session Pydantic v2 schemas (FR01)."""

import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.enums import UserRole

_LOCAL_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]+)*\.local$")


def _validate_account_email(value: str) -> str:
    cleaned = value.strip()
    if "@" not in cleaned:
        raise ValueError("Invalid email address format.")
    local_part, domain_part = cleaned.rsplit("@", 1)
    lower_domain = domain_part.lower()

    # Permit RFC-6762 '.local' seeded demo/campus accounts while enforcing RFC local-part syntax
    if lower_domain.endswith(".local"):
        if not _LOCAL_DOMAIN_RE.match(lower_domain):
            raise ValueError("Invalid .local domain name.")
        try:
            checked = validate_email(f"{local_part}@example.org", check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError(str(exc)) from exc
        return f"{checked.local_part.lower()}@{lower_domain}"

    try:
        checked = validate_email(cleaned, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return checked.normalized.lower()


AccountEmail = Annotated[str, Field(min_length=3, max_length=254), AfterValidator(_validate_account_email)]


class RegisterRequest(BaseModel):
    email: AccountEmail
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: AccountEmail
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: AccountEmail
    role: UserRole
    has_profile: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
