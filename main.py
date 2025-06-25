from qr_generator.generate_qr import generate_qr_codes
from web.app import app
from scripts.send_email import send_sensor_data_email

if __name__ == "__main__":
    generate_qr_codes()
    app.run(debug=True)
