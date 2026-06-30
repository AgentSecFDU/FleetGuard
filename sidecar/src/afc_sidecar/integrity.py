"""Local integrity checks — detect sidecar code tampering."""

import hashlib
from pathlib import Path

from afc_sidecar.config import SidecarConfig, AFC_DIR


def check_integrity(cfg: SidecarConfig) -> list[dict]:
    """Run integrity checks and return a list of findings.

    Only checks sidecar .py source files — config.json and policy-cache.json
    legitimately change during normal operation (heartbeat, policy sync).
    """
    findings = []

    # Check sidecar source code integrity (these should never change at runtime)
    sidecar_dir = Path(__file__).parent
    for py_file in sidecar_dir.glob("*.py"):
        py_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()
        hash_file = AFC_DIR / f".{py_file.name}.hash"
        if hash_file.exists():
            expected = hash_file.read_text().strip()
            if py_hash != expected:
                findings.append({
                    "type": "local_integrity_warning",
                    "detail": f"Sidecar file {py_file.name} modified",
                    "severity": "critical",
                })
        else:
            hash_file.write_text(py_hash)

    return findings


async def run_integrity_checks(cfg: SidecarConfig, event_queue):
    """Run periodic integrity checks and report findings as events."""
    import asyncio
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        findings = check_integrity(cfg)
        for finding in findings:
            await event_queue.push({
                "event_type": finding["type"],
                "params_summary": finding["detail"],
                "risk_score": 80 if finding["severity"] == "critical" else 60,
                "risk_labels": [finding["type"]],
            })
