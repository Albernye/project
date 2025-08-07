import os
import cv2
from pyzbar.pyzbar import decode

def inspect_qr_codes(folder):
    for filename in sorted(os.listdir(folder)):
        if filename.endswith('.png'):
            path = os.path.join(folder, filename)
            img = cv2.imread(path)
            decoded = decode(img)
            if decoded:
                content = decoded[0].data.decode("utf-8")
                print(f"📄 {filename} → {content}")
            else:
                print(f"⚠️ Aucun QR code lisible dans {filename}")

# Example usage
inspect_qr_codes('qrcodes')
