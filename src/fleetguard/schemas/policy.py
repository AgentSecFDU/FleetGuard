"""Policy schemas."""

from pydantic import BaseModel
from typing import Optional


class PolicyCreate(BaseModel):
    policy_id: str
    name: str
    yaml_content: str


class PolicyUpdate(BaseModel):
    yaml_content: str


class PolicyRead(BaseModel):
    id: str
    policy_id: str
    name: str
    version: int
    yaml_content: str
    status: str
    created_by: Optional[str] = None
    published_at: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PolicyListResponse(BaseModel):
    data: list[PolicyRead]
    pagination: dict


class PolicyVersionRead(BaseModel):
    version: int
    status: str
    published_at: Optional[str] = None
    created_at: str


class PolicyPublishResponse(BaseModel):
    policy_id: str
    version: int
    status: str
    message: str
