import os
import sys
import sqlite3
import json
import time
import socket
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response, send_from_directory, make_response

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'tracker.db')

def get_local_ip():
    """Attempt to detect the primary local IP address of this machine."""
    # 1. Try socket connection
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass

    # 2. Try macOS specific interfaces (en0 = Wi-Fi usually)
    import subprocess
    for iface in ['en0', 'en1', 'wlan0', 'eth0']:
        try:
            out = subprocess.check_output(['ipconfig', 'getifaddr', iface], stderr=subprocess.DEVNULL).decode().strip()
            if out:
                return out
        except Exception:
            pass

    return '127.0.0.1'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journeys (
            id TEXT PRIMARY KEY,
            device_name TEXT,
            start_name TEXT,
            end_name TEXT,
            start_lat REAL,
            start_lng REAL,
            end_lat REAL,
            end_lng REAL,
            status TEXT DEFAULT 'active',
            alarm_triggered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_ping_at TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journey_id TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            accuracy REAL,
            speed REAL,
            altitude REAL,
            heading REAL,
            battery_level REAL,
            battery_charging INTEGER,
            network_type TEXT,
            is_offline_sync INTEGER DEFAULT 0,
            recorded_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (journey_id) REFERENCES journeys (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "short_name": "Tracker",
        "name": "Live Device GPS Tracker",
        "id": "/track",
        "start_url": "/track",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "type": "image/png",
                "sizes": "192x192",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icon-512.png",
                "type": "image/png",
                "sizes": "512x512",
                "purpose": "any maskable"
            }
        ]
    })

# ----------------- WEB PAGES -----------------

@app.route('/')
def index():
    local_ip = get_local_ip()
    port = request.environ.get('SERVER_PORT', 5050)
    protocol = request.scheme
    return render_template('dashboard.html', local_ip=local_ip, port=port, protocol=protocol)

@app.route('/track')
def track_universal():
    """Universal tracking endpoint: attaches to the latest active journey or creates one automatically."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM journeys WHERE status = 'active' ORDER BY created_at DESC LIMIT 1")
    journey = cursor.fetchone()

    if not journey:
        journey_id = f"journey-{int(time.time())}"
        cursor.execute('''
            INSERT INTO journeys (id, device_name, start_name, end_name, status)
            VALUES (?, 'My Mobile Phone', 'Start Point', 'Destination', 'active')
        ''', (journey_id,))
        conn.commit()
        cursor.execute("SELECT * FROM journeys WHERE id = ?", (journey_id,))
        journey = cursor.fetchone()

    conn.close()
    return render_template('tracker.html', journey=dict(journey))

@app.route('/track/<journey_id>')
def track_device(journey_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM journeys WHERE id = ?', (journey_id,))
    journey = cursor.fetchone()
    conn.close()

    if not journey:
        return "Journey not found", 404

    return render_template('tracker.html', journey=dict(journey))

# ----------------- API ENDPOINTS -----------------

@app.route('/api/server_info')
def server_info():
    local_ip = get_local_ip()
    port = request.environ.get('SERVER_PORT', 5050)
    proto = request.headers.get('X-Forwarded-Proto', request.scheme)
    host = request.host
    return jsonify({
        'local_ip': local_ip,
        'port': port,
        'host': host,
        'protocol': proto,
        'base_url': f"{proto}://{host}"
    })

@app.route('/api/journey/start', methods=['POST'])
def start_journey():
    data = request.json or {}
    device_name = data.get('device_name', 'My Mobile Phone')
    start_name = data.get('start_name', 'Start Point')
    end_name = data.get('end_name', 'Destination')
    start_lat = data.get('start_lat')
    start_lng = data.get('start_lng')
    end_lat = data.get('end_lat')
    end_lng = data.get('end_lng')

    journey_id = f"journey-{int(time.time())}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO journeys (id, device_name, start_name, end_name, start_lat, start_lng, end_lat, end_lng, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
    ''', (journey_id, device_name, start_name, end_name, start_lat, start_lng, end_lat, end_lng))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'journey_id': journey_id,
        'tracking_url': f"/track/{journey_id}"
    })

@app.route('/api/journey/<journey_id>')
def get_journey(journey_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM journeys WHERE id = ?', (journey_id,))
    journey = cursor.fetchone()

    if not journey:
        conn.close()
        return jsonify({'error': 'Journey not found'}), 404

    cursor.execute('''
        SELECT lat, lng, accuracy, speed, altitude, heading, battery_level, battery_charging,
               network_type, is_offline_sync, recorded_at, created_at
        FROM locations
        WHERE journey_id = ?
        ORDER BY id ASC
    ''', (journey_id,))
    locations = [dict(row) for row in cursor.fetchall()]
    conn.close()

    journey_dict = dict(journey)
    
    # Check if signal is lost (no ping in the last 40 seconds)
    signal_lost = False
    seconds_since_ping = None
    if locations:
        last_loc = locations[-1]
        try:
            # Parse recorded_at or created_at
            rec_str = last_loc.get('created_at')
            if rec_str:
                last_time = datetime.strptime(rec_str, '%Y-%m-%d %H:%M:%S')
                seconds_since_ping = int((datetime.utcnow() - last_time).total_seconds())
                if seconds_since_ping > 40:
                    signal_lost = True
        except Exception:
            pass

    return jsonify({
        'journey': journey_dict,
        'locations': locations,
        'last_known_location': locations[-1] if locations else None,
        'signal_lost': signal_lost,
        'seconds_since_ping': seconds_since_ping
    })

@app.route('/api/journey/latest')
def get_latest_journey():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM journeys ORDER BY created_at DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_journey(row['id'])
    return jsonify({'journey': None, 'locations': []})

@app.route('/api/ping', methods=['POST'])
def receive_ping():
    data = request.json or {}
    journey_id = data.get('journey_id')
    lat = data.get('lat')
    lng = data.get('lng')

    if not journey_id or lat is None or lng is None:
        return jsonify({'error': 'Missing journey_id or coordinates'}), 400

    accuracy = data.get('accuracy')
    speed = data.get('speed')
    altitude = data.get('altitude')
    heading = data.get('heading')
    battery_level = data.get('battery_level')
    battery_charging = 1 if data.get('battery_charging') else 0
    network_type = data.get('network_type', 'unknown')
    recorded_at = data.get('recorded_at') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO locations (journey_id, lat, lng, accuracy, speed, altitude, heading,
                               battery_level, battery_charging, network_type, is_offline_sync, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    ''', (journey_id, lat, lng, accuracy, speed, altitude, heading, battery_level, battery_charging, network_type, recorded_at))

    cursor.execute('UPDATE journeys SET last_ping_at = CURRENT_TIMESTAMP WHERE id = ?', (journey_id,))
    
    cursor.execute('SELECT alarm_triggered, status FROM journeys WHERE id = ?', (journey_id,))
    row = cursor.fetchone()
    alarm_triggered = bool(row[0]) if row else False
    status = row[1] if row else 'active'

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'alarm_triggered': alarm_triggered,
        'status': status
    })

@app.route('/api/sync_offline', methods=['POST'])
def sync_offline():
    """Bulk sync GPS coordinates that were saved offline on the phone when signal dropped."""
    data = request.json or {}
    journey_id = data.get('journey_id')
    pings = data.get('pings', [])

    if not journey_id or not pings:
        return jsonify({'error': 'No pings or missing journey_id'}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for p in pings:
        lat = p.get('lat')
        lng = p.get('lng')
        if lat is None or lng is None:
            continue
        accuracy = p.get('accuracy')
        speed = p.get('speed')
        altitude = p.get('altitude')
        heading = p.get('heading')
        battery_level = p.get('battery_level')
        battery_charging = 1 if p.get('battery_charging') else 0
        network_type = p.get('network_type', 'offline_cached')
        recorded_at = p.get('recorded_at') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO locations (journey_id, lat, lng, accuracy, speed, altitude, heading,
                                   battery_level, battery_charging, network_type, is_offline_sync, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ''', (journey_id, lat, lng, accuracy, speed, altitude, heading, battery_level, battery_charging, network_type, recorded_at))

    cursor.execute('UPDATE journeys SET last_ping_at = CURRENT_TIMESTAMP WHERE id = ?', (journey_id,))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'synced_count': len(pings)
    })

@app.route('/api/journey/<journey_id>/toggle_alarm', methods=['POST'])
def toggle_alarm(journey_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT alarm_triggered FROM journeys WHERE id = ?', (journey_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Journey not found'}), 404

    new_state = 0 if row[0] else 1
    cursor.execute('UPDATE journeys SET alarm_triggered = ? WHERE id = ?', (new_state, journey_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'alarm_triggered': bool(new_state)})

@app.route('/api/journey/<journey_id>/status', methods=['POST'])
def update_status(journey_id):
    data = request.json or {}
    new_status = data.get('status', 'active') # 'active', 'lost', 'completed'

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE journeys SET status = ? WHERE id = ?', (new_status, journey_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'status': new_status})

if __name__ == '__main__':
    # Try running with SSL if cert.pem and key.pem exist
    ssl_context = None
    cert_path = os.path.join(os.path.dirname(__file__), 'cert.pem')
    key_path = os.path.join(os.path.dirname(__file__), 'key.pem')

    port = int(os.environ.get('PORT', 5050))
    use_http = '--http' in sys.argv or os.environ.get('HTTP_MODE') == '1'

    if not use_http and os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)
        print(f"\n🚀 Running in SECURE HTTPS mode for Local Wi-Fi testing!")
        print(f"👉 Local Dashboard: https://localhost:{port}")
        print(f"👉 Real Phone Link: https://{get_local_ip()}:{port}\n")
    else:
        ssl_context = None
        print(f"\n🚀 Running in HTTP mode (Ideal for Public Tunnels / Pinggy / Localhost.run)!")
        print(f"👉 Local Dashboard: http://localhost:{port}")
        print(f"👉 Tunnel forwards this to a secure public https:// URL automatically!\n")

    app.run(host='0.0.0.0', port=port, debug=True, ssl_context=ssl_context)
