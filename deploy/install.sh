#!/usr/bin/env bash
# Install the bot as a systemd service on a Linux VPS. Run from the cloned repo as root:
#   sudo bash deploy/install.sh
# Re-running is safe: it refreshes the venv, dependencies and unit file, then restarts.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_USER="${SERVICE_USER:-jobbot}"
SERVICE_NAME="${SERVICE_NAME:-jobbot}"
PYTHON="${PYTHON:-python3}"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo bash deploy/install.sh" >&2
    exit 1
fi

if ! command -v "$PYTHON" >/dev/null; then
    echo "$PYTHON not found. On Debian/Ubuntu: apt install python3 python3-venv" >&2
    exit 1
fi
if ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    echo "Python 3.10 or newer is required, found $("$PYTHON" --version)" >&2
    exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
    echo "No $APP_DIR/.env yet. Copy .env.example to .env and fill in the token and chat id." >&2
    exit 1
fi

echo "==> Python environment in $APP_DIR/.venv"
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    "$PYTHON" -m venv "$APP_DIR/.venv" || {
        echo "venv creation failed. On Debian/Ubuntu: apt install python3-venv" >&2; exit 1; }
fi
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Service user $SERVICE_USER"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> Checking the Telegram connection"
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/python" "$APP_DIR/bot.py" --test

# First run: mark today's listings as seen so the chat is not flooded. INIT=1 answers yes
# without asking (for non-interactive installs), INIT=0 skips it.
if [[ ! -f "$APP_DIR/seen.json" ]]; then
    answer="${INIT:-}"
    if [[ -z "$answer" && -t 0 ]]; then
        read -r -p "First run: mark today's listings as seen so you are not flooded? [Y/n] " answer
        answer="${answer:-y}"
    fi
    if [[ "$answer" =~ ^[Yy1] ]]; then
        echo "==> Marking current listings as seen"
        sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/python" "$APP_DIR/bot.py" --init
    fi
fi

echo "==> Installing /etc/systemd/system/$SERVICE_NAME.service"
sed -e "s|__APP_DIR__|$APP_DIR|g" -e "s|__USER__|$SERVICE_USER|g" \
    "$APP_DIR/deploy/jobbot.service" > "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo
echo "Done. Useful commands:"
echo "  systemctl status $SERVICE_NAME"
echo "  journalctl -u $SERVICE_NAME -f          # live log"
echo "  sudo systemctl restart $SERVICE_NAME    # after git pull or .env changes"
