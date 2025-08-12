import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
from web.app import get_project_root
from config import config

def generate_qr_codes(base_url: str = None, output_dir: str = None) -> str:
    """
    Generate QR codes for rooms 201-225 with their numbers below
    and place them in project/qrcodes.
    """
    if base_url is None:
        base_url = config.base_url

    if output_dir is None:
        output_dir = os.path.join(get_project_root(), 'web/qrcodes')

    os.makedirs(output_dir, exist_ok=True)

    # Option : change the font if you want (use an installed font or default)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    for room_number in range(201, 226):
        room_url = f"{base_url}/location?room={room_number}"
        qr = qrcode.make(room_url)

        # Convert to RGB image for editing
        qr = qr.convert("RGB")

        # Create a new image taller for the text
        width, height = qr.size
        new_height = height + 40  # space for the text
        new_img = Image.new("RGB", (width, new_height), "white")
        new_img.paste(qr, (0, 0))

        # Add the text (room number centered)
        draw = ImageDraw.Draw(new_img)
        text = f"Room {room_number}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) / 2, height + 10), text, fill="black", font=font)


        # Save the final image
        filename = os.path.join(output_dir, f"room_{room_number}.png")
        new_img.save(filename)
        print(f"✅ QR code saved to: {filename}")

    print(f"🎉 {25} QR codes generated in {output_dir}")
    return output_dir

if __name__ == "__main__":
    generate_qr_codes()
