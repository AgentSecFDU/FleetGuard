"""Data exfiltration detection rule."""

import re
from fleetguard.engine.base import RiskContext, RiskVerdict, RiskRule

# Known temporary file sharing / pastebin services
EXFIL_DOMAINS = [
    "pastebin.com", "paste.ee", "ghostbin.com", "hastebin.com",
    "termbin.com", "ix.io", "sprunge.us", "clbin.com",
    "transfer.sh", "file.io", "gist.github.com",
    "webhook.site", "requestbin.com", "hookbin.com",
    "discord.com/api/webhooks", "hooks.slack.com",
    "api.telegram.org", "ntfy.sh",
]


class ExfiltrationRule(RiskRule):
    name = "exfiltration"
    description = "Detects potential data exfiltration to external destinations"

    async def evaluate(self, ctx: RiskContext) -> RiskVerdict:
        score = 0
        labels = []
        reasons = []

        is_external = (
            ctx.tool_category in ("network", "message", "browser")
        )

        if not is_external:
            return RiskVerdict()

        # Base score for any external communication
        score += 30
        labels.append("external_communication")

        # Check for known exfiltration domains
        params_str = ctx.params_summary or ""
        if ctx.params_redacted:
            params_str += " " + " ".join(str(v) for v in ctx.params_redacted.values())

        for domain in EXFIL_DOMAINS:
            if domain in params_str.lower():
                score += 40
                labels.append("potential_exfiltration")
                reasons.append(f"Data sent to known file-sharing service: {domain}")
                break

        # If untrusted input preceded external communication
        if ctx.input_provenance and "untrusted" in ctx.input_provenance:
            score += 30
            labels.append("untrusted_to_external")
            reasons.append("External communication after untrusted input")

        # Check for email sending
        if re.search(r"(send|email|mailto|smtp)", params_str, re.IGNORECASE):
            score += 20
            labels.append("email_send")
            reasons.append("Email sending detected")

        return RiskVerdict(score=min(score, 100), labels=labels, reasons=reasons)
