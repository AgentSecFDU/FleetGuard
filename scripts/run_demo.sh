#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# Agentfleetcontrol Full Stack Demo
# ────────────────────────────────────────────────────────────────────
# Launches:
#   Docker: PostgreSQL + Redis + API + 3 Sidecars
#   Local:  Frontend dev server (optional)
# ────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Agentfleetcontrol — Full Stack Demo Launch          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Start Docker services ──────────────────────────────────
echo -e "${YELLOW}[1/2] Starting all Docker services...${NC}"
echo "  • PostgreSQL + Redis + Control Center API"
echo "  • 3 Sidecars (alice-macbook, bob-thinkpad, carol-desktop)"
echo ""
docker compose up -d --build
echo ""

# ── Step 2: Wait for API ───────────────────────────────────────────
echo -e "${YELLOW}[2/2] Waiting for API to be ready...${NC}"
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ API is ready!${NC}"
        break
    fi
    sleep 3
done
echo ""

# ── Done ───────────────────────────────────────────────────────────
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Agentfleetcontrol Demo is running!                  ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  API Docs:  http://localhost:8000/docs           ║${NC}"
echo -e "${GREEN}║  Frontend:  cd frontend && npm run dev           ║${NC}"
echo -e "${GREEN}║            http://localhost:5173                  ║${NC}"
echo -e "${GREEN}║  Admin:     admin / admin123                     ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Sidecars:                                       ║${NC}"
echo -e "${GREEN}║    afc-sidecar-alice (alice-macbook)      ║${NC}"
echo -e "${GREEN}║    afc-sidecar-bob   (bob-thinkpad)       ║${NC}"
echo -e "${GREEN}║    afc-sidecar-carol (carol-desktop)      ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Stop:  docker compose down                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Show sidecar logs briefly
echo -e "${YELLOW}Checking sidecar connectivity...${NC}"
sleep 5
echo ""
curl -s http://localhost:8000/api/v1/devices/ \
    -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])' 2>/dev/null)" \
    | python3 -c "
import sys,json
data = json.load(sys.stdin)
devices = data.get('data', data) if isinstance(data, dict) else data
if isinstance(devices, list):
    print(f'  Devices online: {sum(1 for d in devices if d.get(\"status\")==\"online\")}/{len(devices)}')
    for d in devices:
        print(f'    {d[\"device_id\"]:20s} | {d[\"hostname\"]:20s} | {d[\"status\"]:10s} | sessions: {d[\"current_sessions\"]}')
" 2>/dev/null || echo "  (Waiting for devices to register...)"
