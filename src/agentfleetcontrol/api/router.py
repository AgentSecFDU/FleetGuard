from fastapi import APIRouter
from agentfleetcontrol.api.v1 import devices, events, policies, approvals, dashboard, auth, audit

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(policies.router, prefix="/policies", tags=["Policies"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
