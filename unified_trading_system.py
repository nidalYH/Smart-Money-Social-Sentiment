"""
Sistema de Trading Unificado con Configuración de Binance
Dashboard con navegación por pestañas y todas las funcionalidades
"""

import os
import sys
import asyncio
import logging
import uvicorn
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import json

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/unified_system.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Crear directorio de logs si no existe
os.makedirs('logs', exist_ok=True)

# Importar configuración de Binance
try:
    from config.binance_config import binance_config, setup_binance_credentials
except ImportError:
    logger.warning("No se pudo importar la configuración de Binance")
    # Crear configuración dummy
    class DummyBinanceConfig:
        def __init__(self):
            self.api_key = ""
            self.secret_key = ""
            self.testnet = True
            self.base_url = "https://testnet.binance.vision"
        
        def is_configured(self):
            return False
    
    binance_config = DummyBinanceConfig()
    setup_binance_credentials = None

# Modelos de datos
class BinanceConfig(BaseModel):
    api_key: str
    secret_key: str
    testnet: bool = True

class SystemConfig(BaseModel):
    update_interval: int = 30
    max_positions: int = 10
    auto_trading: bool = True

class TradingSignal(BaseModel):
    asset: str
    action: str  # buy, sell, hold
    price: float
    reason: str
    timestamp: datetime
    confidence: float

class Position(BaseModel):
    id: str
    asset: str
    type: str  # long, short
    quantity: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    timestamp: datetime

class WhaleActivity(BaseModel):
    wallet: str
    asset: str
    quantity: float
    value_usd: float
    timestamp: datetime
    type: str  # buy, sell

class SentimentMention(BaseModel):
    text: str
    sentiment: str  # positive, negative, neutral
    timestamp: datetime
    source: str

# Clase principal del sistema
class UnifiedTradingSystem:
    def __init__(self):
        self.app = FastAPI(
            title="Smart Money Trading System",
            description="Sistema de trading unificado con análisis de ballenas y sentimiento",
            version="2.0.0"
        )
        self.db_path = "unified_trading.db"
        self.positions = {}
        self.signals = []
        self.whale_activities = []
        self.sentiment_mentions = []
        self.is_trading_active = False
        self.binance_configured = False
        
        # Configurar rutas
        self.setup_routes()
        self.setup_database()
        
    def setup_database(self):
        """Configurar la base de datos SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crear tablas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    asset TEXT NOT NULL,
                    type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_percent REAL NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset TEXT NOT NULL,
                    action TEXT NOT NULL,
                    price REAL NOT NULL,
                    reason TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS whale_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    value_usd REAL NOT NULL,
                    type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sentiment_mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Base de datos configurada exitosamente")
            
        except Exception as e:
            logger.error(f"Error configurando base de datos: {e}")
    
    def setup_routes(self):
        """Configurar las rutas de la API"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Dashboard principal"""
            return templates.TemplateResponse("unified_dashboard.html", {"request": request})
        
        @self.app.get("/health")
        async def health_check():
            """Health check"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "binance_configured": self.binance_configured,
                "trading_active": self.is_trading_active
            }
        
        @self.app.get("/api/overview")
        async def get_overview():
            """Obtener datos del resumen"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Calcular métricas
                cursor.execute("SELECT COUNT(*) FROM positions")
                active_positions = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(pnl) FROM positions")
                total_pnl = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT SUM(quantity * current_price) FROM positions")
                total_value = cursor.fetchone()[0] or 0
                
                # Calcular tasa de éxito
                cursor.execute("SELECT COUNT(*) FROM signals WHERE action IN ('buy', 'sell')")
                total_signals = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM signals WHERE action IN ('buy', 'sell') AND confidence > 0.7")
                successful_signals = cursor.fetchone()[0]
                
                win_rate = (successful_signals / total_signals * 100) if total_signals > 0 else 0
                
                # Obtener actividad reciente
                cursor.execute("""
                    SELECT 'signal' as type, asset, action as quantity, price, timestamp
                    FROM signals 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                recent_activity = []
                for row in cursor.fetchall():
                    recent_activity.append({
                        "type": row[0],
                        "asset": row[1],
                        "quantity": row[2],
                        "price": row[3],
                        "timestamp": row[4],
                        "status": "completed"
                    })
                
                conn.close()
                
                return {
                    "totalValue": round(total_value, 2),
                    "profitLoss": round(total_pnl, 2),
                    "activePositions": active_positions,
                    "winRate": round(win_rate, 1),
                    "recentActivity": recent_activity,
                    "priceData": self._generate_price_data()
                }
                
            except Exception as e:
                logger.error(f"Error obteniendo resumen: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/trading/status")
        async def get_trading_status():
            """Obtener estado del trading"""
            return {
                "active": self.is_trading_active,
                "binance_configured": self.binance_configured,
                "chartData": self._generate_trading_chart_data()
            }
        
        @self.app.get("/api/whales/activity")
        async def get_whale_activity():
            """Obtener actividad de ballenas"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT wallet, asset, quantity, value_usd, type, timestamp
                    FROM whale_activities 
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """)
                
                activities = []
                for row in cursor.fetchall():
                    activities.append({
                        "wallet": row[0],
                        "asset": row[1],
                        "quantity": row[2],
                        "valueUsd": row[3],
                        "type": row[4],
                        "timestamp": row[5]
                    })
                
                conn.close()
                return {"activities": activities}
                
            except Exception as e:
                logger.error(f"Error obteniendo actividad de ballenas: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/sentiment/analysis")
        async def get_sentiment_analysis():
            """Obtener análisis de sentimiento"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Calcular distribución de sentimiento
                cursor.execute("SELECT sentiment, COUNT(*) FROM sentiment_mentions GROUP BY sentiment")
                sentiment_counts = dict(cursor.fetchall())
                
                total_mentions = sum(sentiment_counts.values())
                sentiment_data = {
                    "positive": (sentiment_counts.get("positive", 0) / total_mentions * 100) if total_mentions > 0 else 0,
                    "neutral": (sentiment_counts.get("neutral", 0) / total_mentions * 100) if total_mentions > 0 else 0,
                    "negative": (sentiment_counts.get("negative", 0) / total_mentions * 100) if total_mentions > 0 else 0
                }
                
                # Obtener menciones recientes
                cursor.execute("""
                    SELECT text, sentiment, timestamp, source
                    FROM sentiment_mentions 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                """)
                
                mentions = []
                for row in cursor.fetchall():
                    mentions.append({
                        "text": row[0],
                        "sentiment": row[1],
                        "timestamp": row[2],
                        "source": row[3]
                    })
                
                conn.close()
                return {
                    "sentimentData": sentiment_data,
                    "mentions": mentions
                }
                
            except Exception as e:
                logger.error(f"Error obteniendo análisis de sentimiento: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/signals/recent")
        async def get_recent_signals():
            """Obtener señales recientes"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT asset, action, price, reason, confidence, timestamp
                    FROM signals 
                    ORDER BY timestamp DESC 
                    LIMIT 20
                """)
                
                signals = []
                for row in cursor.fetchall():
                    signals.append({
                        "asset": row[0],
                        "action": row[1],
                        "price": row[2],
                        "reason": row[3],
                        "confidence": row[4],
                        "timestamp": row[5]
                    })
                
                conn.close()
                return {"signals": signals}
                
            except Exception as e:
                logger.error(f"Error obteniendo señales: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/positions/active")
        async def get_active_positions():
            """Obtener posiciones activas"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, asset, type, quantity, entry_price, current_price, pnl, pnl_percent, timestamp
                    FROM positions 
                    ORDER BY timestamp DESC
                """)
                
                positions = []
                for row in cursor.fetchall():
                    positions.append({
                        "id": row[0],
                        "asset": row[1],
                        "type": row[2],
                        "quantity": row[3],
                        "entryPrice": row[4],
                        "currentPrice": row[5],
                        "pnl": row[6],
                        "pnlPercent": row[7],
                        "timestamp": row[8]
                    })
                
                conn.close()
                return {"positions": positions}
                
            except Exception as e:
                logger.error(f"Error obteniendo posiciones: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/config/binance")
        async def save_binance_config(config: BinanceConfig):
            """Guardar configuración de Binance"""
            try:
                if setup_binance_credentials:
                    setup_binance_credentials(config.api_key, config.secret_key, config.testnet)
                    self.binance_configured = True
                    logger.info("Configuración de Binance guardada exitosamente")
                    return {"message": "Configuración de Binance guardada exitosamente"}
                else:
                    raise HTTPException(status_code=500, detail="Configuración de Binance no disponible")
            except Exception as e:
                logger.error(f"Error guardando configuración de Binance: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/config/system")
        async def save_system_config(config: SystemConfig):
            """Guardar configuración del sistema"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO system_config (key, value) 
                    VALUES ('update_interval', ?), ('max_positions', ?), ('auto_trading', ?)
                """, (str(config.update_interval), str(config.max_positions), str(config.auto_trading)))
                
                conn.commit()
                conn.close()
                
                logger.info("Configuración del sistema guardada exitosamente")
                return {"message": "Configuración del sistema guardada exitosamente"}
                
            except Exception as e:
                logger.error(f"Error guardando configuración del sistema: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/positions/{position_id}/close")
        async def close_position(position_id: str):
            """Cerrar posición"""
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    conn.close()
                    logger.info(f"Posición {position_id} cerrada exitosamente")
                    return {"message": "Posición cerrada exitosamente"}
                else:
                    conn.close()
                    raise HTTPException(status_code=404, detail="Posición no encontrada")
                    
            except Exception as e:
                logger.error(f"Error cerrando posición: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _generate_price_data(self):
        """Generar datos de precio simulados"""
        import random
        import time
        
        now = datetime.now()
        labels = []
        prices = []
        volumes = []
        
        for i in range(24):
            timestamp = now - timedelta(hours=23-i)
            labels.append(timestamp.strftime("%H:%M"))
            prices.append(50000 + random.randint(-5000, 5000))
            volumes.append(random.randint(100, 1000))
        
        return {
            "labels": labels,
            "prices": prices,
            "volumes": volumes
        }
    
    def _generate_trading_chart_data(self):
        """Generar datos del gráfico de trading"""
        import random
        
        # Datos simulados de candlestick
        data = []
        base_price = 50000
        
        for i in range(50):
            open_price = base_price + random.randint(-1000, 1000)
            close_price = open_price + random.randint(-500, 500)
            high_price = max(open_price, close_price) + random.randint(0, 200)
            low_price = min(open_price, close_price) - random.randint(0, 200)
            
            data.append([open_price, high_price, low_price, close_price])
            base_price = close_price
        
        return {
            "labels": [f"T{i}" for i in range(50)],
            "datasets": [{
                "label": "Precio",
                "data": data,
                "type": "candlestick"
            }]
        }
    
    def generate_sample_data(self):
        """Generar datos de muestra para testing"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generar señales de muestra
            assets = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
            actions = ["buy", "sell", "hold"]
            
            for i in range(20):
                cursor.execute("""
                    INSERT INTO signals (asset, action, price, reason, confidence, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    assets[i % len(assets)],
                    actions[i % len(actions)],
                    50000 + (i * 1000),
                    f"Señal generada automáticamente #{i+1}",
                    0.7 + (i % 3) * 0.1,
                    (datetime.now() - timedelta(hours=i)).isoformat()
                ))
            
            # Generar actividad de ballenas
            for i in range(15):
                cursor.execute("""
                    INSERT INTO whale_activities (wallet, asset, quantity, value_usd, type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"0x{'a' * 40}",
                    assets[i % len(assets)],
                    100 + (i * 10),
                    5000000 + (i * 100000),
                    actions[i % 2],
                    (datetime.now() - timedelta(hours=i)).isoformat()
                ))
            
            # Generar menciones de sentimiento
            sentiments = ["positive", "negative", "neutral"]
            sources = ["Twitter", "Reddit", "Telegram"]
            
            for i in range(25):
                cursor.execute("""
                    INSERT INTO sentiment_mentions (text, sentiment, source, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    f"Mención de muestra #{i+1} sobre {assets[i % len(assets)]}",
                    sentiments[i % len(sentiments)],
                    sources[i % len(sources)],
                    (datetime.now() - timedelta(hours=i)).isoformat()
                ))
            
            conn.commit()
            conn.close()
            logger.info("Datos de muestra generados exitosamente")
            
        except Exception as e:
            logger.error(f"Error generando datos de muestra: {e}")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Crear instancia del sistema
system = UnifiedTradingSystem()

# Generar datos de muestra
system.generate_sample_data()

# Configurar CORS
from fastapi.middleware.cors import CORSMiddleware
system.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    """Función principal"""
    logger.info("🚀 Iniciando Smart Money Trading System Unificado...")
    logger.info("📊 Dashboard con navegación por pestañas")
    logger.info("🏦 Configuración de Binance integrada")
    logger.info("🐋 Análisis de ballenas en tiempo real")
    logger.info("💹 Trading automático y manual")
    logger.info("📱 Interfaz unificada y responsive")
    
    try:
        uvicorn.run(
            system.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"Error iniciando el sistema: {e}")

if __name__ == "__main__":
    main()
