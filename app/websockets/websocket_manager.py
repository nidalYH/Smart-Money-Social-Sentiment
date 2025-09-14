"""
WebSocket Manager for Real-time Trading Updates
Provides real-time communication between backend and frontend
"""
import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import weakref

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        # Store active connections
        self.active_connections: Set[WebSocket] = set()

        # Store connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}

        # Message queue for offline clients
        self.message_queue: Dict[str, list] = {}

        # Statistics
        self.stats = {
            'total_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'connections_dropped': 0
        }

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None):
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            self.active_connections.add(websocket)

            # Store connection info
            self.connection_info[websocket] = {
                'client_id': client_id or f"client_{len(self.active_connections)}",
                'connected_at': datetime.utcnow(),
                'last_ping': datetime.utcnow()
            }

            self.stats['total_connections'] += 1

            logger.info(f"WebSocket connected: {self.connection_info[websocket]['client_id']} "
                       f"(Total: {len(self.active_connections)})")

            # Send connection confirmation
            await self.send_personal_message({
                'type': 'connection_established',
                'client_id': self.connection_info[websocket]['client_id'],
                'server_time': datetime.utcnow().isoformat(),
                'message': 'Connected to Smart Money Trading System'
            }, websocket)

            # Send any queued messages
            if client_id and client_id in self.message_queue:
                for message in self.message_queue[client_id]:
                    await self.send_personal_message(message, websocket)
                del self.message_queue[client_id]

        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

                client_info = self.connection_info.pop(websocket, {})
                client_id = client_info.get('client_id', 'unknown')

                self.stats['connections_dropped'] += 1

                logger.info(f"WebSocket disconnected: {client_id} "
                           f"(Remaining: {len(self.active_connections)})")

        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")

    async def send_personal_message(self, message: Dict[Any, Any], websocket: WebSocket):
        """Send message to a specific client"""
        try:
            if websocket in self.active_connections:
                message_str = json.dumps(message, default=str)
                await websocket.send_text(message_str)
                self.stats['messages_sent'] += 1
                return True
            else:
                logger.warning("Attempted to send message to disconnected client")
                return False

        except WebSocketDisconnect:
            logger.info("Client disconnected during message send")
            self.disconnect(websocket)
            return False
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.stats['messages_failed'] += 1
            return False

    async def broadcast(self, message: Dict[Any, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        disconnected = set()
        message_str = json.dumps(message, default=str)

        logger.debug(f"Broadcasting to {len(self.active_connections)} connections")

        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
                self.stats['messages_sent'] += 1
            except WebSocketDisconnect:
                logger.info("Client disconnected during broadcast")
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
                self.stats['messages_failed'] += 1

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_signal_update(self, signal: Dict):
        """Send new trading signal to all clients"""
        message = {
            'type': 'new_signal',
            'timestamp': datetime.utcnow().isoformat(),
            'signal': signal
        }
        await self.broadcast(message)

    async def send_trade_update(self, trade: Dict, portfolio: Dict = None):
        """Send trade execution update"""
        message = {
            'type': 'trade_executed',
            'timestamp': datetime.utcnow().isoformat(),
            'trade': trade,
            'portfolio': portfolio
        }
        await self.broadcast(message)

    async def send_position_update(self, positions: list, portfolio: Dict = None):
        """Send position update"""
        message = {
            'type': 'portfolio_update',
            'timestamp': datetime.utcnow().isoformat(),
            'positions': positions,
            'portfolio': portfolio
        }
        await self.broadcast(message)

    async def send_position_closed(self, trade: Dict):
        """Send position closed notification"""
        message = {
            'type': 'position_closed',
            'timestamp': datetime.utcnow().isoformat(),
            'trade': trade
        }
        await self.broadcast(message)

    async def send_market_update(self, market_data: Dict):
        """Send market overview update"""
        message = {
            'type': 'market_update',
            'timestamp': datetime.utcnow().isoformat(),
            'data': market_data
        }
        await self.broadcast(message)

    async def send_system_alert(self, alert_type: str, message_text: str, level: str = 'info'):
        """Send system alert to all clients"""
        message = {
            'type': 'system_alert',
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': alert_type,
            'message': message_text,
            'level': level
        }
        await self.broadcast(message)

    async def send_auto_trading_status(self, enabled: bool, settings: Dict = None):
        """Send auto-trading status update"""
        message = {
            'type': 'auto_trading_status',
            'timestamp': datetime.utcnow().isoformat(),
            'enabled': enabled,
            'settings': settings or {}
        }
        await self.broadcast(message)

    async def handle_client_message(self, websocket: WebSocket, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            # Update last ping time
            if websocket in self.connection_info:
                self.connection_info[websocket]['last_ping'] = datetime.utcnow()

            if msg_type == 'ping':
                # Respond to ping with pong
                await self.send_personal_message({
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)

            elif msg_type == 'subscribe':
                # Handle subscription requests
                channels = data.get('channels', [])
                await self._handle_subscription(websocket, channels)

            elif msg_type == 'request_data':
                # Handle data requests
                data_type = data.get('data_type')
                await self._handle_data_request(websocket, data_type)

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    async def _handle_subscription(self, websocket: WebSocket, channels: list):
        """Handle channel subscription requests"""
        # Store subscription preferences in connection info
        if websocket in self.connection_info:
            self.connection_info[websocket]['subscriptions'] = channels

        await self.send_personal_message({
            'type': 'subscription_confirmed',
            'channels': channels,
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

    async def _handle_data_request(self, websocket: WebSocket, data_type: str):
        """Handle data requests from clients"""
        try:
            if data_type == 'portfolio':
                # Get current portfolio data
                from ..trading.paper_trading import get_trading_engine
                trading_engine = get_trading_engine()

                portfolio = await trading_engine.get_portfolio_metrics()
                positions = trading_engine.get_position_summary()

                await self.send_personal_message({
                    'type': 'data_response',
                    'data_type': 'portfolio',
                    'portfolio': portfolio.__dict__,
                    'positions': positions,
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)

            elif data_type == 'recent_signals':
                # Would get recent signals from signal engine
                await self.send_personal_message({
                    'type': 'data_response',
                    'data_type': 'recent_signals',
                    'signals': [],  # Would be populated with actual signals
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)

        except Exception as e:
            logger.error(f"Error handling data request {data_type}: {e}")

    async def cleanup_stale_connections(self):
        """Remove stale connections that haven't pinged recently"""
        stale_connections = set()
        current_time = datetime.utcnow()

        for websocket, info in self.connection_info.items():
            last_ping = info.get('last_ping', info.get('connected_at'))
            if (current_time - last_ping).total_seconds() > 300:  # 5 minutes
                stale_connections.add(websocket)

        for websocket in stale_connections:
            logger.info("Cleaning up stale connection")
            self.disconnect(websocket)

    def get_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            **self.stats,
            'active_connections': len(self.active_connections),
            'timestamp': datetime.utcnow().isoformat()
        }

    async def start_periodic_tasks(self):
        """Start background tasks"""
        asyncio.create_task(self._periodic_cleanup())
        asyncio.create_task(self._periodic_stats())

    async def _periodic_cleanup(self):
        """Periodic cleanup of stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                await self.cleanup_stale_connections()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def _periodic_stats(self):
        """Periodic stats broadcast"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                if self.active_connections:
                    stats = self.get_stats()
                    await self.broadcast({
                        'type': 'stats_update',
                        'stats': stats
                    })
            except Exception as e:
                logger.error(f"Error in periodic stats: {e}")


# Global connection manager instance
manager = ConnectionManager()


def get_websocket_manager() -> ConnectionManager:
    """Get the global WebSocket manager"""
    return manager


# WebSocket endpoint handler
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler"""
    client_id = None

    try:
        # Get client ID from query params if provided
        client_id = websocket.query_params.get('client_id')

        # Connect the client
        await manager.connect(websocket, client_id)

        # Start periodic tasks if this is the first connection
        if len(manager.active_connections) == 1:
            await manager.start_periodic_tasks()

        # Listen for messages
        while True:
            try:
                message = await websocket.receive_text()
                await manager.handle_client_message(websocket, message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error receiving WebSocket message: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


# Utility functions for easy integration
async def broadcast_signal(signal: Dict):
    """Broadcast new signal to all connected clients"""
    await manager.send_signal_update(signal)

async def broadcast_trade(trade: Dict, portfolio: Dict = None):
    """Broadcast trade execution to all connected clients"""
    await manager.send_trade_update(trade, portfolio)

async def broadcast_portfolio_update(positions: list, portfolio: Dict):
    """Broadcast portfolio update to all connected clients"""
    await manager.send_position_update(positions, portfolio)

async def broadcast_position_closed(trade: Dict):
    """Broadcast position closed to all connected clients"""
    await manager.send_position_closed(trade)

async def broadcast_system_alert(alert_type: str, message: str, level: str = 'info'):
    """Broadcast system alert to all connected clients"""
    await manager.send_system_alert(alert_type, message, level)


logger.info("WebSocket manager initialized")