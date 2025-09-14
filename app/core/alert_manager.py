"""
Multi-channel alert system for trading signals and whale activities
"""
import asyncio
import aiohttp
import logging
import smtplib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.config import settings
from app.models.alert import Alert, AlertDelivery
from app.models.user import User
from app.core.data_manager import DataManager

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


@dataclass
class AlertTemplate:
    """Alert message template"""
    title: str
    message: str
    emoji: str
    priority: AlertPriority
    channels: List[AlertChannel]


class AlertManager:
    """Main alert management system"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.is_running = False
        
        # Rate limiting
        self.rate_limits = {
            "telegram": {"limit": 30, "window": 3600},  # 30 per hour
            "discord": {"limit": 50, "window": 3600},   # 50 per hour
            "email": {"limit": 10, "window": 3600},     # 10 per hour
            "sms": {"limit": 5, "window": 3600}         # 5 per hour
        }
        
        # Alert templates
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, AlertTemplate]:
        """Initialize alert message templates"""
        return {
            "early_accumulation": AlertTemplate(
                title="🚀 Early Accumulation Signal",
                message="Whales are accumulating {token_symbol} with low social attention. "
                       "Net buying volume: ${net_volume:,.0f}. "
                       "Confidence: {confidence:.1%}",
                emoji="🚀",
                priority=AlertPriority.HIGH,
                channels=[AlertChannel.TELEGRAM, AlertChannel.DISCORD]
            ),
            
            "momentum_build": AlertTemplate(
                title="📈 Momentum Building",
                message="Social momentum building for {token_symbol}. "
                       "Sentiment: {sentiment:.2f}, Velocity: {velocity:.1f}/hr. "
                       "Whale support: {whale_score:.1%}",
                emoji="📈",
                priority=AlertPriority.MEDIUM,
                channels=[AlertChannel.TELEGRAM, AlertChannel.DISCORD]
            ),
            
            "fomo_warning": AlertTemplate(
                title="⚠️ FOMO Warning",
                message="High social buzz for {token_symbol} but whales are selling! "
                       "Sentiment: {sentiment:.2f}, Velocity: {velocity:.1f}/hr. "
                       "Net selling: ${net_volume:,.0f}",
                emoji="⚠️",
                priority=AlertPriority.CRITICAL,
                channels=[AlertChannel.TELEGRAM, AlertChannel.DISCORD, AlertChannel.EMAIL]
            ),
            
            "contrarian_play": AlertTemplate(
                title="🎯 Contrarian Opportunity",
                message="Negative sentiment for {token_symbol} but whales accumulating. "
                       "Sentiment: {sentiment:.2f}, Net buying: ${net_volume:,.0f}. "
                       "Risk: {risk:.1%}",
                emoji="🎯",
                priority=AlertPriority.HIGH,
                channels=[AlertChannel.TELEGRAM, AlertChannel.DISCORD]
            ),
            
            "whale_activity": AlertTemplate(
                title="🐋 Whale Activity",
                message="Large transaction detected: {transaction_type} {amount:,.0f} {token_symbol} "
                       "(${amount_usd:,.0f}) by wallet {wallet_address[:8]}... "
                       "Gas: {gas_price:.1f} gwei",
                emoji="🐋",
                priority=AlertPriority.MEDIUM,
                channels=[AlertChannel.TELEGRAM, AlertChannel.DISCORD]
            ),
            
            "sentiment_shift": AlertTemplate(
                title="📊 Sentiment Shift",
                message="Significant sentiment change for {token_symbol}: "
                       "{old_sentiment:.2f} → {new_sentiment:.2f} "
                       "({trend}). Mentions: {mention_count}",
                emoji="📊",
                priority=AlertPriority.MEDIUM,
                channels=[AlertChannel.TELEGRAM]
            ),
            
            "volume_spike": AlertTemplate(
                title="📊 Volume Spike",
                message="Unusual volume detected for {token_symbol}: "
                       "{volume_change:+.0%} (${volume_24h:,.0f}). "
                       "Whale activity: {whale_score:.1%}",
                emoji="📊",
                priority=AlertPriority.MEDIUM,
                channels=[AlertChannel.TELEGRAM, AlertChannel.DISCORD]
            )
        }
    
    async def send_signal_alert(self, signal_data: Dict, users: List[User] = None) -> bool:
        """Send alert for trading signal"""
        try:
            # Determine template based on signal type
            template_key = signal_data.get("signal_type", "unknown")
            if template_key not in self.templates:
                template_key = "whale_activity"  # Default template
            
            template = self.templates[template_key]
            
            # Format message
            title = template.title
            message = template.message.format(
                token_symbol=signal_data.get("token_symbol", "UNKNOWN"),
                confidence=signal_data.get("confidence", 0.0),
                sentiment=signal_data.get("sentiment_score", 0.0),
                velocity=signal_data.get("mention_velocity", 0.0),
                whale_score=signal_data.get("whale_activity_score", 0.0),
                net_volume=signal_data.get("whale_volume_usd", 0),
                risk=signal_data.get("risk_score", 0.0)
            )
            
            # Create alert
            alert = await self._create_alert(
                alert_type=signal_data.get("signal_type", "signal"),
                priority=template.priority,
                title=title,
                message=message,
                token_address=signal_data.get("token_address"),
                token_symbol=signal_data.get("token_symbol"),
                confidence_score=signal_data.get("confidence", 0.0),
                signal_id=signal_data.get("signal_id")
            )
            
            # Send to users
            if users:
                success = await self._send_alert_to_users(alert, users, template.channels)
            else:
                success = await self._send_alert_to_subscribers(alert, template.channels)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")
            return False
    
    async def send_whale_alert(self, whale_data: Dict, users: List[User] = None) -> bool:
        """Send alert for whale activity"""
        try:
            template = self.templates["whale_activity"]
            
            # Format message
            title = template.title
            message = template.message.format(
                transaction_type=whale_data.get("transaction_type", "transfer"),
                amount=whale_data.get("amount", 0),
                token_symbol=whale_data.get("token_symbol", "UNKNOWN"),
                amount_usd=whale_data.get("amount_usd", 0),
                wallet_address=whale_data.get("wallet_address", "unknown"),
                gas_price=whale_data.get("gas_price_gwei", 0)
            )
            
            # Create alert
            alert = await self._create_alert(
                alert_type="whale_activity",
                priority=template.priority,
                title=title,
                message=message,
                token_address=whale_data.get("token_address"),
                token_symbol=whale_data.get("token_symbol"),
                whale_wallet_id=whale_data.get("whale_wallet_id")
            )
            
            # Send to users
            if users:
                success = await self._send_alert_to_users(alert, users, template.channels)
            else:
                success = await self._send_alert_to_subscribers(alert, template.channels)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending whale alert: {e}")
            return False
    
    async def send_sentiment_alert(self, sentiment_data: Dict, users: List[User] = None) -> bool:
        """Send alert for sentiment shift"""
        try:
            template = self.templates["sentiment_shift"]
            
            # Format message
            title = template.title
            message = template.message.format(
                token_symbol=sentiment_data.get("token_symbol", "UNKNOWN"),
                old_sentiment=sentiment_data.get("old_sentiment", 0.0),
                new_sentiment=sentiment_data.get("new_sentiment", 0.0),
                trend=sentiment_data.get("trend", "stable"),
                mention_count=sentiment_data.get("mention_count", 0)
            )
            
            # Create alert
            alert = await self._create_alert(
                alert_type="sentiment_shift",
                priority=template.priority,
                title=title,
                message=message,
                token_address=sentiment_data.get("token_address"),
                token_symbol=sentiment_data.get("token_symbol"),
                sentiment_score_id=sentiment_data.get("sentiment_score_id")
            )
            
            # Send to users
            if users:
                success = await self._send_alert_to_users(alert, users, template.channels)
            else:
                success = await self._send_alert_to_subscribers(alert, template.channels)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending sentiment alert: {e}")
            return False
    
    async def _create_alert(self, alert_type: str, priority: AlertPriority, title: str, 
                          message: str, **kwargs) -> Alert:
        """Create alert record in database"""
        try:
            async with self.data_manager.get_db_session() as session:
                alert = Alert(
                    alert_type=alert_type,
                    priority=priority.value,
                    title=title,
                    message=message,
                    token_address=kwargs.get("token_address"),
                    token_symbol=kwargs.get("token_symbol"),
                    timestamp=datetime.utcnow(),
                    confidence_score=kwargs.get("confidence_score", 0.0),
                    signal_id=kwargs.get("signal_id"),
                    whale_wallet_id=kwargs.get("whale_wallet_id"),
                    sentiment_score_id=kwargs.get("sentiment_score_id"),
                    delivery_channels=[],
                    delivery_status="pending"
                )
                
                session.add(alert)
                await session.commit()
                await session.refresh(alert)
                
                return alert
                
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise
    
    async def _send_alert_to_users(self, alert: Alert, users: List[User], 
                                 channels: List[AlertChannel]) -> bool:
        """Send alert to specific users"""
        success_count = 0
        
        for user in users:
            try:
                # Check user preferences
                user_channels = self._get_user_preferred_channels(user, channels)
                
                for channel in user_channels:
                    delivery_success = await self._send_alert_delivery(
                        alert, user, channel
                    )
                    
                    if delivery_success:
                        success_count += 1
                
            except Exception as e:
                logger.error(f"Error sending alert to user {user.id}: {e}")
        
        return success_count > 0
    
    async def _send_alert_to_subscribers(self, alert: Alert, 
                                       channels: List[AlertChannel]) -> bool:
        """Send alert to all active subscribers"""
        try:
            # Get active subscribers
            async with self.data_manager.get_db_session() as session:
                stmt = select(User).where(
                    and_(
                        User.is_active == True,
                        or_(
                            User.telegram_enabled == True,
                            User.discord_enabled == True,
                            User.email_enabled == True
                        )
                    )
                )
                
                result = await session.execute(stmt)
                users = result.scalars().all()
            
            return await self._send_alert_to_users(alert, users, channels)
            
        except Exception as e:
            logger.error(f"Error sending alert to subscribers: {e}")
            return False
    
    def _get_user_preferred_channels(self, user: User, available_channels: List[AlertChannel]) -> List[AlertChannel]:
        """Get user's preferred channels from available channels"""
        user_channels = []
        
        for channel in available_channels:
            if channel == AlertChannel.TELEGRAM and user.telegram_enabled:
                user_channels.append(channel)
            elif channel == AlertChannel.DISCORD and user.discord_enabled:
                user_channels.append(channel)
            elif channel == AlertChannel.EMAIL and user.email_enabled:
                user_channels.append(channel)
            elif channel == AlertChannel.SMS and user.sms_enabled:
                user_channels.append(channel)
        
        return user_channels
    
    async def _send_alert_delivery(self, alert: Alert, user: User, 
                                 channel: AlertChannel) -> bool:
        """Send alert delivery through specific channel"""
        try:
            # Check rate limits
            rate_limit_key = f"alert_rate_limit:{user.id}:{channel.value}"
            if not await self.data_manager.check_rate_limit(
                rate_limit_key, 
                self.rate_limits[channel.value]["limit"],
                self.rate_limits[channel.value]["window"]
            ):
                logger.warning(f"Rate limit exceeded for user {user.id} on {channel.value}")
                return False
            
            # Create delivery record
            delivery = AlertDelivery(
                alert_id=alert.id,
                channel=channel.value,
                recipient_id=str(user.id),
                status="pending",
                attempted_at=datetime.utcnow()
            )
            
            # Send through appropriate channel
            success = False
            
            if channel == AlertChannel.TELEGRAM:
                success = await self._send_telegram_alert(alert, user, delivery)
            elif channel == AlertChannel.DISCORD:
                success = await self._send_discord_alert(alert, user, delivery)
            elif channel == AlertChannel.EMAIL:
                success = await self._send_email_alert(alert, user, delivery)
            elif channel == AlertChannel.SMS:
                success = await self._send_sms_alert(alert, user, delivery)
            
            # Update delivery status
            await self._update_delivery_status(delivery, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending alert delivery: {e}")
            return False
    
    async def _send_telegram_alert(self, alert: Alert, user: User, delivery: AlertDelivery) -> bool:
        """Send alert via Telegram"""
        if not user.telegram_chat_id:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            
            message = f"*{alert.title}*\n\n{alert.message}\n\n"
            message += f"⏰ {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            message += f"🎯 Confidence: {alert.confidence_score:.1%}"
            
            payload = {
                "chat_id": user.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            delivery.external_message_id = str(data["result"]["message_id"])
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def _send_discord_alert(self, alert: Alert, user: User, delivery: AlertDelivery) -> bool:
        """Send alert via Discord webhook"""
        webhook_url = user.discord_webhook_url or settings.discord_webhook_url
        
        if not webhook_url:
            return False
        
        try:
            # Choose embed color based on priority
            color_map = {
                "low": 0x00ff00,      # Green
                "medium": 0xffff00,   # Yellow
                "high": 0xff8800,     # Orange
                "critical": 0xff0000  # Red
            }
            
            embed = {
                "title": alert.title,
                "description": alert.message,
                "color": color_map.get(alert.priority, 0x888888),
                "timestamp": alert.timestamp.isoformat(),
                "footer": {
                    "text": f"Smart Money Sentiment • Confidence: {alert.confidence_score:.1%}"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "Smart Money Bot"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 204
            
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False
    
    async def _send_email_alert(self, alert: Alert, user: User, delivery: AlertDelivery) -> bool:
        """Send alert via email"""
        if not user.email_enabled or not settings.smtp_username:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_username
            msg['To'] = user.email
            msg['Subject'] = f"[Smart Money] {alert.title}"
            
            # HTML body
            html_body = f"""
            <html>
            <body>
                <h2>{alert.title}</h2>
                <p>{alert.message}</p>
                <hr>
                <p><strong>Token:</strong> {alert.token_symbol or 'N/A'}</p>
                <p><strong>Confidence:</strong> {alert.confidence_score:.1%}</p>
                <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <hr>
                <p><em>This is an automated alert from Smart Money Social Sentiment Analyzer.</em></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False
    
    async def _send_sms_alert(self, alert: Alert, user: User, delivery: AlertDelivery) -> bool:
        """Send alert via SMS (placeholder implementation)"""
        # SMS implementation would require a service like Twilio
        logger.info(f"SMS alert would be sent to {user.phone_number}: {alert.title}")
        return False
    
    async def _update_delivery_status(self, delivery: AlertDelivery, success: bool):
        """Update delivery status in database"""
        try:
            async with self.data_manager.get_db_session() as session:
                delivery.status = "delivered" if success else "failed"
                delivery.delivered_at = datetime.utcnow() if success else None
                delivery.failed_at = datetime.utcnow() if not success else None
                
                session.add(delivery)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating delivery status: {e}")
    
    async def get_alert_statistics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get alert delivery statistics"""
        try:
            async with self.data_manager.get_db_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                
                # Total alerts
                total_alerts = await session.scalar(
                    select(func.count(Alert.id)).where(
                        Alert.timestamp >= cutoff_time
                    )
                )
                
                # Successful deliveries
                successful_deliveries = await session.scalar(
                    select(func.count(AlertDelivery.id)).where(
                        and_(
                            AlertDelivery.attempted_at >= cutoff_time,
                            AlertDelivery.status == "delivered"
                        )
                    )
                )
                
                # Failed deliveries
                failed_deliveries = await session.scalar(
                    select(func.count(AlertDelivery.id)).where(
                        and_(
                            AlertDelivery.attempted_at >= cutoff_time,
                            AlertDelivery.status == "failed"
                        )
                    )
                )
                
                # Delivery rate
                total_deliveries = successful_deliveries + failed_deliveries
                delivery_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
                
                # Alerts by type
                alerts_by_type = await session.execute(
                    select(Alert.alert_type, func.count(Alert.id))
                    .where(Alert.timestamp >= cutoff_time)
                    .group_by(Alert.alert_type)
                )
                
                # Alerts by priority
                alerts_by_priority = await session.execute(
                    select(Alert.priority, func.count(Alert.id))
                    .where(Alert.timestamp >= cutoff_time)
                    .group_by(Alert.priority)
                )
                
                return {
                    "time_window_hours": hours_back,
                    "total_alerts": total_alerts,
                    "successful_deliveries": successful_deliveries,
                    "failed_deliveries": failed_deliveries,
                    "delivery_rate_percent": round(delivery_rate, 2),
                    "alerts_by_type": dict(alerts_by_type.fetchall()),
                    "alerts_by_priority": dict(alerts_by_priority.fetchall())
                }
                
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {}
    
    async def retry_failed_deliveries(self, max_retries: int = 3) -> int:
        """Retry failed alert deliveries"""
        try:
            async with self.data_manager.get_db_session() as session:
                # Get failed deliveries that haven't exceeded max retries
                stmt = select(AlertDelivery).where(
                    and_(
                        AlertDelivery.status == "failed",
                        AlertDelivery.retry_count < max_retries,
                        AlertDelivery.attempted_at >= datetime.utcnow() - timedelta(hours=24)
                    )
                )
                
                result = await session.execute(stmt)
                failed_deliveries = result.scalars().all()
                
                retry_count = 0
                for delivery in failed_deliveries:
                    try:
                        # Get alert and user
                        alert_stmt = select(Alert).where(Alert.id == delivery.alert_id)
                        alert_result = await session.execute(alert_stmt)
                        alert = alert_result.scalar_one_or_none()
                        
                        user_stmt = select(User).where(User.id == delivery.recipient_id)
                        user_result = await session.execute(user_stmt)
                        user = user_result.scalar_one_or_none()
                        
                        if alert and user:
                            # Retry delivery
                            success = await self._retry_delivery(delivery, alert, user)
                            if success:
                                retry_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error retrying delivery {delivery.id}: {e}")
                
                return retry_count
                
        except Exception as e:
            logger.error(f"Error retrying failed deliveries: {e}")
            return 0
    
    async def _retry_delivery(self, delivery: AlertDelivery, alert: Alert, user: User) -> bool:
        """Retry a failed delivery"""
        try:
            # Increment retry count
            delivery.retry_count += 1
            delivery.attempted_at = datetime.utcnow()
            
            # Determine channel
            channel = AlertChannel(delivery.channel)
            
            # Retry sending
            success = False
            if channel == AlertChannel.TELEGRAM:
                success = await self._send_telegram_alert(alert, user, delivery)
            elif channel == AlertChannel.DISCORD:
                success = await self._send_discord_alert(alert, user, delivery)
            elif channel == AlertChannel.EMAIL:
                success = await self._send_email_alert(alert, user, delivery)
            
            # Update status
            await self._update_delivery_status(delivery, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Error retrying delivery: {e}")
            return False
    
    async def start_alert_processing(self):
        """Start continuous alert processing"""
        logger.info("Starting alert processing...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Retry failed deliveries every 30 minutes
                retry_count = await self.retry_failed_deliveries()
                if retry_count > 0:
                    logger.info(f"Retried {retry_count} failed deliveries")
                
                # Wait 30 minutes
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"Error in alert processing: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def stop_alert_processing(self):
        """Stop alert processing"""
        logger.info("Stopping alert processing...")
        self.is_running = False


