"""Local HTTP API — called by the AgentFleetControl Plugin inside OpenClaw Gateway."""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from afc_sidecar.config import SidecarConfig
from afc_sidecar.event_queue import EventQueue
from afc_sidecar.policy_sync import PolicySyncer
from afc_sidecar.quarantine import QuarantineController


# ── Request schemas ────────────────────────────────────────────────

class EventRequest(BaseModel):
    event_type: str
    tool_name: str | None = None
    tool_category: str | None = None
    input_provenance: str | None = None
    params_summary: str | None = None
    params_redacted: dict | None = None
    session_id: str | None = None
    agent_id: str | None = None
    run_id: str | None = None
    risk_score: int = 0
    risk_labels: list[str] = []
    content_uploaded: bool = False


class ApprovalRequest(BaseModel):
    event_id: str
    tool_name: str
    params_summary: str
    risk_score: int
    risk_labels: list[str] = []
    reason: str
    session_id: str | None = None
    run_id: str | None = None


class QuarantineRequest(BaseModel):
    reason: str = "Quarantine requested"
    session_id: str | None = None


# ── Create FastAPI app ────────────────────────────────────────────

def create_local_api(
    cfg: SidecarConfig,
    event_queue: EventQueue,
    policy_syncer: PolicySyncer,
    quarantine_ctrl: QuarantineController,
) -> FastAPI:
    app = FastAPI(title="AgentFleetControl Sidecar Local API", version="0.1.0", docs_url=None, redoc_url=None)

    @app.get("/local/status")
    async def get_status():
        """Get local sidecar status."""
        return {
            "device_id": cfg.device_id,
            "hostname": cfg.hostname,
            "status": "quarantined" if cfg.quarantine else "online",
            "quarantine": cfg.quarantine,
            "policy_version": cfg.policy_version,
            "control_center_url": cfg.control_center_url,
            "control_center_reachable": True,  # For now
            "queue_size": event_queue.queue_size,
            "current_sessions": cfg.current_sessions,
            "active_agent_runs": cfg.active_agent_runs,
        }

    @app.get("/local/policy")
    async def get_policy():
        """Get the currently cached policy (for Plugin's policy engine)."""
        policy = policy_syncer.get_policy()
        if policy is None:
            # Try to sync now
            await policy_syncer.sync()
            policy = policy_syncer.get_policy()

        if policy is None:
            raise HTTPException(status_code=503, detail="No policy available (offline, no cache)")

        return policy

    @app.post("/local/events")
    async def submit_event(event: EventRequest):
        """Submit an event from the Plugin. Queued for batch upload."""
        # Check quarantine
        if event.tool_category and not quarantine_ctrl.is_tool_allowed(event.tool_category, event.session_id):
            return {
                "decision": "block",
                "reason": "Device or session is quarantined",
                "event_id": None,
            }

        # Queue the event
        evt = event.model_dump()
        evt["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        await event_queue.push(evt)

        # Evaluate against local policy
        policy = policy_syncer.get_policy()
        if policy:
            decision = _evaluate_policy(policy, evt)
        else:
            # Offline mode: default deny for high-risk
            decision = {"action": policy_syncer.get_default_action(), "reason": "Offline mode — default action"}

        return {
            "decision": decision["action"],
            "reason": decision.get("reason", ""),
            "event_id": evt.get("event_id"),
        }

    @app.post("/local/approval/request")
    async def request_approval(req: ApprovalRequest):
        """Create an approval request via Control Center."""
        import httpx
        import uuid

        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            async with httpx.AsyncClient(base_url=cfg.control_center_url, timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {cfg.device_token}"}
                resp = await client.post("/api/v1/approvals/", json={
                    "approval_id": approval_id,
                    "device_id": cfg.device_id,
                    "event_id": req.event_id,
                    "session_id": req.session_id,
                    "run_id": req.run_id,
                    "tool_name": req.tool_name,
                    "params_summary": req.params_summary,
                    "risk_score": req.risk_score,
                    "risk_labels": req.risk_labels,
                    "reason": req.reason,
                    "requested_at": now,
                }, headers=headers)
                resp.raise_for_status()
        except Exception:
            raise HTTPException(status_code=503, detail="Cannot reach Control Center to create approval")

        return {"approval_id": approval_id, "status": "pending"}

    @app.get("/local/approval/{approval_id}/wait")
    async def wait_approval(approval_id: str):
        """Long-poll for approval decision."""
        import httpx
        import asyncio

        for _ in range(24):  # 120 seconds max (24 × 5s)
            try:
                async with httpx.AsyncClient(base_url=cfg.control_center_url, timeout=5.0) as client:
                    resp = await client.get(f"/api/v1/approvals/{approval_id}/status")
                    resp.raise_for_status()
                    data = resp.json()

                status = data.get("status", "pending")
                if status != "pending":
                    return {"approval_id": approval_id, "status": status,
                            "decision_reason": data.get("decision_reason")}
            except Exception:
                pass
            await asyncio.sleep(5)

        return {"approval_id": approval_id, "status": "expired", "decision_reason": "Approval timed out"}

    @app.post("/local/quarantine/session")
    async def quarantine_session(req: QuarantineRequest):
        """Quarantine a specific session."""
        session_id = req.session_id or "default"
        status = quarantine_ctrl.quarantine_session(session_id, req.reason)
        return {"status": status, "session_id": session_id}

    @app.post("/local/quarantine/device")
    async def quarantine_device(req: QuarantineRequest):
        """Quarantine the entire device."""
        status = quarantine_ctrl.quarantine_device(req.reason)
        return {"status": status, "device_id": cfg.device_id}

    return app


# ── Policy evaluation helpers ──────────────────────────────────────

def _evaluate_policy(policy: dict, event: dict) -> dict:
    """Simple local policy evaluation against cached policy rules."""
    default_action = policy.get("default_action", "allow")
    rules = policy.get("rules", [])

    for rule in rules:
        when = rule.get("when", {})
        if not when:
            continue

        # Check event_type
        if when.get("event_type") and when["event_type"] != event.get("event_type"):
            continue

        # Check tool_category
        tc = when.get("tool_category")
        if tc:
            categories = [tc] if isinstance(tc, str) else tc
            if event.get("tool_category") not in categories:
                continue

        # Rule matched — return its action
        return {"action": rule.get("action", default_action), "reason": f"Matched rule: {rule.get('id')}"}

    return {"action": default_action, "reason": "Default policy action"}
