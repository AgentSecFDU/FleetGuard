"""Persistence and configuration tampering detection rule."""

from fleetguard.engine.base import RiskContext, RiskVerdict, RiskRule


PERSISTENCE_EVENT_TYPES = {
    "memory_updated",
    "config_changed",
    "skill_added",
    "plugin_added",
    "before_install",
}

PERSISTENCE_PATHS = [
    "AGENTS.md", "CLAUDE.md", "config.json", "config.yaml",
    ".bashrc", ".zshrc", ".profile", ".bash_profile",
    "crontab", "launchd", "systemd",
    "startup", "autorun",
]


class PersistenceRule(RiskRule):
    name = "persistence"
    description = "Detects persistence attempts via memory, config, plugin, or startup modifications"

    async def evaluate(self, ctx: RiskContext) -> RiskVerdict:
        score = 0
        labels = []
        reasons = []

        # Direct persistence events
        if ctx.event_type in PERSISTENCE_EVENT_TYPES:
            score += 30
            labels.append("persistence_attempt")
            reasons.append(f"Persistence-related event: {ctx.event_type}")

            # Plugin/skill install is higher risk
            if ctx.event_type in ("skill_added", "plugin_added", "before_install"):
                score += 20
                labels.append("untrusted_install")
                reasons.append("Plugin or skill installation detected")

        # Check for persistence-related file paths
        params_str = ctx.params_summary or ""
        if ctx.params_redacted:
            params_str += " " + " ".join(str(v) for v in ctx.params_redacted.values())

        for path in PERSISTENCE_PATHS:
            if path.lower() in params_str.lower():
                score += 20
                labels.append("config_tampering")
                reasons.append(f"Persistence file referenced: {path}")
                break

        # If persistence attempt comes from untrusted input, escalate
        if ctx.input_provenance and "untrusted" in ctx.input_provenance and score > 0:
            score += 20
            reasons.append("Persistence attempt triggered by untrusted input")

        return RiskVerdict(score=min(score, 100), labels=labels, reasons=reasons)
