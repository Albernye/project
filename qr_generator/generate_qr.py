import qrcode
import os

# Ensure the output directory exists
output_dir = "project/qrcodes"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Base URL to encode in the QR Code (adapt according to your project)
base_url = "https://98e7-84-79-64-75.ngrok-free.app/location?room="

# Generation of QR codes for offices 201 to 225
for room_number in range(201, 226):
    room_url = f"{base_url}{room_number}"
    qr = qrcode.make(room_url)

    # Output filename
    filename = os.path.join(output_dir, f"room_{room_number}.png")

    # Save the QR code
    qr.save(filename)
    print(f"QR code saved: {filename}")
