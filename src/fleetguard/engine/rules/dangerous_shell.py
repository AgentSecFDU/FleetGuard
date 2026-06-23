"""Dangerous shell command detection rule."""

import re
from fleetguard.engine.base import RiskContext, RiskVerdict, RiskRule

# Patterns that indicate dangerous shell usage
DANGEROUS_PATTERNS = [
    (re.compile(r"curl\s+.*\|\s*(sh|bash|shell)", re.IGNORECASE), "remote_script_execution", "curl piped to shell"),
    (re.compile(r"wget\s+.*\|\s*(sh|bash|shell)", re.IGNORECASE), "remote_script_execution", "wget piped to shell"),
    (re.compile(r"rm\s+-rf\s+/", re.IGNORECASE), "dangerous_shell", "rm -rf / detected"),
    (re.compile(r"chmod\s+\+x\s+.*&&.*", re.IGNORECASE), "dangerous_shell", "chmod +x with chained execution"),
    (re.compile(r"bash\s+-c", re.IGNORECASE), "dangerous_shell", "bash -c execution"),
    (re.compile(r"python\s+-c", re.IGNORECASE), "dangerous_shell", "python -c execution"),
    (re.compile(r"nc\s+-e", re.IGNORECASE), "dangerous_shell", "netcat -e (reverse shell)"),
    (re.compile(r"crontab", re.IGNORECASE), "persistence_attempt", "crontab modification"),
    (re.compile(r"sudoers", re.IGNORECASE), "privilege_escalation", "sudoers access"),
    (re.compile(r"authorized_keys", re.IGNORECASE), "persistence_attempt", "SSH authorized_keys modification"),
    (re.compile(r"eval\s+", re.IGNORECASE), "dangerous_shell", "eval usage"),
    (re.compile(r"exec\s*\(.*\)", re.IGNORECASE), "dangerous_shell", "exec() call"),
]


class DangerousShellRule(RiskRule):
    name = "dangerous_shell"
    description = "Detects dangerous shell commands including remote script execution, privilege escalation, and persistence"

    async def evaluate(self, ctx: RiskContext) -> RiskVerdict:
        if ctx.tool_category != "shell":
            return RiskVerdict()

        command = ctx.params_summary or ""
        if ctx.params_redacted and "command" in ctx.params_redacted:
            command = str(ctx.params_redacted.get("command", command))

        score = 0
        labels = []
        reasons = []

        for pattern, label, reason in DANGEROUS_PATTERNS:
            if pattern.search(command):
                score += 60
                labels.append(label)
                reasons.append(reason)

        return RiskVerdict(score=min(score, 100), labels=labels, reasons=reasons)
