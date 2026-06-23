"""Risk detection rules registry."""

from fleetguard.engine.base import RiskRule
from fleetguard.engine.rules.dangerous_shell import DangerousShellRule
from fleetguard.engine.rules.sensitive_path import SensitivePathRule
from fleetguard.engine.rules.exfiltration import ExfiltrationRule
from fleetguard.engine.rules.prompt_injection import PromptInjectionRule
from fleetguard.engine.rules.persistence import PersistenceRule


def get_all_rules() -> list[RiskRule]:
    """Return all default risk detection rules."""
    return [
        DangerousShellRule(),
        SensitivePathRule(),
        ExfiltrationRule(),
        PromptInjectionRule(),
        PersistenceRule(),
    ]
