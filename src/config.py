"""Configuration module for the Taxi Bot."""
import os
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""
    
    # Telegram settings
    tg_token: str
    tg_admin_id: int
    
    # Redis settings
    redis_host: str
    redis_password: str
    
    # Taxi service settings
    taxi_username: str
    taxi_password: str
    taxi_update_period: int  # in seconds
    
    # Optional settings with defaults
    tg_log_path: Optional[str] = None
    redis_port: int = 6379
    redis_db: int = 0
    debug_html_dir: str = '/tmp/taxi_debug'
    bot_secret_code: Optional[str] = None  # Secret code for new users
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables."""
        # Validate required environment variables
        required_vars: List[str] = [
            'TG_TOKEN', 'TG_ADMIN_ID', 'RDS_HOST', 'RDS_PASSWORD',
            'TXI_USERNAME', 'TXI_PASSWORD'
        ]
        
        missing_vars: List[str] = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Parse update period (convert minutes to seconds)
        update_period_minutes: int = int(os.getenv('TXI_UPDATE_PERIOD', '25'))
        
        return cls(
            tg_token=os.getenv('TG_TOKEN'),
            tg_admin_id=int(os.getenv('TG_ADMIN_ID')),
            redis_host=os.getenv('RDS_HOST'),
            redis_password=os.getenv('RDS_PASSWORD'),
            taxi_username=os.getenv('TXI_USERNAME'),
            taxi_password=os.getenv('TXI_PASSWORD'),
            taxi_update_period=update_period_minutes * 60,
            tg_log_path=os.getenv('TG_LOG'),
            redis_port=int(os.getenv('RDS_PORT', '6379')),
            redis_db=int(os.getenv('RDS_DB', '0')),
            debug_html_dir=os.getenv('DEBUG_HTML_DIR', '/tmp/taxi_debug'),
            bot_secret_code=os.getenv('BOT_SECRET_CODE'),
        )

