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
->data/ # Collected sensor and location data
->qrcode/ # Folder containing generated QR codes
->scripts/ # Python scripts (QR generation, email sending)
->web/ # Webpage that opens after scanning a QR code
->README.md # This file