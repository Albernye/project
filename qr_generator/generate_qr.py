import qrcode
import os
from config import config

def generate_qr_codes(base_url: str = None, output_dir: str = None) -> str:
    """
    Génère les QR codes pour les salles 201-225
    et les place dans project/qrcodes.
    """
    # URL de base
    if base_url is None:
        base_url = config.qr_base_url

    # Répertoire de sortie : toujours sous la racine du projet
    if output_dir is None:
        output_dir = os.path.join(config.get_project_root(), 'qrcodes')

    os.makedirs(output_dir, exist_ok=True)

    for room_number in range(201, 226):
        room_url = f"{base_url}{room_number}"
        img = qrcode.make(room_url)
        filename = os.path.join(output_dir, f"room_{room_number}.png")
        img.save(filename)
        print(f"✅ QR code sauvegardé : {filename}")

    print(f"🎉 {25} QR codes générés dans {output_dir}")
    return output_dir

if __name__ == "__main__":
    generate_qr_codes()
