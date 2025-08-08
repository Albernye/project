import os
from unittest.mock import patch, MagicMock
import pytest
from dotenv import load_dotenv
from services.send_email import send_email 

# Load environment variables from .env file
load_dotenv()

def test_send_email_success():
    # Create a mock for the SMTP server
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_instance

        # Use the real Mailtrap values for the mocked test as well
        os.environ['EMAIL_USER'] = os.getenv('EMAIL_USER', '6f548cfb4a3570')  # Use real values
        os.environ['EMAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD', '0424226662f65d')  # Use real values
        os.environ['SMTP_SERVER'] = os.getenv('SMTP_SERVER', 'sandbox.smtp.mailtrap.io')  # Use real values
        os.environ['SMTP_PORT'] = os.getenv('SMTP_PORT', '587')  # Use real values

        # Call the send_email function with test parameters
        result = send_email('Test Subject', 'Test Body', to_email='dest@example.com')

        # Check that the email was sent successfully
        assert result is True
        mock_instance.starttls.assert_called_once()
        mock_instance.login.assert_called_once_with(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASSWORD'))
        mock_instance.send_message.assert_called_once()

def test_send_email_mailtrap():
    # Display environment variables for diagnostics
    print("Loaded environment variables:")
    for key in ['SMTP_SERVER', 'SMTP_PORT', 'EMAIL_USER', 'RECIPIENT_EMAIL']:
        value = os.getenv(key, 'Not Set')
        print(f"{key}: {value}")

    # Use the real Mailtrap values from the .env file
    success = send_email(
        subject="⚙️ Pytest Integration Mailtrap",
        body="This is a test integration with Mailtrap."
    )
    assert success, "Failed to send email via Mailtrap"

if __name__ == '__main__':
    pytest.main([__file__, '-s'])  # The '-s' option allows printed messages to be displayed

def test_send_email_missing_config():
    """Test error when config is missing."""
    import types
    import services.send_email as se
    se.email_config.is_configured = lambda: False
    se.email_config.get_missing_vars = lambda: ['EMAIL_USER']
    result = se.send_email('Subject', 'Body', to_email='dest@example.com')
    assert result is False

def test_send_email_no_recipient():
    """Test error when no recipient is set."""
    import types
    import services.send_email as se
    se.email_config.is_configured = lambda: True
    se.email_config.recipient_email = None
    result = se.send_email('Subject', 'Body', to_email=None)
    assert result is False
