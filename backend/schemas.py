"""Pydantic request/response models shared by backend modules.

Currently holds the authentication models. Transaction / KPI / simulation models will be added
here later (agree on field names with the frontend first).
"""
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(raw: str) -> str:
    """Trim, lower-case and validate an email address. Raises ValueError if it is not valid."""
    email = raw.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address.")
    return email


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)  # not trimmed: spaces may be part of a password
    remember: bool = False

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        return normalize_email(value)
