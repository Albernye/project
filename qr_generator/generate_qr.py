import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
from config import config

def generate_qr_codes(base_url: str = None, output_dir: str = None) -> str:
    """
    Génère les QR codes pour les salles 201-225 avec leur numéro en dessous
    et les place dans project/qrcodes.
    """
    if base_url is None:
        base_url = config.qr_base_url

    if output_dir is None:
        output_dir = os.path.join(config.get_project_root(), 'qrcodes')

    os.makedirs(output_dir, exist_ok=True)

    # Optionnel : change la police si tu veux (utilise une police installée ou par défaut)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    for room_number in range(201, 226):
        room_url = f"{base_url}{room_number}"
        qr = qrcode.make(room_url)

        # Convertir en image RGB pour modification
        qr = qr.convert("RGB")

        # Créer une nouvelle image plus haute pour le texte
        width, height = qr.size
        new_height = height + 40  # espace pour le texte
        new_img = Image.new("RGB", (width, new_height), "white")
        new_img.paste(qr, (0, 0))

        # Ajouter le texte (numéro de salle centré)
        draw = ImageDraw.Draw(new_img)
        text = f"Salle {room_number}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) / 2, height + 10), text, fill="black", font=font)


        # Sauvegarder l’image finale
        filename = os.path.join(output_dir, f"room_{room_number}.png")
        new_img.save(filename)
        print(f"✅ QR code sauvegardé : {filename}")

    print(f"🎉 {25} QR codes générés dans {output_dir}")
    return output_dir

if __name__ == "__main__":
    generate_qr_codes()
