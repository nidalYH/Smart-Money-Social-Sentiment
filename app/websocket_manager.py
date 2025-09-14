"""
WebSocket manager for real-time updates
"""
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Store active connections
        self.active_connections: List[WebSocket] = []
        
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Message queue for broadcasting
        self.message_queue: Optional[asyncio.Queue] = None
        self._processor_task: Optional[asyncio.Task] = None
    
    async def _start_message_processor(self):
        """Start the message processor task if not already started"""
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_message_queue())
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Start message processor if not started
        await self._start_message_processor()
        
        # Store connection metadata
        connection_id = str(uuid.uuid4())
        self.connection_metadata[websocket] = {
            "connection_id": connection_id,
            "connected_at": datetime.utcnow(),
            "client_info": client_info or {},
            "subscriptions": set()
        }
        
        logger.info(f"WebSocket connected: {connection_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to Smart Money Trading System"
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if websocket in self.connection_metadata:
            connection_id = self.connection_metadata[websocket]["connection_id"]
            del self.connection_metadata[websocket]
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None):
        """Broadcast a message to all connected clients"""
        # Add to message queue for processing
        await self.message_queue.put({
            "message": message,
            "exclude": exclude
        })
    
    async def _process_message_queue(self):
        """Process messages from the queue and broadcast them"""
        while True:
            try:
                # Wait for message from queue
                queue_item = await self.message_queue.get()
                message = queue_item["message"]
                exclude = queue_item.get("exclude")
                
                # Send to all active connections except excluded one
                disconnected_connections = []
                
                for websocket in self.active_connections:
                    if websocket == exclude:
                        continue
                    
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_text(json.dumps(message))
                        else:
                            disconnected_connections.append(websocket)
                    except Exception as e:
                        logger.error(f"Error broadcasting to connection: {e}")
                        disconnected_connections.append(websocket)
                
                # Remove disconnected connections
                for websocket in disconnected_connections:
                    self.disconnect(websocket)
                
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
    
    async def subscribe_to_topic(self, websocket: WebSocket, topic: str):
        """Subscribe a connection to a specific topic"""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(topic)
            logger.info(f"Connection subscribed to topic: {topic}")
    
    async def unsubscribe_from_topic(self, websocket: WebSocket, topic: str):
        """Unsubscribe a connection from a specific topic"""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(topic)
            logger.info(f"Connection unsubscribed from topic: {topic}")
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]):
        """Broadcast a message to all connections subscribed to a topic"""
        subscribed_connections = []
        
        for websocket, metadata in self.connection_metadata.items():
            if topic in metadata["subscriptions"]:
                subscribed_connections.append(websocket)
        
        # Send to subscribed connections
        for websocket in subscribed_connections:
            await self.send_personal_message(message, websocket)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Get information about all active connections"""
        connection_info = []
        
        for websocket, metadata in self.connection_metadata.items():
            connection_info.append({
                "connection_id": metadata["connection_id"],
                "connected_at": metadata["connected_at"].isoformat(),
                "subscriptions": list(metadata["subscriptions"]),
                "client_info": metadata["client_info"]
            })
        
        return connection_info


class WebSocketManager:
    """Main WebSocket manager for the trading system"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.is_running = False
    
    async def start(self):
        """Start the WebSocket manager"""
        self.is_running = True
        logger.info("WebSocket manager started")
    
    async def stop(self):
        """Stop the WebSocket manager"""
        self.is_running = False
        logger.info("WebSocket manager stopped")
    
    async def handle_connection(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """Handle a new WebSocket connection"""
        await self.connection_manager.connect(websocket, client_info)
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                await self._handle_client_message(websocket, message)
                
        except WebSocketDisconnect:
            self.connection_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")
            self.connection_manager.disconnect(websocket)
    
    async def _handle_client_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle incoming messages from clients"""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe":
                topic = message.get("topic")
                if topic:
                    await self.connection_manager.subscribe_to_topic(websocket, topic)
                    await self.connection_manager.send_personal_message({
                        "type": "subscription_confirmed",
                        "topic": topic,
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
            
            elif message_type == "unsubscribe":
                topic = message.get("topic")
                if topic:
                    await self.connection_manager.unsubscribe_from_topic(websocket, topic)
                    await self.connection_manager.send_personal_message({
                        "type": "unsubscription_confirmed",
                        "topic": topic,
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
            
            elif message_type == "ping":
                await self.connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
    
    async def broadcast_signal(self, signal_data: Dict[str, Any]):
        """Broadcast a new trading signal"""
        message = {
            "type": "new_signal",
            "signal": signal_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("signals", message)
    
    async def broadcast_portfolio_update(self, portfolio_data: Dict[str, Any]):
        """Broadcast portfolio update"""
        message = {
            "type": "portfolio_update",
            "portfolio": portfolio_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("portfolio", message)
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast an alert"""
        message = {
            "type": "alert",
            "alert": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("alerts", message)
    
    async def broadcast_trade_execution(self, trade_data: Dict[str, Any]):
        """Broadcast trade execution"""
        message = {
            "type": "trade_execution",
            "trade": trade_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("trades", message)
    
    async def broadcast_market_update(self, market_data: Dict[str, Any]):
        """Broadcast market data update"""
        message = {
            "type": "market_update",
            "market": market_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("market", message)
    
    async def broadcast_whale_activity(self, whale_data: Dict[str, Any]):
        """Broadcast whale activity"""
        message = {
            "type": "whale_activity",
            "whale": whale_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("whales", message)
    
    async def broadcast_sentiment_update(self, sentiment_data: Dict[str, Any]):
        """Broadcast sentiment update"""
        message = {
            "type": "sentiment_update",
            "sentiment": sentiment_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.connection_manager.broadcast(message)
        await self.connection_manager.broadcast_to_topic("sentiment", message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            "active_connections": self.connection_manager.get_connection_count(),
            "connection_info": self.connection_manager.get_connection_info(),
            "is_running": self.is_running,
            "message_queue_size": self.connection_manager.message_queue.qsize()
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
