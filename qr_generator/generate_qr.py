import qrcode
import os

def generate_qr_codes(base_url=None, output_dir=None):
    """
    Generate QR codes for rooms 201-225

    Args:
        base_url (str): Base URL for the QR codes
        output_dir (str): Output directory for the QR codes
    """
    # Default configuration
    if base_url is None:
        base_url = "http://localhost:5000/location?room="
    
    if output_dir is None:
        # Use a relative path from the script's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(os.path.dirname(current_dir), "qrcodes")

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Directory created: {output_dir}")

    # Generate QR codes for rooms 201 to 225
    for room_number in range(201, 226):
        room_url = f"{base_url}{room_number}"
        qr = qrcode.make(room_url)

        # Output filename
        filename = os.path.join(output_dir, f"room_{room_number}.png")

        # Save the QR code
        qr.save(filename)
        print(f"✅ QR code saved: {filename}")

    print(f"🎉 {25} QR codes generated successfully in {output_dir}")
    return output_dir

# Function for direct script execution
if __name__ == "__main__":
    # Allow direct script execution for testing
    generate_qr_codes()