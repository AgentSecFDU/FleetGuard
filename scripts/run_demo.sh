#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# FleetGuard Demo — Full Stack Launch Script
# ────────────────────────────────────────────────────────────────────
# Starts:
#   1. PostgreSQL + Redis + FleetGuard API (Docker)
#   2. 3 simulated devices (local processes)
#   3. Frontend dev server (optional)
# ────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       FleetGuard Demo — Full Stack Launch        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Start Docker services ──────────────────────────────────
echo -e "${YELLOW}[1/4] Starting Docker services (PostgreSQL + Redis + API)...${NC}"
docker compose up -d --build postgres redis api

echo -e "${GREEN}  ✓ Docker services started${NC}"
echo ""

# ── Step 2: Wait for API to be ready ───────────────────────────────
echo -e "${YELLOW}[2/4] Waiting for API to be ready...${NC}"
for i in $(seq 1 60); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ API is ready!${NC}"
        break
    fi
    sleep 2
done
echo ""

# ── Step 3: Seed database (ships with Docker CMD, but ensure) ──────
echo -e "${YELLOW}[3/4] Verifying seed data...${NC}"
# The API Dockerfile already runs seed on startup. Let's verify.
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$ADMIN_TOKEN" ]; then
    echo -e "${GREEN}  ✓ Admin login verified${NC}"
else
    echo -e "${YELLOW}  ⚠ Could not verify admin login, continuing anyway...${NC}"
fi
echo ""

# ── Step 4: Launch 3 device simulators ─────────────────────────────
echo -e "${YELLOW}[4/4] Starting 3 device simulators...${NC}"
echo -e "  ${CYAN}Press Ctrl+C to stop all simulators${NC}"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping all simulators...${NC}"
    kill $PID1 $PID2 $PID3 2>/dev/null || true
    wait $PID1 $PID2 $PID3 2>/dev/null || true
    echo -e "${GREEN}Demo stopped. Docker services still running.${NC}"
    echo -e "  To stop Docker: ${CYAN}docker compose down${NC}"
}
trap cleanup EXIT INT TERM

# Launch 3 simulators in background
uv run python scripts/simulate_device.py \
    --device-id "fg-dev-alice-001" \
    --hostname "alice-macbook" \
    --username "alice" \
    --os "macOS" \
    --api-url "http://localhost:8000" \
    --heartbeat-interval 10 \
    --event-interval 15 &
PID1=$!

sleep 3

uv run python scripts/simulate_device.py \
    --device-id "fg-dev-bob-001" \
    --hostname "bob-thinkpad" \
    --username "bob" \
    --os "Linux" \
    --api-url "http://localhost:8000" \
    --heartbeat-interval 10 \
    --event-interval 15 &
PID2=$!

sleep 3

uv run python scripts/simulate_device.py \
    --device-id "fg-dev-carol-001" \
    --hostname "carol-desktop" \
    --username "carol" \
    --os "Windows" \
    --api-url "http://localhost:8000" \
    --heartbeat-interval 10 \
    --event-interval 15 &
PID3=$!

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ FleetGuard Demo is running!                  ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  API Docs:  http://localhost:8000/docs           ║${NC}"
echo -e "${GREEN}║  Dashboard: http://localhost:8000/docs           ║${NC}"
echo -e "${GREEN}║  Admin:     admin / admin123                     ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  3 devices simulating:                           ║${NC}"
echo -e "${GREEN}║    • fg-dev-alice-001 (alice-macbook, macOS)     ║${NC}"
echo -e "${GREEN}║    • fg-dev-bob-001   (bob-thinkpad, Linux)      ║${NC}"
echo -e "${GREEN}║    • fg-dev-carol-001 (carol-desktop, Windows)   ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Frontend:  cd frontend && npm run dev           ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# Wait for simulators
wait $PID1 $PID2 $PID3
