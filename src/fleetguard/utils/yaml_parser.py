"""YAML policy parsing and validation utilities."""

import yaml
from pydantic import BaseModel, ValidationError
from typing import Optional


class PolicyRuleWhen(BaseModel):
    event_type: Optional[str] = None
    tool_category: Optional[str | list[str]] = None
    command_matches: Optional[list[str]] = None
    path_matches: Optional[list[str]] = None
    input_provenance: Optional[str] = None
    destination_trust: Optional[str] = None
    data_sensitivity: Optional[list[str]] = None
    source_not_in: Optional[list[str]] = None


class PolicyRule(BaseModel):
    id: str
    description: Optional[str] = None
    when: Optional[PolicyRuleWhen] = None
    action: str  # allow, log, redact, block, require_approval, quarantine_session, quarantine_device
    severity: Optional[str] = None  # low, medium, high, critical


class PolicyScope(BaseModel):
    devices: list[str] = []
    users: list[str] = []
    groups: list[str] = []


class PolicyDefinition(BaseModel):
    policy_id: str
    version: int = 1
    name: str = ""
    description: Optional[str] = None
    updated_at: Optional[str] = None
    default_action: str = "allow"
    allow: list[str] = []
    deny: list[str] = []
    rules: list[PolicyRule] = []
    scope: Optional[PolicyScope] = None


def parse_policy_yaml(yaml_str: str) -> PolicyDefinition:
    """Parse a YAML policy string into a validated PolicyDefinition."""
    data = yaml.safe_load(yaml_str)
    if data is None:
        raise ValueError("Empty YAML document")
    return PolicyDefinition(**data)


def validate_policy_yaml(yaml_str: str) -> list[str]:
    """Validate a YAML policy string. Returns list of error messages (empty = valid)."""
    try:
        parse_policy_yaml(yaml_str)
        return []
    except (yaml.YAMLError, ValidationError, ValueError) as e:
        return [str(e)]


def dump_policy_yaml(policy: PolicyDefinition) -> str:
    """Serialize a PolicyDefinition back to YAML string."""
    return yaml.safe_dump(policy.model_dump(), default_flow_style=False, sort_keys=False)
