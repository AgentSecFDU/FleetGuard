"""Risk engine base classes: Rule ABC, RiskContext, RiskVerdict, RuleRegistry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RiskContext:
    """All fields a risk rule might need to inspect."""
    event_type: str = ""
    tool_name: str | None = None
    tool_category: str | None = None
    input_provenance: str | None = None
    params_summary: str | None = None
    params_redacted: dict | None = None
    session_has_untrusted_input: bool = False
    session_has_quarantine: bool = False
    device_is_quarantined: bool = False


@dataclass
class RiskVerdict:
    """Result of a risk rule evaluation."""
    score: int = 0           # 0-100
    labels: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class RiskRule(ABC):
    """Abstract base class for risk detection rules."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def evaluate(self, ctx: RiskContext) -> RiskVerdict:
        """Evaluate the risk context and return a verdict.
        Return zero-score verdict if the rule doesn't match.
        """
        ...


class RuleRegistry:
    """Registry of risk rules that can be loaded and extended."""

    def __init__(self):
        self._rules: list[RiskRule] = []

    def register(self, rule: RiskRule) -> None:
        self._rules.append(rule)

    def register_all(self, rules: list[RiskRule]) -> None:
        self._rules.extend(rules)

    @property
    def rules(self) -> list[RiskRule]:
        return list(self._rules)
