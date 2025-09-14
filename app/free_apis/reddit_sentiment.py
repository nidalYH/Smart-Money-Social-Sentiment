"""
Reddit sentiment analysis engine using free Reddit API
Analyzes cryptocurrency discussions across multiple subreddits
"""
import asyncio
import aiohttp
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from urllib.parse import quote

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """Reddit post data structure"""
    title: str
    content: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    url: str
    author: str
    upvote_ratio: float


@dataclass
class RedditComment:
    """Reddit comment data structure"""
    body: str
    score: int
    created_utc: float
    author: str
    is_top_level: bool


@dataclass
class RedditSentimentResult:
    """Reddit sentiment analysis result"""
    symbol: str
    overall_sentiment: float
    confidence: float
    total_mentions: int
    post_count: int
    comment_count: int
    engagement_score: float
    subreddit_breakdown: Dict[str, float]
    trending_topics: List[str]
    top_posts: List[Dict]


class RedditSentimentEngine:
    """Free Reddit sentiment analysis using public API"""

    def __init__(self):
        self.crypto_subreddits = [
            'CryptoCurrency',
            'Bitcoin',
            'ethereum',
            'DeFi',
            'SatoshiStreetBets',
            'CryptoMoonShots',
            'altcoin',
            'CryptoMarkets',
            'ethtrader',
            'bitcoinbeginners'
        ]

        # Enhanced crypto lexicon for better sentiment analysis
        self.crypto_lexicon = {
            # Strong positive
            'moon': 3.5, 'mooning': 3.5, 'lambo': 3.0, 'rocket': 3.0,
            'parabolic': 2.8, 'breakout': 2.5, 'pump': 2.5, 'surge': 2.5,
            'bullish': 2.5, 'bull': 2.0, 'gains': 2.0, 'profit': 2.0,

            # Moderate positive
            'hodl': 1.8, 'hold': 1.5, 'diamond hands': 2.2, 'buy': 1.5,
            'accumulate': 1.8, 'dip': 1.2, 'undervalued': 2.0, 'gem': 2.5,
            'solid': 1.5, 'strong': 1.8, 'good': 1.2, 'bullish': 2.0,

            # Strong negative
            'dump': -2.8, 'dumping': -2.8, 'crash': -3.0, 'crashing': -3.0,
            'rug': -3.5, 'rugpull': -3.5, 'scam': -3.2, 'ponzi': -3.0,
            'dead': -2.8, 'rekt': -2.5, 'liquidated': -2.8, 'bear': -2.0,

            # Moderate negative
            'bearish': -2.0, 'sell': -1.5, 'selling': -1.8, 'fear': -1.8,
            'panic': -2.2, 'correction': -1.2, 'decline': -1.5, 'drop': -1.5,
            'fall': -1.2, 'down': -1.0, 'loss': -1.8, 'lost': -1.5,

            # Neutral but important
            'whale': 0.0, 'volume': 0.0, 'market': 0.0, 'trading': 0.0,
            'analysis': 0.2, 'chart': 0.0, 'technical': 0.2
        }

        # Initialize VADER with crypto lexicon
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.vader_analyzer.lexicon.update(self.crypto_lexicon)

        # Rate limiting
        self.request_delay = 2.0  # 2 seconds between requests
        self.last_request_time = 0

    async def get_reddit_sentiment(self, symbol: str, hours_back: int = 24) -> RedditSentimentResult:
        """
        Get comprehensive Reddit sentiment for a cryptocurrency symbol
        """
        logger.info(f"Analyzing Reddit sentiment for {symbol} (last {hours_back} hours)")

        all_posts = []
        all_comments = []
        subreddit_sentiments = {}

        # Search across all crypto subreddits
        for subreddit in self.crypto_subreddits:
            try:
                posts = await self._fetch_subreddit_posts(subreddit, symbol, hours_back)
                if posts:
                    all_posts.extend(posts)

                    # Analyze subreddit-specific sentiment
                    subreddit_sentiment = self._calculate_subreddit_sentiment(posts)
                    subreddit_sentiments[subreddit] = subreddit_sentiment

                    # Get comments for top posts
                    for post in posts[:3]:  # Top 3 posts per subreddit
                        comments = await self._fetch_post_comments(subreddit, post.url.split('/')[-2])
                        all_comments.extend(comments)

                # Rate limiting
                await self._respect_rate_limit()

            except Exception as e:
                logger.error(f"Error analyzing subreddit {subreddit}: {e}")
                continue

        if not all_posts and not all_comments:
            return self._create_empty_result(symbol)

        # Calculate overall sentiment
        overall_sentiment = self._calculate_overall_sentiment(all_posts, all_comments)
        confidence = self._calculate_confidence(all_posts, all_comments)
        engagement_score = self._calculate_engagement_score(all_posts)
        trending_topics = self._extract_trending_topics(all_posts)
        top_posts = self._get_top_posts(all_posts, 5)

        result = RedditSentimentResult(
            symbol=symbol,
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            total_mentions=len(all_posts) + len(all_comments),
            post_count=len(all_posts),
            comment_count=len(all_comments),
            engagement_score=engagement_score,
            subreddit_breakdown=subreddit_sentiments,
            trending_topics=trending_topics,
            top_posts=top_posts
        )

        logger.info(f"Reddit analysis complete for {symbol}: "
                   f"sentiment={overall_sentiment:.3f}, "
                   f"confidence={confidence:.3f}, "
                   f"mentions={result.total_mentions}")

        return result

    async def _fetch_subreddit_posts(self, subreddit: str, symbol: str, hours_back: int) -> List[RedditPost]:
        """Fetch posts from a subreddit mentioning the symbol"""
        posts = []

        try:
            # Try multiple sorting methods for better coverage
            for sort_method in ['hot', 'new', 'top']:
                url = f"https://www.reddit.com/r/{subreddit}/{sort_method}.json"
                params = {'limit': 100}

                async with aiohttp.ClientSession() as session:
                    headers = {'User-Agent': 'SmartMoney-Bot/1.0'}

                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status != 200:
                            continue

                        data = await response.json()

                        if 'data' not in data or 'children' not in data['data']:
                            continue

                        cutoff_time = datetime.utcnow().timestamp() - (hours_back * 3600)

                        for item in data['data']['children']:
                            post_data = item['data']

                            # Check if post is recent enough
                            if post_data['created_utc'] < cutoff_time:
                                continue

                            # Check if symbol is mentioned (case insensitive)
                            title_text = post_data.get('title', '').lower()
                            content_text = post_data.get('selftext', '').lower()
                            symbol_lower = symbol.lower()

                            if (symbol_lower in title_text or
                                symbol_lower in content_text or
                                f"${symbol_lower}" in title_text or
                                f"${symbol_lower}" in content_text):

                                post = RedditPost(
                                    title=post_data.get('title', ''),
                                    content=post_data.get('selftext', ''),
                                    score=post_data.get('score', 0),
                                    num_comments=post_data.get('num_comments', 0),
                                    created_utc=post_data.get('created_utc', 0),
                                    subreddit=subreddit,
                                    url=post_data.get('permalink', ''),
                                    author=post_data.get('author', '[deleted]'),
                                    upvote_ratio=post_data.get('upvote_ratio', 0.5)
                                )
                                posts.append(post)

                # Rate limiting between sort methods
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit}: {e}")

        # Remove duplicates and sort by engagement
        unique_posts = {}
        for post in posts:
            key = post.title + str(post.created_utc)
            if key not in unique_posts:
                unique_posts[key] = post

        posts = list(unique_posts.values())
        posts.sort(key=lambda x: x.score + x.num_comments, reverse=True)

        return posts[:20]  # Top 20 posts per subreddit

    async def _fetch_post_comments(self, subreddit: str, post_id: str) -> List[RedditComment]:
        """Fetch comments from a specific post"""
        comments = []

        try:
            url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"

            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'SmartMoney-Bot/1.0'}

                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return comments

                    data = await response.json()

                    if len(data) < 2:
                        return comments

                    comment_data = data[1]['data']['children']

                    for comment_item in comment_data[:10]:  # Top 10 comments
                        if 'data' not in comment_item:
                            continue

                        comment_info = comment_item['data']

                        if comment_info.get('body', '') in ['[deleted]', '[removed]', '']:
                            continue

                        comment = RedditComment(
                            body=comment_info.get('body', ''),
                            score=comment_info.get('score', 0),
                            created_utc=comment_info.get('created_utc', 0),
                            author=comment_info.get('author', '[deleted]'),
                            is_top_level=True
                        )
                        comments.append(comment)

        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")

        return comments

    def _calculate_overall_sentiment(self, posts: List[RedditPost], comments: List[RedditComment]) -> float:
        """Calculate weighted overall sentiment"""
        total_weighted_sentiment = 0
        total_weight = 0

        # Analyze posts (higher weight)
        for post in posts:
            text = f"{post.title} {post.content}"
            sentiment = self._analyze_text_sentiment(text)

            # Weight by engagement (score + comments)
            weight = max(1, post.score + post.num_comments * 2)

            # Boost weight for high upvote ratio
            if post.upvote_ratio > 0.8:
                weight *= 1.5

            total_weighted_sentiment += sentiment * weight
            total_weight += weight

        # Analyze comments (lower weight)
        for comment in comments:
            sentiment = self._analyze_text_sentiment(comment.body)

            # Weight by comment score
            weight = max(1, comment.score)

            total_weighted_sentiment += sentiment * weight * 0.5  # Comments have half weight
            total_weight += weight * 0.5

        return total_weighted_sentiment / max(total_weight, 1)

    def _analyze_text_sentiment(self, text: str) -> float:
        """Analyze sentiment of text using enhanced VADER"""
        if not text or len(text.strip()) < 3:
            return 0.0

        # Clean and normalize text
        text = self._preprocess_text(text)

        # Get VADER sentiment
        scores = self.vader_analyzer.polarity_scores(text)

        return scores['compound']  # Returns -1 to 1

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for sentiment analysis"""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove Reddit markdown
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)  # Bold/italic
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
        text = re.sub(r'~~([^~]+)~~', r'\1', text)  # Strikethrough

        # Handle emojis and special crypto expressions
        text = text.replace('🚀', ' rocket ')
        text = text.replace('🌙', ' moon ')
        text = text.replace('💎', ' diamond ')
        text = text.replace('📈', ' up ')
        text = text.replace('📉', ' down ')

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _calculate_subreddit_sentiment(self, posts: List[RedditPost]) -> float:
        """Calculate average sentiment for a specific subreddit"""
        if not posts:
            return 0.0

        sentiments = []
        for post in posts:
            text = f"{post.title} {post.content}"
            sentiment = self._analyze_text_sentiment(text)
            sentiments.append(sentiment)

        return sum(sentiments) / len(sentiments)

    def _calculate_confidence(self, posts: List[RedditPost], comments: List[RedditComment]) -> float:
        """Calculate confidence score based on sample size and engagement"""
        total_mentions = len(posts) + len(comments)
        total_engagement = sum(p.score + p.num_comments for p in posts) + sum(c.score for c in comments)

        # Base confidence from sample size
        sample_confidence = min(1.0, total_mentions / 50.0)  # 50+ mentions = full confidence

        # Engagement boost
        engagement_confidence = min(1.0, total_engagement / 1000.0)  # 1000+ engagement points

        # Time recency boost (more recent = higher confidence)
        if posts:
            avg_age_hours = (datetime.utcnow().timestamp() - sum(p.created_utc for p in posts) / len(posts)) / 3600
            recency_confidence = max(0.3, 1.0 - (avg_age_hours / 48.0))  # Decay over 48 hours
        else:
            recency_confidence = 0.5

        # Combined confidence
        confidence = (sample_confidence * 0.4 +
                     engagement_confidence * 0.3 +
                     recency_confidence * 0.3)

        return min(0.95, confidence)  # Cap at 95%

    def _calculate_engagement_score(self, posts: List[RedditPost]) -> float:
        """Calculate normalized engagement score"""
        if not posts:
            return 0.0

        total_engagement = sum(p.score + p.num_comments * 2 for p in posts)
        avg_engagement = total_engagement / len(posts)

        # Normalize to 0-1 scale (assume 100 is high engagement)
        return min(1.0, avg_engagement / 100.0)

    def _extract_trending_topics(self, posts: List[RedditPost]) -> List[str]:
        """Extract trending topics and keywords"""
        all_text = " ".join([f"{p.title} {p.content}" for p in posts])

        # Simple keyword extraction (could be enhanced with NLP)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())

        # Filter out common words and count frequency
        stop_words = {'the', 'and', 'but', 'for', 'with', 'this', 'that', 'are', 'was', 'will', 'been', 'have', 'has', 'had', 'you', 'your', 'they', 'them', 'their'}
        word_count = {}

        for word in words:
            if word not in stop_words and len(word) > 3:
                word_count[word] = word_count.get(word, 0) + 1

        # Return top 10 trending words
        trending = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, count in trending if count > 2]

    def _get_top_posts(self, posts: List[RedditPost], count: int) -> List[Dict]:
        """Get top posts by engagement"""
        sorted_posts = sorted(posts, key=lambda x: x.score + x.num_comments, reverse=True)

        top_posts = []
        for post in sorted_posts[:count]:
            top_posts.append({
                'title': post.title,
                'score': post.score,
                'comments': post.num_comments,
                'subreddit': post.subreddit,
                'upvote_ratio': post.upvote_ratio,
                'author': post.author,
                'url': f"https://reddit.com{post.url}",
                'sentiment': self._analyze_text_sentiment(f"{post.title} {post.content}")
            })

        return top_posts

    def _create_empty_result(self, symbol: str) -> RedditSentimentResult:
        """Create empty result when no data found"""
        return RedditSentimentResult(
            symbol=symbol,
            overall_sentiment=0.0,
            confidence=0.0,
            total_mentions=0,
            post_count=0,
            comment_count=0,
            engagement_score=0.0,
            subreddit_breakdown={},
            trending_topics=[],
            top_posts=[]
        )

    async def _respect_rate_limit(self):
        """Ensure we don't exceed Reddit's rate limits"""
        current_time = datetime.utcnow().timestamp()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = datetime.utcnow().timestamp()

    async def get_multiple_symbols_sentiment(self, symbols: List[str], hours_back: int = 24) -> Dict[str, RedditSentimentResult]:
        """Get sentiment for multiple symbols efficiently"""
        results = {}

        for symbol in symbols:
            try:
                result = await self.get_reddit_sentiment(symbol, hours_back)
                results[symbol] = result

                # Extra delay between symbols to be respectful
                await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"Error getting sentiment for {symbol}: {e}")
                results[symbol] = self._create_empty_result(symbol)

        return results


# Example usage
async def main():
    """Example usage of Reddit sentiment engine"""
    engine = RedditSentimentEngine()

    # Analyze sentiment for Bitcoin
    result = await engine.get_reddit_sentiment("BTC", hours_back=48)

    print(f"Bitcoin Reddit Sentiment Analysis:")
    print(f"Overall Sentiment: {result.overall_sentiment:.3f}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Total Mentions: {result.total_mentions}")
    print(f"Engagement Score: {result.engagement_score:.3f}")
    print(f"Trending Topics: {result.trending_topics}")
    print(f"Subreddit Breakdown: {result.subreddit_breakdown}")


if __name__ == "__main__":
    asyncio.run(main())