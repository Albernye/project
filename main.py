import sys
from config import config
from qr_generator.generate_qr import generate_qr_codes
from web.app import app

def main():
    print("🚀 Indoor Navigation System starting...")

    # Génération des QR codes
    print("\n📱 Generating QR codes …")
    try:
        out = generate_qr_codes()
        print(f"✅ QR codes in: {out}")
    except Exception as e:
        print(f"❌ QR generation failed: {e}")
        return False

    # Lancement du serveur Flask
    print("\n🌐 Starting web server …")
    print(f"📡 Accessible at {config.base_url}")
    print(f"🔗 Test URL: {config.qr_base_url}201")
    print("⚠️  Stop with Ctrl+C")

    try:
        app.run(host=config.host, port=config.port, debug=config.debug)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
