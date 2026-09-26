#!/bin/sh
# Kill a dev backend left over from a previous `npm run dev` that didn't shut
# down, so it can't hold port 8000. Only touches this project's .venv processes.
venv="$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/"
for pid in $(lsof -t -iTCP:8000 -sTCP:LISTEN 2>/dev/null); do
  case "$(ps -o command= -p "$pid")" in
    *"$venv"*) echo "Stopping stale backend (pid $pid)"; kill -9 "$pid" ;;
  esac
done
pkill -9 -f "${venv}uvicorn backend.main:app" 2>/dev/null
exit 0
