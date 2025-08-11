import smtplib
from email.message import EmailMessage
import json
import logging
from datetime import datetime
from typing import List, Dict
from config import config, email_config

logger = logging.getLogger(__name__)

def send_email(subject: str, body: str, to_email: str = None) -> bool:
    """
    Send an email with the given subject and body.
    
    Args:
        subject: Subject of the email
        body: Body of the email
        to_email: Recipient (optional, uses RECIPIENT_EMAIL by default)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        if not email_config.is_configured():
            missing = email_config.get_missing_vars()
            logger.error(f"Email config incomplete. Missing: {missing}")
            raise RuntimeError(f"Email config incomplete. Missing: {', '.join(missing)}")

        # Use the configured recipient email if not provided
        recipient = to_email or email_config.recipient_email
        if not recipient:
            raise RuntimeError("No recipient email specified and RECIPIENT_EMAIL not configured")

        # Create the message
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = email_config.email_user
        msg['To'] = recipient
        msg.set_content(body)

        # Send via SMTP
        with smtplib.SMTP(email_config.smtp_server, email_config.smtp_port) as server:
            server.starttls()
            server.login(email_config.email_user, email_config.email_password)
            server.send_message(msg)

        logger.info(f"✅ Email sent successfully to: {recipient}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending email: {e}")
        return False

def format_sensor_data_for_email(sensor_data: List[Dict]) -> str:
    """
    Format sensor data for the email in a readable way
    
    Args:
        sensor_data: List of sensor data

    Returns:
        str: Formatted data for the email
    """
    if not sensor_data:
        return "No sensor data available."

    # Report header
    report = f"""
📊 SENSOR DATA REPORT
===============================
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Number of entries: {len(sensor_data)}

"""
    
    # Summary of rooms and sensors
    rooms = set()
    sensor_counts = {
        'accelerometer': 0,
        'gyroscope': 0,
        'magnetometer': 0,
        'wifi': 0,
        'barometer': 0,
        'gps': 0
    }
    
    for data in sensor_data:
        if 'room' in data:
            rooms.add(data['room'])
        
        for sensor in sensor_counts:
            if sensor in data and data[sensor]:
                if sensor == 'gps':
                    sensor_counts[sensor] += 1
                else:
                    sensor_counts[sensor] += len(data[sensor])

    report += f"🏢 Rooms involved: {', '.join(sorted(rooms)) if rooms else 'Not specified'}\n\n"

    report += "📈 Sensor Summary:\n"
    for sensor, count in sensor_counts.items():
        if count > 0:
            report += f"  • {sensor.capitalize()}: {count} readings\n"
    
    report += "\n" + "="*50 + "\n\n"

    # Detailed data (limited to avoid overly long emails)
    report += "📋 DETAILED DATA:\n\n"

    for i, data in enumerate(sensor_data[-10:], 1):  # Only the last 10
        report += f"Entry #{i}:\n"
        report += f"  Timestamp: {data.get('timestamp', 'N/A')}\n"
        report += f"  Room: {data.get('room', 'N/A')}\n"
        report += f"  Client IP: {data.get('client_ip', 'N/A')}\n"
        
        if 'accelerometer' in data and data['accelerometer']:
            acc = data['accelerometer'][0] if data['accelerometer'] else {}
            report += f"  Accelerometer: x={acc.get('x', 0):.3f}, y={acc.get('y', 0):.3f}, z={acc.get('z', 0):.3f}\n"
        
        if 'gyroscope' in data and data['gyroscope']:
            gyro = data['gyroscope'][0] if data['gyroscope'] else {}
            report += f"  Gyroscope: α={gyro.get('alpha', 0):.3f}, β={gyro.get('beta', 0):.3f}, γ={gyro.get('gamma', 0):.3f}\n"
        
        if 'wifi' in data and data['wifi']:
            wifi_count = len(data['wifi'])
            strongest = max(data['wifi'], key=lambda x: x.get('rssi', -100))
            report += f"  WiFi: {wifi_count} networks detected, strongest: {strongest.get('ssid', 'N/A')} ({strongest.get('rssi', 'N/A')} dBm)\n"
        
        if 'gps' in data:
            gps = data['gps']
            report += f"  GPS: lat={gps.get('lat', 0):.6f}, lng={gps.get('lng', 0):.6f}\n"
        
        report += "\n"
    
    if len(sensor_data) > 10:
        report += f"... and {len(sensor_data) - 10} other entries.\n\n"

    # Footer with raw JSON data (optional)
    report += "="*50 + "\n"
    report += "📄 RAW JSON DATA (last 3 entries):\n\n"
    report += json.dumps(sensor_data[-3:], indent=2, ensure_ascii=False)
    
    return report

def send_sensor_data_email(to_email: str = None, limit: int = 50) -> bool:
    """
    Send the last sensor data entries by email.
    Args:
        to_email: Recipient email (optional, uses RECIPIENT_EMAIL by default)
        limit: Number of entries to include (default 50)
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Retrieve the recipient email
        data_file = config.get_project_root() / 'data' / 'sensor_data.jsonl'

        if not data_file.exists():
            logger.error("Sensor data file not found")
            return False

        # Load the data
        sensor_data = []
        with open(data_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        sensor_data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON line ignored: {e}")

        if not sensor_data:
            logger.error("No valid sensor data found")
            return False

        # Limit the number of entries
        if limit and limit > 0:
            sensor_data = sensor_data[-limit:]

        # Format the data for the email
        subject = f"📊 Sensor Data Report - {len(sensor_data)} entries"
        body = format_sensor_data_for_email(sensor_data)

        # Send the email
        success = send_email(subject, body, to_email)
        
        if success:
            logger.info(f"✅ Sensor data sent by email ({len(sensor_data)} entries)")
        else:
            logger.error("❌ Failed to send sensor data by email")

        return success
        
    except Exception as e:
        logger.error(f"Error sending sensor data by email: {e}")
        return False

def send_position_report_email(to_email: str, room: str, position: List[float], 
                              history: List[List[float]] = None) -> bool:
    """
    Send a position report email with the current position and history.
    Args:
        to_email: Recipient email
        room: Room identifier
        position: Current position as [x, y, z]
        history: List of previous positions (optional)
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        subject = f"📍 Position Report - Room {room}"

        body = f"""
📍 POSITION REPORT
=====================
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Room: {room}
Current Position: x={position[0]:.3f}, y={position[1]:.3f}

"""
        
        if len(position) > 2:
            body += f"Altitude: {position[2]:.3f}m\n"
        
        if history:
            body += f"\n📈 Position History (last {min(10, len(history))} positions):\n"
            for i, pos in enumerate(history[-10:], 1):
                body += f"  {i}. x={pos[0]:.3f}, y={pos[1]:.3f}"
                if len(pos) > 2:
                    body += f", z={pos[2]:.3f}"
                body += "\n"
        
        return send_email(subject, body, to_email)
        
    except Exception as e:
        logger.error(f"Error sending position report: {e}")
        return False

def send_error_report_email(error_message: str, context: str = None) -> bool:
    """
    Send an error report email to the administrators
    
    Args:
        error_message: Error message
        context: Error context (optional)

    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        subject = "🚨 System Error - Indoor Navigation"

        body = f"""
🚨 SYSTEM ERROR REPORT
==========================
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ERROR:
{error_message}

"""
        
        if context:
            body += f"CONTEXTE:\n{context}\n\n"
        
        body += """
Please check the system logs for more details.

Best regards,
Indoor Navigation System
"""

        # Send to default email (administrator)
        return send_email(subject, body)
        
    except Exception as e:
        logger.error(f"Error sending error report: {e}")
        return False

# Test email configuration on module load
if __name__ == "__main__":
    print("🧪 Test email configuration...")

    if email_config.is_configured():
        print("✅ Email configuration OK")
        
        # Test sending (optional)
        test_data = [{
            "room": "201",
            "timestamp": datetime.now().isoformat(),
            "accelerometer": [{"x": 0.1, "y": 0.2, "z": 0.0}],
            "wifi": [{"ssid": "TEST_AP", "rssi": -45}]
        }]
        
        print("📧 Test sending email...")
        success = send_email("Test Configuration", "Email configuration successful!")
        print(f"Result: {'✅ Success' if success else '❌ Failure'}")

    else:
        missing = email_config.get_missing_vars()
        print(f"❌ Incomplete email configuration. Missing variables: {missing}")
        print("""
To configure email, set the following environment variables:
export EMAIL_USER="your.email@gmail.com"
export EMAIL_PASSWORD="your_app_password"  # Not your regular password!
export SMTP_SERVER="smtp.gmail.com"            # Optional, default: smtp.gmail.com
export SMTP_PORT="587"                         # Optional, default: 587
export RECIPIENT_EMAIL="recipient@email.com" # Optional, for default emails
        """)