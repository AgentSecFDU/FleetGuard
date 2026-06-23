"""Indirect prompt injection detection rule."""

import re
from fleetguard.engine.base import RiskContext, RiskVerdict, RiskRule

INJECTION_PATTERNS = [
    (re.compile(r"ignore\s+previous\s+instructions?", re.IGNORECASE), "ignore previous instructions"),
    (re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.IGNORECASE), "reveal system prompt"),
    (re.compile(r"send\s+(your\s+)?secrets?", re.IGNORECASE), "send secrets"),
    (re.compile(r"read\s+local\s+files?", re.IGNORECASE), "read local files"),
    (re.compile(r"install\s+this\s+plugin", re.IGNORECASE), "install this plugin"),
    (re.compile(r"run\s+this\s+command", re.IGNORECASE), "run this command"),
    (re.compile(r"exfiltrate", re.IGNORECASE), "exfiltrate"),
    (re.compile(r"do\s+not\s+tell\s+the\s+user", re.IGNORECASE), "do not tell the user"),
    (re.compile(r"bypass\s+policy", re.IGNORECASE), "bypass policy"),
    (re.compile(r"disable\s+safety", re.IGNORECASE), "disable safety"),
    (re.compile(r"override\s+developer\s+instruction", re.IGNORECASE), "override developer instruction"),
    (re.compile(r"forget\s+(everything|all|your)", re.IGNORECASE), "forget everything"),
    (re.compile(r"you\s+are\s+now\s+DAN", re.IGNORECASE), "DAN jailbreak"),
    (re.compile(r"pretend\s+you\s+are", re.IGNORECASE), "pretend you are"),
    (re.compile(r"new\s+instructions?:", re.IGNORECASE), "new instructions"),
]


class PromptInjectionRule(RiskRule):
    name = "prompt_injection"
    description = "Scans for indirect prompt injection patterns in untrusted input"

    async def evaluate(self, ctx: RiskContext) -> RiskVerdict:
        # Only check when input provenance is untrusted
        if not ctx.input_provenance or "untrusted" not in ctx.input_provenance:
            return RiskVerdict()

        text_to_scan = ctx.params_summary or ""
        if ctx.params_redacted:
            text_to_scan += " " + " ".join(str(v) for v in ctx.params_redacted.values())

        score = 0
        labels = ["prompt_injection_suspected"]
        reasons = []

        for pattern, reason in INJECTION_PATTERNS:
            if pattern.search(text_to_scan):
                score += 30
                reasons.append(f"Injection pattern detected: {reason}")

        if score > 0:
            return RiskVerdict(score=min(score, 100), labels=labels, reasons=reasons)
        return RiskVerdict()
