import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# -----------------------------------------------------------------------------
# Project directories and files
# -----------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / 'data'
RAW_DIR: Path = DATA_DIR / 'raw'
PROCESSED_DIR: Path = DATA_DIR / 'processed'
STATS_DIR: Path = DATA_DIR / 'stats'
RECORDINGS_DIR: Path = DATA_DIR / 'recordings'
QRCODES_DIR: Path = BASE_DIR / 'qrcodes'

# Specific files
PDR_TRACE: Path = DATA_DIR / 'pdr_traces' / 'current.csv'
FP_CURRENT: Path = RECORDINGS_DIR / 'current_fingerprints.csv'
QR_EVENTS_FILE: Path = DATA_DIR / 'qr_events.json'
ROOM_POS_CSV: Path = DATA_DIR / 'room_positions.csv'
SENSOR_DATA_FILE: Path = DATA_DIR / 'sensor_data.jsonl'

# -----------------------------------------------------------------------------
# Default parameters and mappings
# -----------------------------------------------------------------------------
DEFAULT_HOST: str = '0.0.0.0'
DEFAULT_PORT: int = 5000
DEFAULT_DEBUG: bool = True

DEFAULT_FLOOR: int = 2
DEFAULT_POSXY: tuple[float, float] = (2.194291, 41.406351)
DEFAULT_RSSI: int = -80
DEFAULT_AP_N: int = 5

SENSOR_MAPPING: dict[str, str] = {
    'accelerometer': 'accelerometer',
    'gyroscope': 'gyroscope',
    'magnetometer': 'magnetometer',
    'barometer': 'barometer',
    'gravity': 'gravity',
    'orientation': 'orientation',
    'compass': 'compass',
    'pedometer': 'pedometer',
    'microphone': 'microphone'
}
UNCALIBRATED_SUFFIX: str = 'uncalibrated'
MIN_ROWS: int = 15
ROOM_PREFIX: str = '2-'
# -----------------------------------------------------------------------------
# Simulation parameters
# -----------------------------------------------------------------------------
USE_SIMULATED_IMU: bool = True
SIM_DURATION: float = 10.0  # seconds
SIM_FS: float = 100.0       # sampling frequency (Hz)

# -----------------------------------------------------------------------------
# Environment-specific settings
# -----------------------------------------------------------------------------

class Env:
    DEVELOPMENT = 'development'
    STAGING = 'staging'
    PRODUCTION = 'production'

class Config:
    """Dynamic configuration based on environment."""
    def __init__(self):
        self.environment: str = os.getenv('FLASK_ENV', Env.DEVELOPMENT)
        self.debug: bool = os.getenv('DEBUG', 'True').lower() == 'true'
        self.host: str = os.getenv('HOST', DEFAULT_HOST)
        self.port: int = int(os.getenv('PORT', DEFAULT_PORT))

    @property
    def base_url(self) -> str:
        # Priority: explicit BASE_URL
        if url := os.getenv('BASE_URL'):
            return url.rstrip('/')
        # Environment-specific defaults
        if self.environment == Env.PRODUCTION:
            return os.getenv('PRODUCTION_URL', 'https://your-domain.com').rstrip('/')
        if self.environment == Env.STAGING:
            return os.getenv('STAGING_URL', 'https://staging.your-domain.com').rstrip('/')
        # Development fallback: detect local IP
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
            return f"http://{ip}:{self.port}"
        except Exception:
            return f"http://localhost:{self.port}"

# Singleton instance of Config
config = Config()

# -----------------------------------------------------------------------------
# Email configuration
# -----------------------------------------------------------------------------

class EmailConfig:
    """Configuration for sending emails read dynamically from environment."""

    @property
    def smtp_server(self) -> str:
        return os.getenv('SMTP_SERVER', 'smtp.gmail.com')

    @property
    def smtp_port(self) -> int:
        return int(os.getenv('SMTP_PORT', '587'))

    @property
    def email_user(self) -> Optional[str]:
        return os.getenv('EMAIL_USER')

    @property
    def email_password(self) -> Optional[str]:
        return os.getenv('EMAIL_PASSWORD')

    @property
    def recipient_email(self) -> Optional[str]:
        return os.getenv('RECIPIENT_EMAIL')

    def is_configured(self) -> bool:
        """
        Checks if SMTP_SERVER, EMAIL_USER and EMAIL_PASSWORD are set.
        """
        return all([self.smtp_server, self.email_user, self.email_password])

    def get_missing_vars(self) -> list[str]:
        missing: list[str] = []
        if not self.smtp_server:
            missing.append('SMTP_SERVER')
        if not self.email_user:
            missing.append('EMAIL_USER')
        if not self.email_password:
            missing.append('EMAIL_PASSWORD')
        return missing

# Singleton instance of EmailConfig
email_config = EmailConfig()
