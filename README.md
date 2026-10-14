# 🛰️ Real Device Journey Tracker & Lost Phone Recovery

A full-stack, real-time GPS tracking system engineered specifically for **physical mobile device testing** (iPhone & Android) with **offline store-and-forward caching** and **lost device emergency recovery**.

---

## ⚡ Quick Start (1-Minute Setup)

1. Open Terminal in this folder and start the server:
   ```bash
   ./start.sh
   # or: python3 app.py
   ```

2. Open the **Dashboard** on your laptop:
   ```
   https://localhost:5050
   ```

3. Click **"🚀 Start Journey & Pair Real Phone"**.
4. Scan the **QR Code** with your physical smartphone (iPhone or Android camera) or copy the URL:
   ```
   https://<YOUR_MAC_IP>:5050/track/journey-xxxx
   ```

---

## 📱 Real Mobile Device Setup & Tips

### 1. SSL / HTTPS Security (Crucial for GPS)
Mobile browsers (Safari on iOS & Chrome on Android) **strictly require HTTPS** to access device hardware GPS (`navigator.geolocation`).
- The server automatically serves over HTTPS using a local certificate.
- When opening the link on your phone for the first time, your mobile browser will show a standard certificate notice:
  - **iOS Safari:** Tap *Show Details* ➔ *visit this website*.
  - **Android Chrome:** Tap *Advanced* ➔ *Proceed to site (unsafe)*.
  - Tap **"Allow Location Access"** when prompted.

### 2. Testing On-The-Go (When Leaving Home Wi-Fi)
If you are taking your phone out on a real journey (where the phone leaves your home Wi-Fi):
- **Option A (Phone's Mobile Hotspot):** Connect your Mac to your phone's Personal Hotspot before leaving. They will remain on the same network anywhere you travel!
- **Option B (Free Public Tunnel):** In a separate terminal tab on your Mac, run:
  ```bash
  ssh -R 80:localhost:5050 localhost.run
  ```
  This creates an instant public HTTPS URL (e.g. `https://random.lhr.life`) that you can open on your phone using 4G/5G mobile data from anywhere in the city!

---

## 🚀 Key Features

### 1. Hardware GPS Telemetry
- Reads real device coordinates, altitude, heading, and speed (in km/h).
- Monitors real phone battery percentage and charging state via `navigator.getBattery()`.
- Screen Wake Lock API ensures the screen stays active in your pocket or vehicle mount so background GPS polling continues without interruption.

### 2. Hybrid Offline "Store-and-Forward" Caching
- **When Online:** Pings are streamed live to the map every 2.5 seconds.
- **When Offline (Dead zones, tunnels, subway):** The mobile tracker automatically detects signal loss and buffers all GPS breadcrumbs with timestamps into `localStorage`.
- **When Reconnected:** The phone automatically syncs the entire queue to the server (`/api/sync_offline`), drawing a dashed orange "Recovered Offline Route" trail on the map!

### 3. Emergency "Lost Phone" Recovery
- **Automatic Disconnect Alert:** If the phone stops broadcasting pings for $> 40$ seconds, the dashboard turns RED and highlights the **Last Known Location**.
- **Remote Siren Alarm:** Tap "Trigger Remote Siren Alarm" on the laptop dashboard. The phone synthesizes a loud continuous emergency siren using Web Audio API and flashes a red alert screen.
- **One-Click Navigation:** Tap "Navigate in Google Maps" to get instant driving directions directly to where the phone was last seen on the road.
