"""
Social sentiment analysis models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy import JSON
import uuid

from app.database import Base


class SocialMention(Base):
    """Model for social media mentions"""
    __tablename__ = "social_mentions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source information
    source = Column(String(50), nullable=False, index=True)  # twitter, telegram, discord, etc.
    source_id = Column(String(255), nullable=False, index=True)  # tweet_id, message_id, etc.
    platform_user_id = Column(String(255), nullable=True, index=True)
    platform_username = Column(String(255), nullable=True)
    
    # Content
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, default="en")
    
    # Mention details
    timestamp = Column(DateTime, nullable=False, index=True)
    mentioned_tokens = Column(JSON, nullable=False, default=list)  # List of token symbols
    hashtags = Column(JSON, nullable=True, default=list)
    urls = Column(JSON, nullable=True, default=list)
    
    # Engagement metrics
    likes_count = Column(Integer, nullable=False, default=0)
    retweets_count = Column(Integer, nullable=False, default=0)
    replies_count = Column(Integer, nullable=False, default=0)
    shares_count = Column(Integer, nullable=False, default=0)
    
    # User metrics
    user_followers_count = Column(Integer, nullable=True)
    user_verified = Column(Boolean, nullable=False, default=False)
    user_influence_score = Column(Float, nullable=False, default=0.0)
    
    # Classification
    is_spam = Column(Boolean, nullable=False, default=False)
    is_bot = Column(Boolean, nullable=False, default=False)
    sentiment_raw = Column(Float, nullable=True)  # Raw sentiment score
    
    # Processing status
    is_processed = Column(Boolean, nullable=False, default=False)
    processing_notes = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_mention_source_timestamp', 'source', 'timestamp'),
        Index('idx_mention_tokens', 'mentioned_tokens'),
        Index('idx_mention_influence', 'user_influence_score'),
        Index('idx_mention_processed', 'is_processed'),
    )


class SentimentScore(Base):
    """Model for aggregated sentiment scores"""
    __tablename__ = "sentiment_scores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Target information
    token_address = Column(String(42), nullable=False, index=True)
    token_symbol = Column(String(20), nullable=False, index=True)
    
    # Time period
    timestamp = Column(DateTime, nullable=False, index=True)
    time_window = Column(String(20), nullable=False)  # 1h, 4h, 24h, 7d
    
    # Sentiment metrics
    sentiment_score = Column(Float, nullable=False)  # -1 to 1
    sentiment_confidence = Column(Float, nullable=False)  # 0 to 1
    
    # Volume metrics
    mention_count = Column(Integer, nullable=False, default=0)
    mention_velocity = Column(Float, nullable=False, default=0.0)  # mentions per hour
    mention_acceleration = Column(Float, nullable=False, default=0.0)  # change in velocity
    
    # Engagement metrics
    total_engagement = Column(Integer, nullable=False, default=0)
    avg_engagement_per_mention = Column(Float, nullable=False, default=0.0)
    engagement_velocity = Column(Float, nullable=False, default=0.0)
    
    # Influencer metrics
    influencer_mention_count = Column(Integer, nullable=False, default=0)
    influencer_weighted_score = Column(Float, nullable=False, default=0.0)
    top_influencers = Column(JSON, nullable=True, default=list)
    
    # Source breakdown
    source_breakdown = Column(JSON, nullable=True, default=dict)  # {twitter: 0.8, telegram: 0.6}
    
    # Trend analysis
    sentiment_trend = Column(String(20), nullable=True)  # rising, falling, stable
    sentiment_momentum = Column(Float, nullable=False, default=0.0)
    
    # Comparative metrics
    vs_market_sentiment = Column(Float, nullable=True)  # Relative to overall crypto sentiment
    vs_historical_average = Column(Float, nullable=True)  # vs 30-day average
    
    # Quality indicators
    data_quality_score = Column(Float, nullable=False, default=1.0)
    sample_size = Column(Integer, nullable=False, default=0)
    
    # Indexes
    __table_args__ = (
        Index('idx_sentiment_token_timestamp', 'token_address', 'timestamp'),
        Index('idx_sentiment_symbol_timestamp', 'token_symbol', 'timestamp'),
        Index('idx_sentiment_score', 'sentiment_score'),
        Index('idx_sentiment_velocity', 'mention_velocity'),
        Index('idx_sentiment_window', 'time_window'),
    )


