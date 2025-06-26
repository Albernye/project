import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

class Config:
    """Configuration centralisée du projet"""
    
    # Configuration par défaut
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 5000
    DEFAULT_DEBUG = True
    
    # Environnements possibles
    DEVELOPMENT = 'development'
    STAGING = 'staging'
    PRODUCTION = 'production'
    
    def __init__(self):
        self.environment = os.getenv('FLASK_ENV', self.DEVELOPMENT)
        self.debug = os.getenv('DEBUG', 'True').lower() == 'true'
        self.host = os.getenv('HOST', self.DEFAULT_HOST)
        self.port = int(os.getenv('PORT', self.DEFAULT_PORT))
        
    @property
    def base_url(self) -> str:
        """
        Retourne l'URL de base selon l'environnement
        """
        # URL depuis variable d'environnement (priorité)
        env_url = os.getenv('BASE_URL')
        if env_url:
            return env_url.rstrip('/')
            
        # URLs par environnement
        if self.environment == self.PRODUCTION:
            # URL de production (à définir lors du déploiement)
            return os.getenv('PRODUCTION_URL', 'https://your-domain.com')
            
        elif self.environment == self.STAGING:
            # URL de staging/test
            return os.getenv('STAGING_URL', 'https://staging.your-domain.com')
            
        else:  # development
            # En développement, essayer de détecter l'IP locale
            return self._get_development_url()
    
    def _get_development_url(self) -> str:
        """
        En développement, essaie de détecter la meilleure URL locale
        """
        import socket
        
        try:
            # Méthode pour obtenir l'IP locale
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            return f"http://{local_ip}:{self.port}"
        except:
            # Fallback sur localhost
            return f"http://localhost:{self.port}"
    
    @property
    def qr_base_url(self) -> str:
        """URL de base pour les QR codes"""
        return f"{self.base_url}/location?room="
    
    def get_project_root(self) -> str:
        # __file__ est config.py, donc on remonte d’un niveau pour être à la racine
        return os.path.dirname(os.path.abspath(__file__))

    
    def get_data_dir(self) -> str:
        """Retourne le répertoire des données"""
        return os.path.join(self.get_project_root(), 'data')
    
    def get_qr_dir(self) -> str:
        """Retourne le répertoire des QR codes"""
        return os.path.join(self.get_project_root(), 'qrcodes')

# Instance globale de configuration
config = Config()

# Configuration email (à adapter selon votre fournisseur)
class EmailConfig:
    """Configuration pour l'envoi d'emails"""
    
    # Configuration Gmail (exemple)
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    
    # Credentials depuis variables d'environnement (SÉCURISÉ)
    EMAIL_USER = os.getenv('EMAIL_USER')  # votre-email@gmail.com
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # mot de passe d'application
    
    # Email de destination pour les données
    RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', 'supervisor@university.edu')
    
    @classmethod
    def is_configured(cls) -> bool:
        """Vérifie si la configuration email est complète"""
        return all([cls.EMAIL_USER, cls.EMAIL_PASSWORD, cls.SMTP_SERVER])

email_config = EmailConfig()

def print_config():
    """Affiche la configuration actuelle (pour debug)"""
    print("🔧 Configuration du projet :")
    print(f"   📍 Environnement : {config.environment}")
    print(f"   🌐 URL de base : {config.base_url}")
    print(f"   📱 URL QR codes : {config.qr_base_url}")
    print(f"   📁 Dossier projet : {config.get_project_root()}")
    print(f"   📊 Dossier data : {config.get_data_dir()}")
    print(f"   📱 Dossier QR : {config.get_qr_dir()}")
    print(f"   📧 Email configuré : {email_config.is_configured()}")

if __name__ == "__main__":
    print_config()