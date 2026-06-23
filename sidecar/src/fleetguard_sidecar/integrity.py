"""Local integrity checks — detect policy/config drift and tampering."""

import hashlib
import json
from pathlib import Path

from fleetguard_sidecar.config import SidecarConfig, FLEETGUARD_DIR


def compute_file_hash(path: Path) -> str | None:
    """Compute SHA-256 hash of a file."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_integrity(cfg: SidecarConfig) -> list[dict]:
    """Run integrity checks and return a list of findings."""
    findings = []

    # Check config file integrity
    config_hash = compute_file_hash(FLEETGUARD_DIR / "config.json")
    if config_hash:
        # Store hash if not present, or compare
        hash_file = FLEETGUARD_DIR / ".config.hash"
        if hash_file.exists():
            expected = hash_file.read_text().strip()
            if config_hash != expected:
                findings.append({
                    "type": "policy_drift_detected",
                    "detail": "Config file hash mismatch — possible tampering",
                    "severity": "high",
                })
        else:
            hash_file.write_text(config_hash)

    # Check policy cache integrity
    policy_path = FLEETGUARD_DIR / "policy-cache.json"
    if policy_path.exists():
        policy_hash = compute_file_hash(policy_path)
        hash_file = FLEETGUARD_DIR / ".policy.hash"
        if hash_file.exists():
            expected = hash_file.read_text().strip()
            if policy_hash != expected:
                findings.append({
                    "type": "local_integrity_warning",
                    "detail": "Policy cache hash mismatch — possible tampering",
                    "severity": "critical",
                })
        elif policy_hash:
            hash_file.write_text(policy_hash)

    # Check sidecar binary integrity
    sidecar_dir = Path(__file__).parent
    for py_file in sidecar_dir.glob("*.py"):
        py_hash = hashlib.sha256(py_file.read_bytes()).hexdigest()
        hash_file = FLEETGUARD_DIR / f".{py_file.name}.hash"
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
