---
title: Indoor Routing and Localization System
description: QR-code based hybrid indoor positioning using PDR and Wi-Fi fingerprinting
---

# Indoor Routing & Localization System

This project was developed during my engineering internship at the **Universitat Oberta de Catalunya**, under the supervision of **Dr. Pérez-Navarro**.  
It aims to provide a lightweight, mobile-friendly **indoor navigation system** based on **QR codes**, **IMU sensors (PDR)**, and **Wi‑Fi fingerprinting**.

<img src="diag.png" alt="System Architecture" style="max-width: 100%;">

---

##  Project Goals

- Generate **QR codes** for each room (201 to 225) to be placed at the door.
- Upon scanning a QR code:
  - Open a web page showing the **current location**.
  - Display a list of **available destinations**.
  - (Coming soon) Show the **path to the destination**.
- Continuously collect **mobile sensor data** (Wi‑Fi, magnetometer, accelerometer).
- Compute indoor location by combining:
  - **PDR** (Pedestrian Dead Reckoning).
  - **Wi‑Fi fingerprinting** (kNN with stats).
  - **Fusion filtering** (e.g., Kalman Filter).

---

##  Project Structure

```text
project/
├── algorithms/             # Core positioning logic
│   ├── pdr.py              # PDR trajectory from IMU
│   ├── fingerprint.py      # Wi‑Fi kNN positioning
│   ├── filters.py          # Fusion filters (e.g. Kalman)
│   └── fusion.py           # Combines QR, PDR, Wi‑Fi
│
├── qr_generator/           
│   └── generate_qr.py      # CLI for QR creation and parsing
│
├── web/                    
│   ├── app.py              # Flask backend and routing
│   ├── templates/          # HTML (Jinja2)
│   └── static/             # JS (sensor logic), CSS, Leaflet
│
├── scripts/                
│   ├── init_stats.py       # Generate Wi‑Fi baselines
│   ├── record_realtime.py  # Collect live sensor data
│   ├── geolocate.py        # CLI geolocation using fusion
│   ├── send_email.py       # Alert/reporting system
│   └── route.py            # GeoJSON + routing logic
│
├── data/
│   ├── raw/                # Raw Wi‑Fi/IMU recordings
│   ├── stats/              # Aggregated fingerprint baselines
│   └── recordings/         # Live session recordings
│
├── main.py                 # Entry point (e.g. test script)
├── diag.png                # System architecture diagram
├── config.py               # Environment and path setup
├── requirements.txt        # Python dependencies
├── Dockerfile              # For containerized deployment
├── .env                    # API keys and secrets
├── .gitignore
├── README.md
└── roadmap.txt             # Development checklist
