import os
import sys

# Add the project directory to the path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from qr_generator.generate_qr import generate_qr_codes
from web.app import app

def main():
    print("🚀 Starting of indoor navigation system")
    
    # Step 1: Generate QR codes
    print("\n📱 Generating QR codes...")
    try:
        qr_output_dir = generate_qr_codes()
        print(f"✅ QR codes generated in: {qr_output_dir}")
    except Exception as e:
        print(f"❌ Error generating QR codes: {e}")
        return False

    # Step 2: Start the web application
    print("\n🌐 Starting web server...")
    try:
        print("📡 Server accessible at: http://localhost:5000")
        print("🔗 Test URL: http://localhost:5000/location?room=201")
        print("⚠️  To stop the server: Ctrl+C")

        # Start Flask
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)