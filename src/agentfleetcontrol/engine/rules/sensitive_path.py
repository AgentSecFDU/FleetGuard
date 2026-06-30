"""Sensitive file path detection rule."""

import re
from agentfleetcontrol.engine.base import RiskContext, RiskVerdict, RiskRule

SENSITIVE_PATH_PATTERNS = [
    (re.compile(r"\.ssh/", re.IGNORECASE), "sensitive_path_access", "SSH directory access"),
    (re.compile(r"\.aws/", re.IGNORECASE), "sensitive_path_access", "AWS credentials access"),
    (re.compile(r"\.gcloud/", re.IGNORECASE), "sensitive_path_access", "GCP credentials access"),
    (re.compile(r"\.kube/", re.IGNORECASE), "sensitive_path_access", "Kubernetes config access"),
    (re.compile(r"credentials", re.IGNORECASE), "sensitive_path_access", "Credentials file access"),
    (re.compile(r"\.npmrc", re.IGNORECASE), "sensitive_path_access", "npmrc access"),
    (re.compile(r"\.pypirc", re.IGNORECASE), "sensitive_path_access", "PyPI config access"),
    (re.compile(r"\.env", re.IGNORECASE), "sensitive_path_access", ".env file access"),
    (re.compile(r"id_rsa|id_ed25519", re.IGNORECASE), "sensitive_path_access", "SSH private key access"),
    (re.compile(r"Cookies|Login Data", re.IGNORECASE), "sensitive_path_access", "Browser credential access"),
    (re.compile(r"\.config/.*credentials", re.IGNORECASE), "sensitive_path_access", "Config credentials access"),
    (re.compile(r"\.config/.*secret", re.IGNORECASE), "sensitive_path_access", "Config secret access"),
    (re.compile(r"/etc/passwd|/etc/shadow", re.IGNORECASE), "sensitive_path_access", "System auth file access"),
]


class SensitivePathRule(RiskRule):
    name = "sensitive_path"
    description = "Detects access to sensitive file paths (credentials, keys, browser data)"

    async def evaluate(self, ctx: RiskContext) -> RiskVerdict:
        # Only applies to file operations
        if ctx.tool_category not in ("file", "shell"):
            return RiskVerdict()

        path_to_check = ctx.params_summary or ""
        if ctx.params_redacted:
            for v in ctx.params_redacted.values():
                path_to_check += " " + str(v)

        score = 0
        labels = []
        reasons = []

        for pattern, label, reason in SENSITIVE_PATH_PATTERNS:
            if pattern.search(path_to_check):
                score += 40
                labels.append(label)
                reasons.append(reason)

        return RiskVerdict(score=min(score, 100), labels=labels, reasons=reasons)
