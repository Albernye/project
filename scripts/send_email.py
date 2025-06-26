import os
import smtplib
from email.message import EmailMessage
import json
from config import email_config, config

def send_email(subject: str, body: str, to_email: str = None):
    if not email_config.is_configured():
        raise RuntimeError("Email config incomplete in environment")

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = email_config.EMAIL_USER
    msg['To']      = to_email or email_config.RECIPIENT_EMAIL
    msg.set_content(body)

    with smtplib.SMTP(email_config.SMTP_SERVER, email_config.SMTP_PORT) as server:
        server.starttls()
        server.login(email_config.EMAIL_USER, email_config.EMAIL_PASSWORD)
        server.send_message(msg)
    print("✅ Email sent to:", msg['To'])

def send_sensor_data_email(to_email: str = None):
    # on lit les données JSONL
    file_path = os.path.join(config.get_project_root(), 'data', 'sensor_data.json')
    if not os.path.exists(file_path):
        raise FileNotFoundError("No sensor_data.json found")
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [json.loads(line) for line in f if line.strip()]
    subject = "Sensor Data Report"
    body = json.dumps(lines, indent=2)
    send_email(subject, body, to_email)
    print("✅ Sensor data emailed.")
