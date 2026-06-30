"""Policy evaluator: compiles YAML policy into actionable rules and evaluates events."""

import re
from agentfleetcontrol.engine.base import RiskContext
from agentfleetcontrol.utils.yaml_parser import parse_policy_yaml, PolicyDefinition


class PolicyEvaluator:
    """Compiles and evaluates a YAML policy against event contexts."""

    def __init__(self, yaml_content: str):
        self.policy: PolicyDefinition = parse_policy_yaml(yaml_content)
        self._compile_rules()

    def _compile_rules(self):
        """Pre-compile regex patterns from policy rules for fast matching."""
        self._compiled: list[dict] = []
        for rule in self.policy.rules:
            when = rule.when
            if not when:
                continue
            compiled = {
                "id": rule.id,
                "action": rule.action,
                "severity": rule.severity,
                "event_type": when.event_type,
                "tool_categories": (
                    [when.tool_category] if isinstance(when.tool_category, str)
                    else when.tool_category
                ) if when.tool_category else None,
                "input_provenance": when.input_provenance,
                "command_patterns": [
                    re.compile(p, re.IGNORECASE) for p in (when.command_matches or [])
                ],
                "path_patterns": [
                    re.compile(p.replace("**", ".*").replace("*", "[^/]*"), re.IGNORECASE)
                    for p in (when.path_matches or [])
                ],
                "destination_trust": when.destination_trust,
            }
            self._compiled.append(compiled)

    def evaluate(self, ctx: RiskContext) -> dict:
        """Evaluate event context against policy rules.

        Returns:
            {"action": "allow"|"block"|"require_approval"|"quarantine_session"|"quarantine_device",
             "matched_rule": str|None, "reason": str}
        """
        # Check lockdown mode
        if hasattr(ctx, 'device_is_quarantined') and ctx.device_is_quarantined:
            if ctx.tool_category in ("shell", "network", "message", "browser", "plugin"):
                return {
                    "action": "block",
                    "matched_rule": "lockdown",
                    "reason": "Device is quarantined — high-risk tools blocked",
                }

        for rule in self._compiled:
            # Check event_type
            if rule["event_type"] and rule["event_type"] != ctx.event_type:
                continue

            # Check tool_category
            if rule["tool_categories"] and ctx.tool_category not in rule["tool_categories"]:
                continue

            # Check input_provenance
            if rule["input_provenance"] and rule["input_provenance"] != ctx.input_provenance:
                continue

            # Check command patterns
            if rule["command_patterns"]:
                cmd = ctx.params_summary or ""
                if ctx.params_redacted and "command" in ctx.params_redacted:
                    cmd = str(ctx.params_redacted.get("command", cmd))
                matched = False
                for pattern in rule["command_patterns"]:
                    if pattern.search(cmd):
                        matched = True
                        break
                if not matched:
                    continue

            # Check path patterns
            if rule["path_patterns"]:
                path = ctx.params_summary or ""
                if ctx.params_redacted:
                    path += " " + " ".join(str(v) for v in ctx.params_redacted.values())
                matched = False
                for pattern in rule["path_patterns"]:
                    if pattern.search(path):
                        matched = True
                        break
                if not matched:
                    continue

            # Rule matched!
            return {
                "action": rule["action"],
                "matched_rule": rule["id"],
                "reason": f"Matched policy rule: {rule['id']}",
            }

        # Default action
        return {
            "action": self.policy.default_action,
            "matched_rule": None,
            "reason": "Default policy action",
        }
