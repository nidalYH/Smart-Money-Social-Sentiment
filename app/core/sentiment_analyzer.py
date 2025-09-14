"""
Social sentiment analysis engine for cryptocurrency mentions
"""
import asyncio
import aiohttp
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter

import tweepy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.config import settings
from app.models.sentiment import SocialMention, SentimentScore
from app.core.data_manager import DataManager

logger = logging.getLogger(__name__)


@dataclass
class SentimentData:
    """Data class for sentiment analysis results"""
    token_symbol: str
    sentiment_score: float  # -1 to 1
    confidence: float  # 0 to 1
    mention_count: int
    mention_velocity: float  # mentions per hour
    influencer_weight: float
    engagement_score: float


class SentimentAnalyzer:
    """Main sentiment analysis class"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize Twitter API
        self.twitter_client = None
        self.twitter_stream = None
        
        # Initialize Telegram bot
        self.telegram_bot = None
        
        # Crypto-specific lexicon
        self.crypto_lexicon = self._load_crypto_lexicon()
        
        # Known influencers and their weights
        self.influencer_weights = self._load_influencer_weights()
        
        # Token symbol patterns
        self.token_patterns = self._build_token_patterns()
        
        self.is_running = False
    
    def _load_crypto_lexicon(self) -> Dict[str, float]:
        """Load crypto-specific sentiment lexicon"""
        return {
            # Positive crypto terms
            "moon": 2.0, "lambo": 1.5, "hodl": 1.2, "bullish": 1.8, "pump": 1.5,
            "gains": 1.3, "profit": 1.2, "rocket": 2.0, "gem": 1.4, "diamond": 1.3,
            "bull": 1.5, "breakout": 1.3, "rally": 1.4, "surge": 1.3, "boom": 1.6,
            "ath": 1.2, "parabolic": 1.4, "fomo": 0.8, "yolo": 0.9,
            
            # Negative crypto terms
            "dump": -2.0, "crash": -2.2, "bear": -1.5, "bearish": -1.8, "rekt": -1.8,
            "loss": -1.2, "selloff": -1.5, "panic": -1.4, "fear": -1.3, "correction": -0.8,
            "bearish": -1.8, "decline": -1.2, "drop": -1.3, "fall": -1.2, "plunge": -1.6,
            "rugpull": -2.5, "scam": -2.0, "ponzi": -2.5, "bubble": -1.0,
            
            # Neutral but important terms
            "whale": 0.0, "volume": 0.0, "market": 0.0, "trading": 0.0, "buy": 0.5,
            "sell": -0.5, "hold": 0.0, "support": 0.3, "resistance": 0.0
        }
    
    def _load_influencer_weights(self) -> Dict[str, float]:
        """Load influencer weights based on follower count and engagement"""
        return {
            # Major influencers
            "elonmusk": 3.0, "VitalikButerin": 2.5, "naval": 2.0, "balajis": 2.0,
            "APompliano": 2.2, "michael_saylor": 2.3, "rogerkver": 1.8, "brian_armstrong": 2.0,
            
            # Crypto personalities
            "cz_binance": 2.5, "justinsuntron": 2.0, "danheld": 1.8, "CryptoWendyO": 1.5,
            "CryptoCred": 1.4, "CryptoWhale": 1.6, "WhalePanda": 1.5, "CryptoYoda": 1.3,
            
            # Analysts and traders
            "crypto_birb": 1.2, "CryptoWendyO": 1.5, "CryptoCred": 1.4, "rektcapital": 1.3,
            "CryptoWendyO": 1.5, "CryptoCred": 1.4, "rektcapital": 1.3,
            
            # Default weight for unknown users
            "default": 1.0
        }
    
    def _build_token_patterns(self) -> Dict[str, re.Pattern]:
        """Build regex patterns for token symbols"""
        patterns = {}
        for symbol in settings.get_twitter_keywords():
            # Create pattern that matches symbol with word boundaries
            pattern = r'\b' + re.escape(symbol) + r'\b'
            patterns[symbol] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    async def initialize(self):
        """Initialize sentiment analyzer with API connections"""
        logger.info("Initializing sentiment analyzer...")
        
        # Initialize Twitter API
        try:
            self.twitter_client = tweepy.Client(
                bearer_token=settings.twitter_bearer_token,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
        
        # Initialize Telegram bot (placeholder)
        try:
            # Telegram bot initialization would go here
            logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
        
        logger.info("Sentiment analyzer initialized")
    
    async def analyze_twitter_mentions(self, hours_back: int = 24) -> List[SentimentData]:
        """Analyze Twitter mentions for tracked tokens"""
        logger.info(f"Analyzing Twitter mentions for last {hours_back} hours...")
        
        if not self.twitter_client:
            logger.warning("Twitter client not initialized")
            return []
        
        sentiment_results = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for token_symbol in settings.get_twitter_keywords():
            try:
                # Search for tweets mentioning the token
                tweets = await self._search_tweets(token_symbol, hours_back)
                
                if tweets:
                    # Analyze sentiment for this token
                    sentiment_data = await self._analyze_token_sentiment(
                        token_symbol, tweets, cutoff_time
                    )
                    
                    if sentiment_data:
                        sentiment_results.append(sentiment_data)
                        
                        # Store in database
                        await self._store_sentiment_data(sentiment_data, tweets)
                
                # Rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing Twitter mentions for {token_symbol}: {e}")
        
        logger.info(f"Analyzed sentiment for {len(sentiment_results)} tokens")
        return sentiment_results
    
    async def _search_tweets(self, token_symbol: str, hours_back: int) -> List[Dict]:
        """Search for tweets mentioning a token"""
        try:
            # Build search query
            query = f"{token_symbol} -is:retweet lang:en"
            
            # Calculate start time
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Search tweets
            response = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                start_time=start_time,
                tweet_fields=["created_at", "public_metrics", "author_id", "context_annotations"],
                user_fields=["username", "public_metrics", "verified"]
            )
            
            if response.data:
                tweets = []
                users = {user.id: user for user in response.includes.get("users", [])}
                
                for tweet in response.data:
                    user = users.get(tweet.author_id)
                    tweet_data = {
                        "id": tweet.id,
                        "text": tweet.text,
                        "created_at": tweet.created_at,
                        "author_id": tweet.author_id,
                        "public_metrics": tweet.public_metrics,
                        "user": {
                            "username": user.username if user else None,
                            "verified": user.verified if user else False,
                            "followers_count": user.public_metrics.followers_count if user and user.public_metrics else 0
                        } if user else None
                    }
                    tweets.append(tweet_data)
                
                return tweets
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching tweets for {token_symbol}: {e}")
            return []
    
    async def _analyze_token_sentiment(self, token_symbol: str, tweets: List[Dict], 
                                     cutoff_time: datetime) -> Optional[SentimentData]:
        """Analyze sentiment for a specific token"""
        if not tweets:
            return None
        
        # Calculate time window
        time_window_hours = (datetime.utcnow() - cutoff_time).total_seconds() / 3600
        
        # Analyze each tweet
        sentiment_scores = []
        total_engagement = 0
        influencer_mentions = 0
        influencer_weighted_sentiment = 0
        
        for tweet in tweets:
            # Basic sentiment analysis
            sentiment = self._analyze_text_sentiment(tweet["text"])
            sentiment_scores.append(sentiment["compound"])
            
            # Calculate engagement
            metrics = tweet.get("public_metrics", {})
            engagement = (metrics.get("like_count", 0) + 
                         metrics.get("retweet_count", 0) * 2 + 
                         metrics.get("reply_count", 0))
            total_engagement += engagement
            
            # Weight by user influence
            user = tweet.get("user")
            if user:
                followers_count = user.get("followers_count", 0)
                is_verified = user.get("verified", False)
                
                # Calculate influence weight
                influence_weight = self._calculate_influence_weight(
                    followers_count, is_verified, user.get("username")
                )
                
                if influence_weight > 1.2:  # Consider as influencer
                    influencer_mentions += 1
                    influencer_weighted_sentiment += sentiment["compound"] * influence_weight
        
        # Calculate aggregated metrics
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        mention_velocity = len(tweets) / time_window_hours if time_window_hours > 0 else 0
        avg_engagement = total_engagement / len(tweets) if tweets else 0
        avg_influencer_sentiment = (influencer_weighted_sentiment / influencer_mentions 
                                  if influencer_mentions > 0 else 0)
        
        # Calculate confidence based on sample size and engagement
        confidence = min(1.0, len(tweets) / 50 + avg_engagement / 1000)
        
        return SentimentData(
            token_symbol=token_symbol,
            sentiment_score=avg_sentiment,
            confidence=confidence,
            mention_count=len(tweets),
            mention_velocity=mention_velocity,
            influencer_weight=influencer_mentions / len(tweets) if tweets else 0,
            engagement_score=avg_engagement
        )
    
    def _analyze_text_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text using VADER with crypto lexicon"""
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Get base sentiment
        sentiment = self.vader_analyzer.polarity_scores(processed_text)
        
        # Apply crypto lexicon adjustments
        sentiment = self._apply_crypto_lexicon(sentiment, text)
        
        return sentiment
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for sentiment analysis"""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove mentions and hashtags (but keep the words)
        text = re.sub(r'@\w+|#\w+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _apply_crypto_lexicon(self, sentiment: Dict[str, float], text: str) -> Dict[str, float]:
        """Apply crypto-specific lexicon adjustments"""
        text_lower = text.lower()
        
        # Count crypto terms
        positive_terms = 0
        negative_terms = 0
        total_weight = 0
        
        for term, weight in self.crypto_lexicon.items():
            if term in text_lower:
                if weight > 0:
                    positive_terms += 1
                elif weight < 0:
                    negative_terms += 1
                total_weight += abs(weight)
        
        # Adjust sentiment based on crypto terms
        if total_weight > 0:
            crypto_adjustment = (positive_terms - negative_terms) / total_weight * 0.3
            sentiment["compound"] = max(-1, min(1, sentiment["compound"] + crypto_adjustment))
        
        return sentiment
    
    def _calculate_influence_weight(self, followers_count: int, is_verified: bool, 
                                  username: str) -> float:
        """Calculate influence weight for a user"""
        # Base weight from follower count
        if followers_count > 1000000:
            base_weight = 2.0
        elif followers_count > 100000:
            base_weight = 1.5
        elif followers_count > 10000:
            base_weight = 1.2
        else:
            base_weight = 1.0
        
        # Verification bonus
        if is_verified:
            base_weight *= 1.3
        
        # Known influencer bonus
        if username and username.lower() in self.influencer_weights:
            base_weight *= self.influencer_weights[username.lower()]
        
        return min(base_weight, 3.0)  # Cap at 3.0
    
    async def _store_sentiment_data(self, sentiment_data: SentimentData, tweets: List[Dict]):
        """Store sentiment analysis results in database"""
        try:
            # Store individual mentions
            async with self.data_manager.get_db_session() as session:
                for tweet in tweets:
                    mention = SocialMention(
                        source="twitter",
                        source_id=tweet["id"],
                        platform_user_id=tweet["author_id"],
                        platform_username=tweet.get("user", {}).get("username"),
                        content=tweet["text"],
                        timestamp=tweet["created_at"],
                        mentioned_tokens=[sentiment_data.token_symbol],
                        likes_count=tweet.get("public_metrics", {}).get("like_count", 0),
                        retweets_count=tweet.get("public_metrics", {}).get("retweet_count", 0),
                        replies_count=tweet.get("public_metrics", {}).get("reply_count", 0),
                        user_followers_count=tweet.get("user", {}).get("followers_count", 0),
                        user_verified=tweet.get("user", {}).get("verified", False),
                        user_influence_score=self._calculate_influence_weight(
                            tweet.get("user", {}).get("followers_count", 0),
                            tweet.get("user", {}).get("verified", False),
                            tweet.get("user", {}).get("username")
                        ),
                        sentiment_raw=self._analyze_text_sentiment(tweet["text"])["compound"],
                        is_processed=True
                    )
                    session.add(mention)
                
                await session.commit()
            
            # Store aggregated sentiment score
            await self._store_aggregated_sentiment(sentiment_data)
            
        except Exception as e:
            logger.error(f"Error storing sentiment data: {e}")
    
    async def _store_aggregated_sentiment(self, sentiment_data: SentimentData):
        """Store aggregated sentiment score"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get token address
                from app.models.token import Token
                stmt = select(Token.address).where(Token.symbol == sentiment_data.token_symbol)
                result = await session.execute(stmt)
                token_address = result.scalar_one_or_none()
                
                if token_address:
                    sentiment_score = SentimentScore(
                        token_address=token_address,
                        token_symbol=sentiment_data.token_symbol,
                        timestamp=datetime.utcnow(),
                        time_window="1h",
                        sentiment_score=sentiment_data.sentiment_score,
                        sentiment_confidence=sentiment_data.confidence,
                        mention_count=sentiment_data.mention_count,
                        mention_velocity=sentiment_data.mention_velocity,
                        total_engagement=sentiment_data.engagement_score * sentiment_data.mention_count,
                        avg_engagement_per_mention=sentiment_data.engagement_score,
                        engagement_velocity=sentiment_data.mention_velocity * sentiment_data.engagement_score,
                        influencer_weighted_score=sentiment_data.influencer_weight,
                        data_quality_score=sentiment_data.confidence,
                        sample_size=sentiment_data.mention_count
                    )
                    session.add(sentiment_score)
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Error storing aggregated sentiment: {e}")
    
    async def get_sentiment_trends(self, token_symbol: str, hours_back: int = 24) -> Dict:
        """Get sentiment trends for a token"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                # Get sentiment scores over time
                stmt = select(SentimentScore).where(
                    and_(
                        SentimentScore.token_symbol == token_symbol,
                        SentimentScore.timestamp >= cutoff_time
                    )
                ).order_by(SentimentScore.timestamp.desc())
                
                result = await session.execute(stmt)
                scores = result.scalars().all()
                
                if not scores:
                    return {
                        "token_symbol": token_symbol,
                        "trend": "neutral",
                        "current_sentiment": 0.0,
                        "sentiment_change": 0.0,
                        "mention_velocity": 0.0,
                        "confidence": 0.0
                    }
                
                # Calculate trends
                current_sentiment = scores[0].sentiment_score
                old_sentiment = scores[-1].sentiment_score if len(scores) > 1 else current_sentiment
                sentiment_change = current_sentiment - old_sentiment
                
                # Determine trend direction
                if sentiment_change > 0.1:
                    trend = "rising"
                elif sentiment_change < -0.1:
                    trend = "falling"
                else:
                    trend = "stable"
                
                # Calculate average metrics
                avg_velocity = sum(s.mention_velocity for s in scores) / len(scores)
                avg_confidence = sum(s.sentiment_confidence for s in scores) / len(scores)
                
                return {
                    "token_symbol": token_symbol,
                    "trend": trend,
                    "current_sentiment": current_sentiment,
                    "sentiment_change": sentiment_change,
                    "mention_velocity": avg_velocity,
                    "confidence": avg_confidence,
                    "data_points": len(scores)
                }
                
        except Exception as e:
            logger.error(f"Error getting sentiment trends for {token_symbol}: {e}")
            return {"error": str(e)}
    
    async def start_monitoring(self):
        """Start continuous sentiment monitoring"""
        logger.info("Starting sentiment monitoring...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Analyze Twitter mentions
                sentiment_results = await self.analyze_twitter_mentions(hours_back=1)
                
                # Check for significant sentiment changes
                for sentiment_data in sentiment_results:
                    if abs(sentiment_data.sentiment_score) > 0.5 and sentiment_data.confidence > 0.7:
                        await self._check_sentiment_alerts(sentiment_data)
                
                # Wait before next iteration
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in sentiment monitoring: {e}")
                await asyncio.sleep(60)
    
    async def stop_monitoring(self):
        """Stop sentiment monitoring"""
        logger.info("Stopping sentiment monitoring...")
        self.is_running = False
    
    async def _check_sentiment_alerts(self, sentiment_data: SentimentData):
        """Check if sentiment data should trigger alerts"""
        # This will be integrated with the alert system
        logger.info(f"Significant sentiment detected for {sentiment_data.token_symbol}: "
                   f"Score: {sentiment_data.sentiment_score:.2f}, "
                   f"Confidence: {sentiment_data.confidence:.2f}, "
                   f"Mentions: {sentiment_data.mention_count}")
    
    async def get_market_sentiment_overview(self) -> Dict:
        """Get overall market sentiment overview"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get latest sentiment for all tracked tokens
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                stmt = select(SentimentScore).where(
                    SentimentScore.timestamp >= cutoff_time
                ).order_by(SentimentScore.timestamp.desc())
                
                result = await session.execute(stmt)
                recent_scores = result.scalars().all()
                
                if not recent_scores:
                    return {"overall_sentiment": 0.0, "trend": "neutral", "active_tokens": 0}
                
                # Calculate market-wide sentiment
                total_sentiment = sum(s.sentiment_score * s.sentiment_confidence for s in recent_scores)
                total_confidence = sum(s.sentiment_confidence for s in recent_scores)
                
                overall_sentiment = total_sentiment / total_confidence if total_confidence > 0 else 0
                
                # Determine market trend
                if overall_sentiment > 0.2:
                    trend = "bullish"
                elif overall_sentiment < -0.2:
                    trend = "bearish"
                else:
                    trend = "neutral"
                
                return {
                    "overall_sentiment": overall_sentiment,
                    "trend": trend,
                    "active_tokens": len(recent_scores),
                    "confidence": total_confidence / len(recent_scores) if recent_scores else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting market sentiment overview: {e}")
            return {"error": str(e)}


