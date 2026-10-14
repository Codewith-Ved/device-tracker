#!/usr/bin/env bash
# Device Tracker Launcher
cd "$(dirname "$0")"

# Ensure SSL certificates exist (required by mobile browsers for GPS)
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "🔑 Generating self-signed SSL certificate for local mobile HTTPS..."
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost" 2>/dev/null
fi

echo "=========================================================="
echo "   🛰️ REAL DEVICE GPS TRACKER & RECOVERY SYSTEM"
echo "=========================================================="
echo ""
python3 app.py
