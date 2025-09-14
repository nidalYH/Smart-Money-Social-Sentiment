"""
Telegram Bot for Real-time Trading Alerts
Sends formatted notifications for signals, trades, and portfolio updates
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TelegramAlerts:
    """Telegram bot for trading alerts"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        # Message templates
        self.templates = {
            'signal': """🚨 <b>NEW TRADING SIGNAL</b> 🚨

💰 <b>Symbol:</b> {symbol}
📊 <b>Signal:</b> {signal_type}
🎯 <b>Confidence:</b> {confidence:.1%}
💵 <b>Entry Price:</b> ${current_price:.4f}

📈 <b>Targets:</b>
• Take Profit: ${target_price:.4f}
• Stop Loss: ${stop_loss:.4f}

🧠 <b>Reasoning:</b>
{reasoning}

⚡ <b>Auto-Trading:</b> {auto_status}
⏰ <b>Time:</b> {timestamp}""",

            'trade_executed': """✅ <b>TRADE EXECUTED</b>

{side_emoji} <b>{side} {symbol}</b>
💵 Price: ${price:.4f}
📦 Quantity: {quantity:.4f}
💰 Total: ${total:.2f}

💼 <b>Portfolio:</b>
• Balance: ${balance:.2f}
• Total Value: ${total_value:.2f}

⏰ {timestamp}""",

            'position_closed': """🎯 <b>POSITION CLOSED</b>

{pnl_emoji} <b>{symbol}</b>
💰 <b>P&L:</b> ${realized_pnl:.2f} ({realized_pnl_pct:.2f}%)
⏱ <b>Hold Time:</b> {hold_duration}
📤 <b>Exit Reason:</b> {exit_reason}

💵 <b>Trade Details:</b>
• Entry: ${entry_price:.4f}
• Exit: ${exit_price:.4f}
• Quantity: {quantity:.4f}

⏰ {timestamp}""",

            'portfolio_update': """📊 <b>PORTFOLIO UPDATE</b>

💰 <b>Total Value:</b> ${total_value:.2f}
📈 <b>Total Return:</b> {total_return:+.2f}% (${total_return_usd:+.2f})
📅 <b>Daily Return:</b> {daily_return:+.2f}%

🎯 <b>Performance:</b>
• Win Rate: {win_rate:.1f}%
• Active Positions: {active_positions}
• Total Trades: {total_trades}

🎪 <b>Risk Metrics:</b>
• Sharpe Ratio: {sharpe_ratio:.2f}
• Max Drawdown: {max_drawdown:.2f}%

⏰ {timestamp}""",

            'market_alert': """🌍 <b>MARKET ALERT</b>

{alert_emoji} <b>{alert_type}</b>
📊 <b>Symbol:</b> {symbol}
💰 <b>Price:</b> ${price:.4f}
📈 <b>Change:</b> {change:+.2f}%

🔍 <b>Details:</b>
{details}

⏰ {timestamp}""",

            'system_status': """🔧 <b>SYSTEM STATUS</b>

{status_emoji} <b>Status:</b> {status}
🔗 <b>APIs:</b> {api_status}
🤖 <b>Auto-Trading:</b> {auto_trading}

📊 <b>Statistics:</b>
• Signals Today: {signals_today}
• Trades Today: {trades_today}
• API Calls: {api_calls}

⏰ {timestamp}"""
        }

    async def send_signal_alert(self, signal: Dict) -> bool:
        """Send new signal alert"""
        try:
            auto_status = "🤖 ENABLED" if signal.get('auto_trading_enabled') else "🔴 DISABLED"

            message = self.templates['signal'].format(
                symbol=signal['symbol'],
                signal_type=signal['signal_type'],
                confidence=signal['confidence'],
                current_price=signal.get('current_price', 0),
                target_price=signal.get('target_price', 0),
                stop_loss=signal.get('stop_loss', 0),
                reasoning=signal.get('reasoning', 'No reasoning provided'),
                auto_status=auto_status,
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")
            return False

    async def send_trade_execution_alert(self, trade: Dict, portfolio: Dict = None) -> bool:
        """Send trade execution notification"""
        try:
            side = trade['side']
            side_emoji = "🟢" if side == "BUY" else "🔴"
            total_value = trade['quantity'] * trade['price']

            message = self.templates['trade_executed'].format(
                side_emoji=side_emoji,
                side=side,
                symbol=trade['symbol'],
                price=trade['price'],
                quantity=trade['quantity'],
                total=total_value,
                balance=portfolio.get('cash_balance', 0) if portfolio else 0,
                total_value=portfolio.get('total_value', 0) if portfolio else 0,
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending trade execution alert: {e}")
            return False

    async def send_position_closed_alert(self, trade: Dict) -> bool:
        """Send position closed notification"""
        try:
            pnl = trade.get('realized_pnl', 0)
            pnl_emoji = "💚" if pnl > 0 else "❤️" if pnl < 0 else "💙"

            # Format hold duration
            hold_duration = trade.get('hold_duration_hours', 0)
            if hold_duration >= 24:
                hold_str = f"{hold_duration/24:.1f} days"
            else:
                hold_str = f"{hold_duration:.1f} hours"

            message = self.templates['position_closed'].format(
                pnl_emoji=pnl_emoji,
                symbol=trade['symbol'],
                realized_pnl=pnl,
                realized_pnl_pct=trade.get('realized_pnl_pct', 0),
                hold_duration=hold_str,
                exit_reason=trade.get('exit_reason', 'MANUAL'),
                entry_price=trade.get('entry_price', 0),
                exit_price=trade['price'],
                quantity=trade['quantity'],
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending position closed alert: {e}")
            return False

    async def send_portfolio_update(self, portfolio: Dict) -> bool:
        """Send portfolio performance update"""
        try:
            message = self.templates['portfolio_update'].format(
                total_value=portfolio.get('total_value', 0),
                total_return=portfolio.get('total_return_pct', 0),
                total_return_usd=portfolio.get('total_return', 0),
                daily_return=portfolio.get('daily_return_pct', 0),
                win_rate=portfolio.get('win_rate', 0),
                active_positions=len(portfolio.get('positions', [])),
                total_trades=portfolio.get('total_trades', 0),
                sharpe_ratio=portfolio.get('sharpe_ratio', 0),
                max_drawdown=portfolio.get('max_drawdown_pct', 0),
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending portfolio update: {e}")
            return False

    async def send_market_alert(self, alert_type: str, symbol: str, price: float,
                              change_pct: float, details: str) -> bool:
        """Send market-related alert"""
        try:
            # Choose emoji based on alert type
            alert_emojis = {
                'BREAKOUT': '🚀',
                'BREAKDOWN': '📉',
                'VOLUME_SPIKE': '📊',
                'UNUSUAL_ACTIVITY': '⚡',
                'TREND_REVERSAL': '🔄',
                'SUPPORT_RESISTANCE': '📏'
            }

            alert_emoji = alert_emojis.get(alert_type, '⚠️')

            message = self.templates['market_alert'].format(
                alert_emoji=alert_emoji,
                alert_type=alert_type,
                symbol=symbol,
                price=price,
                change=change_pct,
                details=details,
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending market alert: {e}")
            return False

    async def send_system_status(self, status: str, api_status: str, auto_trading: bool,
                               stats: Dict) -> bool:
        """Send system status update"""
        try:
            status_emoji = "🟢" if status == "healthy" else "🟡" if status == "degraded" else "🔴"

            message = self.templates['system_status'].format(
                status_emoji=status_emoji,
                status=status.upper(),
                api_status=api_status,
                auto_trading="🤖 ENABLED" if auto_trading else "🔴 DISABLED",
                signals_today=stats.get('signals_today', 0),
                trades_today=stats.get('trades_today', 0),
                api_calls=stats.get('api_calls_today', 0),
                timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending system status: {e}")
            return False

    async def send_custom_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a custom message"""
        return await self._send_message(message, parse_mode)

    async def send_quick_alert(self, emoji: str, title: str, message: str) -> bool:
        """Send a quick formatted alert"""
        formatted_message = f"{emoji} <b>{title}</b>\n\n{message}\n\n⏰ {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        return await self._send_message(formatted_message)

    async def _send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message via Telegram API"""
        try:
            url = f"{self.base_url}/sendMessage"

            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("Telegram message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Telegram API error {response.status}: {error_text}")
                        return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            url = f"{self.base_url}/getMe"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_info = data.get('result', {})
                            logger.info(f"Telegram bot connected: @{bot_info.get('username', 'unknown')}")

                            # Send test message
                            test_message = "🤖 <b>Smart Money Bot Connected!</b>\n\n✅ Ready to send trading alerts"
                            await self._send_message(test_message)

                            return True
                        else:
                            logger.error(f"Telegram API returned error: {data}")
                            return False
                    else:
                        logger.error(f"HTTP error {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Error testing Telegram connection: {e}")
            return False

    def format_price(self, price: float, symbol: str = "") -> str:
        """Format price for display"""
        if price >= 1:
            return f"${price:,.4f}"
        elif price >= 0.01:
            return f"${price:.6f}"
        else:
            return f"${price:.8f}"

    def format_percentage(self, pct: float) -> str:
        """Format percentage with appropriate emoji"""
        if pct > 0:
            return f"📈 +{pct:.2f}%"
        elif pct < 0:
            return f"📉 {pct:.2f}%"
        else:
            return f"➖ {pct:.2f}%"

    def format_duration(self, hours: float) -> str:
        """Format duration in human-readable format"""
        if hours >= 168:  # 1 week
            return f"{hours/168:.1f} weeks"
        elif hours >= 24:
            return f"{hours/24:.1f} days"
        elif hours >= 1:
            return f"{hours:.1f} hours"
        else:
            return f"{hours*60:.0f} minutes"


# Global instance
telegram_alerts: Optional[TelegramAlerts] = None

def get_telegram_alerts() -> Optional[TelegramAlerts]:
    """Get global Telegram alerts instance"""
    global telegram_alerts
    if telegram_alerts is None:
        from ..config import settings
        bot_token = settings.get("TELEGRAM_BOT_TOKEN")
        chat_id = settings.get("TELEGRAM_CHAT_ID")

        if bot_token and chat_id:
            telegram_alerts = TelegramAlerts(bot_token, chat_id)
        else:
            logger.warning("Telegram bot not configured - alerts disabled")

    return telegram_alerts

async def send_startup_message():
    """Send startup notification"""
    alerts = get_telegram_alerts()
    if alerts:
        await alerts.send_quick_alert(
            "🚀",
            "Smart Money Bot Started",
            "Trading system is now online and monitoring for signals!"
        )

# Example usage
async def main():
    """Example usage of Telegram alerts"""
    # Configuration
    BOT_TOKEN = "your_bot_token_here"
    CHAT_ID = "your_chat_id_here"

    # Initialize
    alerts = TelegramAlerts(BOT_TOKEN, CHAT_ID)

    # Test connection
    connected = await alerts.test_connection()
    if not connected:
        print("Failed to connect to Telegram")
        return

    # Example signal alert
    signal = {
        'symbol': 'BTC',
        'signal_type': 'STRONG_BUY',
        'confidence': 0.85,
        'current_price': 45000,
        'target_price': 48000,
        'stop_loss': 42000,
        'reasoning': 'Strong whale accumulation detected with positive Reddit sentiment and rising Google trends',
        'auto_trading_enabled': True
    }

    await alerts.send_signal_alert(signal)

    # Example trade execution
    trade = {
        'side': 'BUY',
        'symbol': 'BTC',
        'price': 45000,
        'quantity': 0.001
    }

    portfolio = {
        'cash_balance': 95500,
        'total_value': 100000
    }

    await alerts.send_trade_execution_alert(trade, portfolio)

if __name__ == "__main__":
    asyncio.run(main())