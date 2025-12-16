import os
import re
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml
from dotenv import load_dotenv

class Credentials(BaseModel):
    email: str
    password: str


class BrowserConfig(BaseModel):
    headless: bool = True
    slow_mo: int = 100
    timeout: int = 30000

class DefaultSettings(BaseModel):
    duration_hours: int = 3

class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: Optional[str] = None




from .models import Favorite, Zone, ScheduleRule

class Config(BaseSettings):
    municipality: str = "almere"
    credentials: Credentials
    browser: BrowserConfig = BrowserConfig()
    defaults: DefaultSettings = DefaultSettings()
    logging: LoggingConfig = LoggingConfig()
    favorites: List[Favorite] = []
    zones: List[Zone] = []
    
    class Config:
        env_prefix = "PARKEER_"
    
    @classmethod
    def load(cls, config_path: Path = None) -> "Config":
        """Load config from file with env var substitution"""
        load_dotenv()
        
        if config_path is None:
            config_path = Path("config.yaml")
        
        if config_path.exists():
            with open(config_path) as f:
                content = f.read()
            
            # Substitute ${VAR} with environment variables
            def replace_env(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            
            content = re.sub(r'\$\{(\w+)\}', replace_env, content)
            data = yaml.safe_load(content)
            config = cls(**data)
        
        else:
            # Fall back to environment variables only
            email = os.environ.get("PARKEER_EMAIL")
            password = os.environ.get("PARKEER_PASSWORD")
            
            if email and password:
                config = cls(
                    credentials=Credentials(
                        email=email,
                        password=password,
                    )
                )
            else:
                config = cls()
        
        # Add default zone if none exists
        if not config.zones:
            config.zones = [
                Zone(
                    name="Filmwijk",
                    code="36044",
                    hourly_rate=0.25,
                    max_daily_rate=1.00,
                    rules=[
                        ScheduleRule(days=[0, 1, 2], start_time="09:00", end_time="22:00"), # Mon-Wed
                        ScheduleRule(days=[3, 4, 5], start_time="09:00", end_time="24:00"), # Thu-Sat
                        ScheduleRule(days=[6], start_time="12:00", end_time="17:00")        # Sun
                    ]
                )
            ]
            
        return config
