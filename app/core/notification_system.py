"""
Advanced Notification System
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    TRADE_SIGNAL = "trade_signal"
    TRADE_EXECUTED = "trade_executed"
    RISK_ALERT = "risk_alert"
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_UPDATE = "performance_update"
    ERROR_ALERT = "error_alert"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Notification:
    """Notification data structure"""
    id: str
    type: NotificationType
    priority: Priority
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    channels: List[str]
    sent: bool = False

class NotificationSystem:
    """Advanced notification system supporting multiple channels"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notifications = []
        self.channels = {
            'telegram': TelegramNotifier(config.get('telegram', {})),
            'discord': DiscordNotifier(config.get('discord', {})),
            'email': EmailNotifier(config.get('email', {})),
            'webhook': WebhookNotifier(config.get('webhook', {}))
        }
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send notification through specified channels"""
        try:
            success = True
            
            for channel_name in notification.channels:
                if channel_name in self.channels:
                    channel = self.channels[channel_name]
                    channel_success = await channel.send(notification)
                    if not channel_success:
                        success = False
                        logger.error(f"Failed to send notification via {channel_name}")
                else:
                    logger.warning(f"Unknown notification channel: {channel_name}")
                    success = False
            
            notification.sent = success
            self.notifications.append(notification)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_trade_signal(self, signal: Dict[str, Any], channels: List[str] = None) -> bool:
        """Send trade signal notification"""
        if channels is None:
            channels = ['telegram', 'discord']
        
        notification = Notification(
            id=f"signal_{datetime.utcnow().timestamp()}",
            type=NotificationType.TRADE_SIGNAL,
            priority=Priority.HIGH if signal.get('confidence', 0) > 0.8 else Priority.MEDIUM,
            title=f"🚨 New Trading Signal: {signal.get('symbol', 'UNKNOWN')}",
            message=self._format_trade_signal_message(signal),
            data=signal,
            timestamp=datetime.utcnow(),
            channels=channels
        )
        
        return await self.send_notification(notification)
    
    async def send_trade_executed(self, trade: Dict[str, Any], channels: List[str] = None) -> bool:
        """Send trade execution notification"""
        if channels is None:
            channels = ['telegram', 'discord']
        
        notification = Notification(
            id=f"trade_{datetime.utcnow().timestamp()}",
            type=NotificationType.TRADE_EXECUTED,
            priority=Priority.MEDIUM,
            title=f"✅ Trade Executed: {trade.get('symbol', 'UNKNOWN')}",
            message=self._format_trade_executed_message(trade),
            data=trade,
            timestamp=datetime.utcnow(),
            channels=channels
        )
        
        return await self.send_notification(notification)
    
    async def send_risk_alert(self, risk_data: Dict[str, Any], channels: List[str] = None) -> bool:
        """Send risk alert notification"""
        if channels is None:
            channels = ['telegram', 'discord', 'email']
        
        priority = Priority.CRITICAL if risk_data.get('risk_level') == 'CRITICAL' else Priority.HIGH
        
        notification = Notification(
            id=f"risk_{datetime.utcnow().timestamp()}",
            type=NotificationType.RISK_ALERT,
            priority=priority,
            title=f"⚠️ Risk Alert: {risk_data.get('alert_type', 'Portfolio Risk')}",
            message=self._format_risk_alert_message(risk_data),
            data=risk_data,
            timestamp=datetime.utcnow(),
            channels=channels
        )
        
        return await self.send_notification(notification)
    
    async def send_performance_update(self, performance: Dict[str, Any], channels: List[str] = None) -> bool:
        """Send performance update notification"""
        if channels is None:
            channels = ['telegram', 'discord']
        
        notification = Notification(
            id=f"perf_{datetime.utcnow().timestamp()}",
            type=NotificationType.PERFORMANCE_UPDATE,
            priority=Priority.LOW,
            title="📊 Performance Update",
            message=self._format_performance_message(performance),
            data=performance,
            timestamp=datetime.utcnow(),
            channels=channels
        )
        
        return await self.send_notification(notification)
    
    def _format_trade_signal_message(self, signal: Dict[str, Any]) -> str:
        """Format trade signal message"""
        symbol = signal.get('symbol', 'UNKNOWN')
        signal_type = signal.get('signal_type', 'UNKNOWN')
        confidence = signal.get('confidence', 0) * 100
        price = signal.get('price', 0)
        reasoning = signal.get('reasoning', 'No reasoning provided')
        
        emoji = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "🟡"
        
        message = f"""
{emoji} **{signal_type} SIGNAL DETECTED**

💰 **Symbol:** {symbol}
📊 **Confidence:** {confidence:.1f}%
💵 **Price:** ${price:.4f}
🎯 **Reasoning:** {reasoning}

⏰ **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        return message
    
    def _format_trade_executed_message(self, trade: Dict[str, Any]) -> str:
        """Format trade execution message"""
        symbol = trade.get('symbol', 'UNKNOWN')
        trade_type = trade.get('type', 'UNKNOWN')
        quantity = trade.get('quantity', 0)
        price = trade.get('price', 0)
        pnl = trade.get('pnl', 0)
        
        emoji = "✅" if pnl >= 0 else "❌"
        
        message = f"""
{emoji} **TRADE EXECUTED**

💰 **Symbol:** {symbol}
📊 **Type:** {trade_type}
📈 **Quantity:** {quantity:.4f}
💵 **Price:** ${price:.4f}
💸 **P&L:** ${pnl:.2f}

⏰ **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        return message
    
    def _format_risk_alert_message(self, risk_data: Dict[str, Any]) -> str:
        """Format risk alert message"""
        alert_type = risk_data.get('alert_type', 'Portfolio Risk')
        risk_level = risk_data.get('risk_level', 'UNKNOWN')
        description = risk_data.get('description', 'Risk threshold exceeded')
        recommendations = risk_data.get('recommendations', [])
        
        emoji = "🚨" if risk_level == "CRITICAL" else "⚠️"
        
        message = f"""
{emoji} **RISK ALERT**

⚠️ **Type:** {alert_type}
🔴 **Level:** {risk_level}
📝 **Description:** {description}

💡 **Recommendations:**
{chr(10).join(f"• {rec}" for rec in recommendations[:3])}

⏰ **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        return message
    
    def _format_performance_message(self, performance: Dict[str, Any]) -> str:
        """Format performance update message"""
        total_return = performance.get('total_return', 0)
        win_rate = performance.get('win_rate', 0)
        total_trades = performance.get('total_trades', 0)
        sharpe_ratio = performance.get('sharpe_ratio', 0)
        
        emoji = "📈" if total_return >= 0 else "📉"
        
        message = f"""
{emoji} **PERFORMANCE UPDATE**

💰 **Total Return:** {total_return:.2f}%
📊 **Win Rate:** {win_rate:.1f}%
🔢 **Total Trades:** {total_trades}
📈 **Sharpe Ratio:** {sharpe_ratio:.2f}

⏰ **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        return message

class TelegramNotifier:
    """Telegram notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send(self, notification: Notification) -> bool:
        """Send notification via Telegram"""
        try:
            if not self.bot_token or not self.chat_id:
                logger.warning("Telegram not configured")
                return False
            
            message = f"*{notification.title}*\n\n{notification.message}"
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                data = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
                
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        logger.info(f"Telegram notification sent: {notification.id}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False

class DiscordNotifier:
    """Discord notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
    
    async def send(self, notification: Notification) -> bool:
        """Send notification via Discord webhook"""
        try:
            if not self.webhook_url:
                logger.warning("Discord not configured")
                return False
            
            # Create Discord embed
            embed = {
                "title": notification.title,
                "description": notification.message,
                "color": self._get_color_for_priority(notification.priority),
                "timestamp": notification.timestamp.isoformat(),
                "footer": {
                    "text": f"Smart Money Trading System"
                }
            }
            
            payload = {
                "embeds": [embed]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status in [200, 204]:
                        logger.info(f"Discord notification sent: {notification.id}")
                        return True
                    else:
                        logger.error(f"Discord webhook error: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False
    
    def _get_color_for_priority(self, priority: Priority) -> int:
        """Get Discord embed color based on priority"""
        colors = {
            Priority.LOW: 0x00ff00,      # Green
            Priority.MEDIUM: 0xffff00,    # Yellow
            Priority.HIGH: 0xff8800,      # Orange
            Priority.CRITICAL: 0xff0000   # Red
        }
        return colors.get(priority, 0x808080)  # Gray default

class EmailNotifier:
    """Email notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email')
        self.to_emails = config.get('to_emails', [])
    
    async def send(self, notification: Notification) -> bool:
        """Send notification via email"""
        try:
            if not all([self.smtp_server, self.username, self.password, self.from_email, self.to_emails]):
                logger.warning("Email not configured")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{notification.priority.value.upper()}] {notification.title}"
            
            body = f"""
{notification.message}

---
Smart Money Trading System
Timestamp: {notification.timestamp}
Notification ID: {notification.id}
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, self.to_emails, text)
            server.quit()
            
            logger.info(f"Email notification sent: {notification.id}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

class WebhookNotifier:
    """Generic webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.headers = config.get('headers', {})
    
    async def send(self, notification: Notification) -> bool:
        """Send notification via webhook"""
        try:
            if not self.webhook_url:
                logger.warning("Webhook not configured")
                return False
            
            payload = {
                "id": notification.id,
                "type": notification.type.value,
                "priority": notification.priority.value,
                "title": notification.title,
                "message": notification.message,
                "data": notification.data,
                "timestamp": notification.timestamp.isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, 
                    json=payload, 
                    headers=self.headers
                ) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Webhook notification sent: {notification.id}")
                        return True
                    else:
                        logger.error(f"Webhook error: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False
