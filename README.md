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
├── qrcodes/ # generated QR codes (room_201.png … room_225.png)
├── data/ # collected sensor data (sensor_data.json)
├── qr_generator/ # QR code generation module
│ └── generate_qr.py
├── scripts/ # utility scripts
│ ├── init.py
│ ├── collect_sensor_data.py # collects data & sends email
│ └── send_email.py # email sending via Mailtrap / SMTP
├── web/ # Flask web application
│ ├── init.py
│ ├── app.py
│ ├── templates/
│ │ └── index.html # main page + form
│ └── static/
│ └── script.js # JS sensor collection & fetch
├── main.py # entry point (QR generation + Flask server)
├── config.py # .env parsing, paths, URLs
├── requirements.txt # pip dependencies
├── .env # environment variables (excluded from git)
└── .gitignore # ignores venv/, qrcodes/, data/, etc.


# 📝 TODO / Next Steps

- **Enable HTTPS for mobile sensors**  
  - Install and run **ngrok**:  
    ```bash
    ngrok http 5000
    ```  
  - Copy the generated HTTPS URL (e.g. `https://abcdef.ngrok.io`) into your `.env` as:  
    ```dotenv
    BASE_URL=https://abcdef.ngrok.io
    ```  
  - Regenerate your QR codes and re-test collection on iOS Safari.

- **Add indoor routing functionality**  
  1. Expose a new endpoint:  
     ```
     GET /route?from=<roomA>&to=<roomB>
     ```  
  2. Use pgRouting (`pgr_dijkstra` on your `indoor_lines` table) to compute the shortest path.  
  3. Integrate a map library (Leaflet or OpenLayers) into `index.html` to display the route.  


