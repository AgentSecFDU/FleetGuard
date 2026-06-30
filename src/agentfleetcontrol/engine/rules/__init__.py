"""Risk detection rules registry."""

from agentfleetcontrol.engine.base import RiskRule
from agentfleetcontrol.engine.rules.dangerous_shell import DangerousShellRule
from agentfleetcontrol.engine.rules.sensitive_path import SensitivePathRule
from agentfleetcontrol.engine.rules.exfiltration import ExfiltrationRule
from agentfleetcontrol.engine.rules.prompt_injection import PromptInjectionRule
from agentfleetcontrol.engine.rules.persistence import PersistenceRule


def get_all_rules() -> list[RiskRule]:
    """Return all default risk detection rules."""
    return [
        DangerousShellRule(),
        SensitivePathRule(),
        ExfiltrationRule(),
        PromptInjectionRule(),
        PersistenceRule(),
    ]
