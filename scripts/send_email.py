import smtplib
from email.mime.text import MIMEText
import json

# This function sends an email with the specified subject and body to the given email address.
def send_email(subject, body, to_email):
    from_email = "your_email@example.com"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP('smtp.example.com') as server:
        server.login("your_email@example.com", "your_password")
        server.send_message(msg)

# This function reads sensor data from a JSON file and sends it via email.
def send_sensor_data_email(to_email):
    with open('../data/sensor_data.json', 'r') as f:
        data = json.load(f)

    subject = "Sensor Data"
    body = json.dumps(data)
    send_email(subject, body, to_email)
