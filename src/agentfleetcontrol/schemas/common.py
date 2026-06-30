"""Shared Pydantic schemas: pagination, error responses."""

from pydantic import BaseModel
from typing import Any, Optional


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel):
    data: list[Any]
    pagination: dict


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
