#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.fusion-finance.pid"
HOST="${FUSION_FINANCE_HOST:-0.0.0.0}"
PORT="${FUSION_FINANCE_PORT:-11446}"
LOG_FILE="$SCRIPT_DIR/.fusion-finance.log"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Fusion-Finance already running (PID $(cat "$PID_FILE"))"
        return 0
    fi
    echo "Starting Fusion-Finance API on ${HOST}:${PORT}..."
    nohup python -m uvicorn fusion_finance.api.app:app \
        --host "$HOST" \
        --port "$PORT" \
        --log-level info \
        > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "✅ Fusion-Finance started (PID $(cat "$PID_FILE"))"
        echo "   API: http://${HOST}:${PORT}/docs"
    else
        echo "❌ Failed to start, check $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            sleep 2
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID"
            fi
            echo "✅ Fusion-Finance stopped (PID $PID)"
        else
            echo "Process $PID not running"
        fi
        rm -f "$PID_FILE"
    else
        echo "Fusion-Finance not running"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        PID=$(cat "$PID_FILE")
        echo "✅ Fusion-Finance running (PID $PID)"
        echo "   API: http://${HOST}:${PORT}/docs"
        curl -s "http://${HOST}:${PORT}/api/v1/ready" 2>/dev/null | python -m json.tool 2>/dev/null || echo "   (health check failed)"
    else
        echo "❌ Fusion-Finance not running"
    fi
}

log() {
    if [ -f "$LOG_FILE" ]; then
        if [ "${1:-}" = "-f" ]; then
            tail -f "$LOG_FILE"
        else
            tail -n 50 "$LOG_FILE"
        fi
    else
        echo "No log file found"
    fi
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  status ;;
    log)     log "${2:-}" ;;
    *)       echo "Usage: $0 {start|stop|restart|status|log [-f]}" ;;
esac
