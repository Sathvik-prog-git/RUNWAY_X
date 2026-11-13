"""Pydantic request/response models shared by backend modules.

Currently holds the authentication and registration models. Transaction / KPI / simulation models will be added
here later (agree on field names with the frontend first).
"""
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

import registration

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


class RegisterRequest(BaseModel):
    """Public company registration. `extra="forbid"`: any other field (role, company_id, is_admin …) is rejected with 422."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(max_length=200)
    email: str = Field(max_length=254)
    password: str = Field(max_length=1024)           # strength rules (incl. the 128 limit) are applied below
    confirm_password: str = Field(max_length=1024)
    company_name: str = Field(max_length=300)
    phone: str = Field(max_length=40)
    gstin: str | None = Field(default=None, max_length=40)

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, value: str) -> str:
        return registration.normalize_full_name(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str, info: ValidationInfo) -> str:
        problem = registration.check_password(value, info.data.get("email", ""), info.data.get("full_name", ""))
        if problem:
            raise ValueError(problem)
        return value

    @field_validator("confirm_password")
    @classmethod
    def _confirm(cls, value: str, info: ValidationInfo) -> str:
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("The two passwords do not match.")
        return value

    @field_validator("company_name")
    @classmethod
    def _company(cls, value: str) -> str:
        return registration.normalize_company_name(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return registration.normalize_indian_mobile(value)

    @field_validator("gstin")
    @classmethod
    def _gstin(cls, value: str | None) -> str | None:
        return registration.normalize_gstin(value)
