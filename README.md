# Indoor Routing and Localization System

This project is part of my engineering internship at Universitat Oberta de Catalunya supervised by Dr.Perrez-Navarro. It aims to develop an indoor navigation system using QR codes and smartphone sensor data.

## 🔍 Project Overview

The goal is to:
- Generate QR codes for each office (rooms 201 to 225).
- Stick these QR codes on doors to identify room positions.
- When a user scans a QR code, a web page opens indicating:
  - The current location (room scanned).
  - A list of destination rooms.
  - (In future versions) a route to the destination.

At this first stage, we focus on:
- Sending an email when a QR is scanned.
- Including available smartphone data (magnetometer, WiFi signal) in the email.
- Formatting this data following the IPIN competition format.

## 📁 Project Structure

project/
│
├── qrcodes/
│   ├── room_201.png
│   ├── room_202.png
│   ├── ...
│   └── room_225.png
│
├── qr_generator/
│   └── generate_qr.py
│
├── web/
│   ├── app.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       └── script.js
│
├── scripts/
│   ├── send_email.py
│   └── collect_sensor_data.py
│
├── data/
│   └── sensor_data.json
│
├── main.py
├── .gitignore
├── README.md
└── requirements.txt


