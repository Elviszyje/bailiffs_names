"""
Configuration module for the bailiffs matching system.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "bailiffs_matching")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class APIConfig:
    """API configuration settings."""
    dane_gov_base_url: str = os.getenv("DANE_GOV_API_URL", "https://api.dane.gov.pl/1.4")
    bailiffs_resource_id: str = os.getenv("BAILIFFS_RESOURCE_ID", "67925")
    bailiffs_endpoint: str = os.getenv(
        "BAILIFFS_API_ENDPOINT", 
        "https://api.dane.gov.pl/1.4/resources/67925,wykaz-komornikow-na-1072025/data"
    )
    request_timeout: int = 30
    max_retries: int = 3

@dataclass
class MatchingConfig:
    """Matching algorithm configuration."""
    similarity_threshold_auto: float = float(os.getenv("SIMILARITY_THRESHOLD_AUTO", "0.85"))
    similarity_threshold_manual: float = float(os.getenv("SIMILARITY_THRESHOLD_MANUAL", "0.70"))
    similarity_threshold_reject: float = float(os.getenv("SIMILARITY_THRESHOLD_REJECT", "0.70"))
    
    weight_lastname: float = float(os.getenv("WEIGHT_LASTNAME", "0.5"))
    weight_firstname: float = float(os.getenv("WEIGHT_FIRSTNAME", "0.3"))
    weight_location: float = float(os.getenv("WEIGHT_LOCATION", "0.2"))

@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __post_init__(self):
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.matching = MatchingConfig()

# Global configuration instance
config = AppConfig()
