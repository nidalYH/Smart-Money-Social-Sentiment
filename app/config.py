"""
Configuration management for Smart Money Social Sentiment Analyzer
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Keys
    etherscan_api_key: str = Field("YourEtherscanAPIKey123456789", env="ETHERSCAN_API_KEY")
    coingecko_api_key: Optional[str] = Field("YourCoinGeckoAPIKey123456789", env="COINGECKO_API_KEY")
    twitter_bearer_token: str = Field("YourTwitterBearerToken123456789", env="TWITTER_BEARER_TOKEN")
    telegram_bot_token: str = Field("123456789:YourTelegramBotToken123456789", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    discord_webhook_url: Optional[str] = Field("https://discord.com/api/webhooks/your_webhook_url", env="DISCORD_WEBHOOK_URL")
    
    # Database
    database_url: str = Field("sqlite:///./smartmoney.db", env="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # Security
    secret_key: str = Field("your-super-secret-key-for-jwt-tokens-123456789", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Whale Tracking
    min_whale_balance: int = Field(1000, env="MIN_WHALE_BALANCE")
    max_whale_wallets: int = Field(100, env="MAX_WHALE_WALLETS")
    whale_tracking_interval: int = Field(300, env="WHALE_TRACKING_INTERVAL")
    
    # Signal Generation
    signal_confidence_threshold: float = Field(0.7, env="SIGNAL_CONFIDENCE_THRESHOLD")
    max_alerts_per_hour: int = Field(10, env="MAX_ALERTS_PER_HOUR")
    min_volume_change_percent: float = Field(20.0, env="MIN_VOLUME_CHANGE_PERCENT")
    
    # Social Sentiment
    twitter_monitor_keywords: List[str] = Field(
        default=["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "AVAX", "NEAR", "FTM", "ONE"],
        env="TWITTER_MONITOR_KEYWORDS"
    )
    telegram_channels: List[str] = Field(
        default=["binance", "coinbase", "cryptocom", "bybit", "okx"],
        env="TELEGRAM_CHANNELS"
    )
    
    # Alert Settings
    telegram_alerts_enabled: bool = Field(True, env="TELEGRAM_ALERTS_ENABLED")
    discord_alerts_enabled: bool = Field(True, env="DISCORD_ALERTS_ENABLED")
    email_alerts_enabled: bool = Field(False, env="EMAIL_ALERTS_ENABLED")
    sms_alerts_enabled: bool = Field(False, env="SMS_ALERTS_ENABLED")
    
    # Email Configuration
    smtp_server: str = Field("smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    
    # Performance
    max_concurrent_requests: int = Field(50, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    cache_ttl: int = Field(300, env="CACHE_TTL")
    
    # Trading Settings
    demo_trading_mode: bool = Field(True, env="DEMO_TRADING_MODE")
    initial_demo_balance: float = Field(100000.0, env="INITIAL_DEMO_BALANCE")
    trading_platform: str = Field("tradingview", env="TRADING_PLATFORM")
    max_position_size_percent: float = Field(0.05, env="MAX_POSITION_SIZE_PERCENT")
    stop_loss_percent: float = Field(0.05, env="STOP_LOSS_PERCENT")
    take_profit_multiplier: float = Field(2.0, env="TAKE_PROFIT_MULTIPLIER")
    
    # Development
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    environment: str = Field("development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def get_twitter_keywords(self) -> List[str]:
        """Parse comma-separated Twitter keywords"""
        if isinstance(self.twitter_monitor_keywords, str):
            return [kw.strip().upper() for kw in self.twitter_monitor_keywords.split(",")]
        return self.twitter_monitor_keywords
    
    def get_telegram_channels(self) -> List[str]:
        """Parse comma-separated Telegram channels"""
        if isinstance(self.telegram_channels, str):
            return [ch.strip().lower() for ch in self.telegram_channels.split(",")]
        return self.telegram_channels


# Global settings instance
settings = Settings()


# API Endpoints
ETHERSCAN_BASE_URL = "https://api.etherscan.io/api"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
TWITTER_BASE_URL = "https://api.twitter.com/2"
TELEGRAM_BASE_URL = "https://api.telegram.org/bot"


# Rate Limits (requests per minute)
RATE_LIMITS = {
    "etherscan": 5,  # Free tier
    "coingecko": 30,  # Free tier
    "twitter": 300,  # Basic tier
    "telegram": 30,  # Bot API
}


