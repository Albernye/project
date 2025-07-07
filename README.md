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
```
project/
├── app_mobile/                  # Mobile application (React Native / Flutter)
│   ├── src/
│   │   ├── components/
│   │   ├── screens/
│   │   ├── services/            # HTTP client for API endpoints
│   │   └── App.{js,dart}        # entrypoint
│   └── package.json / pubspec.yaml
│
├── qr_generator/                # QR code generation module
│   └── generate_qr.py
│
├── web/                         # Flask web application & static UI
│   ├── app.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── script.js            # JS sensor collection
│       └── leaflet.js           # Map & routing display
│
├── scripts/                     # Backend utility & integration scripts
│   ├── __init__.py
│   ├── collect_sensor_data.py   # saves raw data, organizes into data/raw/<room>/
│   ├── send_email.py            # email via SMTP / Mailtrap
│   ├── geolocate.py             # kNN fingerprint + PDR fusion
│   └── import_sensor_data.py    # convert CSV recordings into JSON stats
│
├── data/
│   ├── raw/                     # raw recordings per room
│   │   └── door_<room>/
│   │       └── recording_<i>.csv
│   ├── stats/                   # aggregated baseline JSON per room
│   │   └── room_<room>.json
│   └── live.json                # real-time collected sensor_data.json (array)
│
├── legacy_tools/                # external PDR & fingerprinting toolbox
│   ├── Txttocsv.py            # convert raw .txt files to CSV for fingerprint and IMU
│   ├── addCol.py             # format fingerprint CSV: unify AP columns, fill missing with -100
│   ├── kNN.py                # k‑Nearest Neighbors algorithm (training/testing, returns stats or positions)
│   ├── k-means.py            # k‑Means clustering variant for fingerprint data
│   ├── PDR.py                 # Pedestrian Dead Reckoning from IMU CSV (step/heading calc)
│   ├── Kalmanfilter.py       # Fuse PDR and kNN fingerprinting via Kalman filter
│   └── finalAlgo.py          # Final positioning algorithm: dual kNN for XY and floor (Z)

## 🛠️ Roadmap / Next Steps

**Relier PDR offline à la géolocalisation**
- Écrire un module `import_sensor_data.py` qui pour chaque parcours CSV calcule la trace PDR via `PDR.py`.
- Comparer la trace PDR à la ligne centrale (corridor) et générer un fichier GeoJSON pour QGIS.
- Charger automatiquement dans QGIS la trace PDR et le plan d’étage pour visualiser décalage vs couloir.

**Activer le Wi‑Fi fingerprinting**
- Dans **app_mobile**, implémenter un scan Wi‑Fi natif (SSID + RSSI) et l’inclure dans `/collect_sensor_data`.
- Adapter `geolocate.py` pour agréger et comparer les RSSI (moyenne, écart‑type) dans le kNN de fingerprint.

**Implémenter la fusion PDR ↔ Fingerprinting**
- En simulation, forcer une dérive PDR > 2 m et déclencher recalage par kNN Wi‑Fi.
- Ajouter un scénario de “nouveau scan QR” pour actualiser la position de référence utilisateur.
- Mettre à jour `geolocate.py` pour fusionner PDR et fingerprint via filtrage (ex : KalmanFilter).

**Feedback & test terrain**
- Scanner un QR dans le bâtiment test pour valider le workflow `/location` et collecte.
- Vérifier sur mobile le rendu carte/routes avec Leaflet et le recalage en cas de dérive.

**Déploiement**
- Dockeriser l’application Flask + CI/CD GitHub Actions.
- Héberger API (Heroku/Railway/VM UOC) et sécuriser HTTPS (ngrok en dev → prod).

---

*Avance rapide : l'objectif pour les 2 prochaines semaines est de boucler ce POC mobile + collecte + PDR + fingerprinting + routing.*
