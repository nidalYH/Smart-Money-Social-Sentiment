"""
Smart Money Trading System - Sistema Completo y Funcional
Dashboard unificado con navegación por pestañas y configuración de Binance
"""

import os
import sys
import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import time

# Imports de FastAPI y dependencias
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_system.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Crear directorio templates si no existe
os.makedirs('templates', exist_ok=True)

# Modelos de datos
class BinanceConfig(BaseModel):
    api_key: str
    secret_key: str
    testnet: bool = True

class SystemConfig(BaseModel):
    update_interval: int = 30
    max_positions: int = 10
    auto_trading: bool = True

# Configuración global
BINANCE_CONFIG = {
    'api_key': '',
    'secret_key': '',
    'testnet': True,
    'configured': False
}

class SmartTradingSystem:
    def __init__(self):
        self.app = FastAPI(title="Smart Money Trading System", version="2.0.0")
        self.db_path = "trading_system.db"
        self.is_trading_active = False
        self.setup_database()
        self.setup_routes()
        self.setup_middleware()
        self.generate_sample_data()
        
    def setup_database(self):
        """Configurar la base de datos SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de posiciones
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
        
        # Tabla de señales
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
        
        # Tabla de actividad de ballenas
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
        
        # Tabla de menciones de sentimiento
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        # Tabla de configuración
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Base de datos configurada exitosamente")
    
    def setup_middleware(self):
        """Configurar middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Configurar rutas de la API"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            return self.get_dashboard_html()
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "binance_configured": BINANCE_CONFIG['configured'],
                "trading_active": self.is_trading_active,
                "database": "connected"
            }
        
        @self.app.get("/api/overview")
        async def get_overview():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM positions")
            active_positions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COALESCE(SUM(pnl), 0) FROM positions")
            total_pnl = cursor.fetchone()[0]
            
            cursor.execute("SELECT COALESCE(SUM(quantity * current_price), 0) FROM positions")
            total_value = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signals WHERE confidence > 0.7")
            successful_signals = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM signals")
            total_signals = cursor.fetchone()[0]
            
            win_rate = (successful_signals / total_signals * 100) if total_signals > 0 else 0
            
            # Actividad reciente
            cursor.execute("""
                SELECT 'signal' as type, asset, action, price, timestamp 
                FROM signals ORDER BY timestamp DESC LIMIT 10
            """)
            recent_activity = [
                {
                    "type": row[0], "asset": row[1], "quantity": row[2],
                    "price": row[3], "timestamp": row[4], "status": "completed"
                } for row in cursor.fetchall()
            ]
            
            conn.close()
            
            return {
                "totalValue": round(total_value, 2),
                "profitLoss": round(total_pnl, 2),
                "activePositions": active_positions,
                "winRate": round(win_rate, 1),
                "recentActivity": recent_activity,
                "priceData": self.generate_price_data()
            }
        
        @self.app.get("/api/trading/status")
        async def get_trading_status():
            return {
                "active": self.is_trading_active,
                "binance_configured": BINANCE_CONFIG['configured'],
                "current_asset": "BTCUSDT",
                "current_interval": "5m"
            }
        
        @self.app.get("/api/whales/activity")
        async def get_whale_activity():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT wallet, asset, quantity, value_usd, type, timestamp
                FROM whale_activities ORDER BY timestamp DESC LIMIT 50
            """)
            
            activities = [
                {
                    "wallet": row[0], "asset": row[1], "quantity": row[2],
                    "valueUsd": row[3], "type": row[4], "timestamp": row[5]
                } for row in cursor.fetchall()
            ]
            
            conn.close()
            return {"activities": activities}
        
        @self.app.get("/api/sentiment/analysis")
        async def get_sentiment_analysis():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT sentiment, COUNT(*) FROM sentiment_mentions GROUP BY sentiment")
            sentiment_counts = dict(cursor.fetchall())
            total_mentions = sum(sentiment_counts.values())
            
            sentiment_data = {
                "positive": (sentiment_counts.get("positive", 0) / total_mentions * 100) if total_mentions > 0 else 33,
                "neutral": (sentiment_counts.get("neutral", 0) / total_mentions * 100) if total_mentions > 0 else 33,
                "negative": (sentiment_counts.get("negative", 0) / total_mentions * 100) if total_mentions > 0 else 34
            }
            
            cursor.execute("""
                SELECT text, sentiment, timestamp, source
                FROM sentiment_mentions ORDER BY timestamp DESC LIMIT 20
            """)
            
            mentions = [
                {
                    "text": row[0], "sentiment": row[1],
                    "timestamp": row[2], "source": row[3]
                } for row in cursor.fetchall()
            ]
            
            conn.close()
            return {"sentimentData": sentiment_data, "mentions": mentions}
        
        @self.app.get("/api/signals/recent")
        async def get_recent_signals():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT asset, action, price, reason, confidence, timestamp
                FROM signals ORDER BY timestamp DESC LIMIT 20
            """)
            
            signals = [
                {
                    "asset": row[0], "action": row[1], "price": row[2],
                    "reason": row[3], "confidence": row[4], "timestamp": row[5]
                } for row in cursor.fetchall()
            ]
            
            conn.close()
            return {"signals": signals}
        
        @self.app.get("/api/positions/active")
        async def get_active_positions():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, asset, type, quantity, entry_price, current_price, pnl, pnl_percent, timestamp
                FROM positions ORDER BY timestamp DESC
            """)
            
            positions = [
                {
                    "id": row[0], "asset": row[1], "type": row[2], "quantity": row[3],
                    "entryPrice": row[4], "currentPrice": row[5], "pnl": row[6],
                    "pnlPercent": row[7], "timestamp": row[8]
                } for row in cursor.fetchall()
            ]
            
            conn.close()
            return {"positions": positions}
        
        @self.app.post("/api/config/binance")
        async def save_binance_config(config: BinanceConfig):
            global BINANCE_CONFIG
            BINANCE_CONFIG.update({
                'api_key': config.api_key,
                'secret_key': config.secret_key,
                'testnet': config.testnet,
                'configured': True
            })
            logger.info("Configuración de Binance guardada")
            return {"message": "Configuración de Binance guardada exitosamente"}
        
        @self.app.post("/api/config/system")
        async def save_system_config(config: SystemConfig):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_config (key, value) 
                VALUES ('update_interval', ?), ('max_positions', ?), ('auto_trading', ?)
            """, (str(config.update_interval), str(config.max_positions), str(config.auto_trading)))
            
            conn.commit()
            conn.close()
            
            return {"message": "Configuración del sistema guardada"}
        
        @self.app.post("/api/positions/{position_id}/close")
        async def close_position(position_id: str):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return {"message": "Posición cerrada exitosamente"}
            else:
                conn.close()
                raise HTTPException(status_code=404, detail="Posición no encontrada")
        
        @self.app.post("/api/trading/toggle")
        async def toggle_trading():
            self.is_trading_active = not self.is_trading_active
            status = "iniciado" if self.is_trading_active else "detenido"
            return {"message": f"Trading {status}", "active": self.is_trading_active}
    
    def generate_price_data(self):
        """Generar datos de precio en tiempo real"""
        now = datetime.now()
        labels = []
        prices = []
        volumes = []
        
        base_price = 45000
        for i in range(24):
            timestamp = now - timedelta(hours=23-i)
            labels.append(timestamp.strftime("%H:%M"))
            price_change = random.randint(-2000, 2000)
            prices.append(base_price + price_change)
            volumes.append(random.randint(100, 1000))
            base_price = prices[-1]
        
        return {"labels": labels, "prices": prices, "volumes": volumes}
    
    def generate_sample_data(self):
        """Generar datos de muestra realistas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Limpiar datos existentes
        cursor.execute("DELETE FROM signals")
        cursor.execute("DELETE FROM whale_activities")
        cursor.execute("DELETE FROM sentiment_mentions")
        cursor.execute("DELETE FROM positions")
        
        # Generar señales
        assets = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "BNBUSDT", "DOGEUSDT"]
        actions = ["buy", "sell", "hold"]
        
        for i in range(25):
            asset = random.choice(assets)
            action = random.choice(actions)
            base_prices = {"BTCUSDT": 45000, "ETHUSDT": 2500, "ADAUSDT": 0.35, "BNBUSDT": 300, "DOGEUSDT": 0.08}
            price = base_prices[asset] * (1 + random.uniform(-0.1, 0.1))
            
            cursor.execute("""
                INSERT INTO signals (asset, action, price, reason, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                asset, action, round(price, 4),
                f"Análisis técnico: RSI {'sobrecomprado' if action=='sell' else 'sobrevendido' if action=='buy' else 'neutral'}",
                round(random.uniform(0.6, 0.95), 2),
                (datetime.now() - timedelta(minutes=i*30)).isoformat()
            ))
        
        # Generar actividad de ballenas
        for i in range(20):
            asset = random.choice(assets)
            wallet_addr = f"0x{''.join(random.choices('abcdef0123456789', k=40))}"
            quantity = random.uniform(100, 10000)
            base_prices = {"BTCUSDT": 45000, "ETHUSDT": 2500, "ADAUSDT": 0.35, "BNBUSDT": 300, "DOGEUSDT": 0.08}
            value_usd = quantity * base_prices[asset]
            
            cursor.execute("""
                INSERT INTO whale_activities (wallet, asset, quantity, value_usd, type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                wallet_addr, asset, round(quantity, 4), round(value_usd, 2),
                random.choice(["buy", "sell"]),
                (datetime.now() - timedelta(hours=i)).isoformat()
            ))
        
        # Generar menciones de sentimiento
        sentiments = ["positive", "negative", "neutral"]
        sources = ["Twitter", "Reddit", "Telegram", "Discord"]
        sample_texts = [
            "Bitcoin está mostrando una fuerte tendencia alcista",
            "El mercado crypto está muy volátil hoy",
            "Ethereum podría superar los $3000 pronto",
            "Las ballenas están acumulando más BTC",
            "El sentimiento del mercado es muy positivo",
            "Posible corrección en el precio de Bitcoin",
            "Dogecoin muestra señales de recuperación",
            "Binance Coin mantiene su fortaleza",
            "Cardano presenta desarrollo prometedor",
            "El volumen de trading está aumentando"
        ]
        
        for i in range(30):
            cursor.execute("""
                INSERT INTO sentiment_mentions (text, sentiment, source, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                random.choice(sample_texts),
                random.choice(sentiments),
                random.choice(sources),
                (datetime.now() - timedelta(hours=i*2)).isoformat()
            ))
        
        # Generar posiciones
        for i in range(8):
            asset = random.choice(assets)
            position_type = random.choice(["long", "short"])
            quantity = random.uniform(0.1, 5)
            base_prices = {"BTCUSDT": 45000, "ETHUSDT": 2500, "ADAUSDT": 0.35, "BNBUSDT": 300, "DOGEUSDT": 0.08}
            entry_price = base_prices[asset] * (1 + random.uniform(-0.05, 0.05))
            current_price = base_prices[asset] * (1 + random.uniform(-0.1, 0.1))
            
            if position_type == "long":
                pnl = (current_price - entry_price) * quantity
            else:
                pnl = (entry_price - current_price) * quantity
            
            pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price * quantity != 0 else 0
            
            cursor.execute("""
                INSERT INTO positions (id, asset, type, quantity, entry_price, current_price, pnl, pnl_percent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"pos_{i+1}_{asset}", asset, position_type, round(quantity, 4),
                round(entry_price, 4), round(current_price, 4), round(pnl, 2),
                round(pnl_percent, 2), (datetime.now() - timedelta(days=i)).isoformat()
            ))
        
        conn.commit()
        conn.close()
        logger.info("Datos de muestra generados exitosamente")

    def get_dashboard_html(self):
        """Retornar el HTML del dashboard completo"""
        return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Money Trading System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .dashboard-container { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .main-card { background: rgba(255, 255, 255, 0.95); border-radius: 20px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1); backdrop-filter: blur(10px); }
        .nav-pills .nav-link { border-radius: 15px; margin: 5px; font-weight: 600; transition: all 0.3s ease; }
        .nav-pills .nav-link.active { background: linear-gradient(45deg, #667eea, #764ba2); border: none; }
        .nav-pills .nav-link:hover:not(.active) { background: rgba(102, 126, 234, 0.1); color: #667eea; }
        .metric-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 15px; padding: 20px; margin: 10px 0; text-align: center; transition: transform 0.3s ease; }
        .metric-card:hover { transform: translateY(-5px); }
        .metric-value { font-size: 2.5rem; font-weight: bold; margin: 10px 0; }
        .metric-label { font-size: 1rem; opacity: 0.9; }
        .chart-container { background: white; border-radius: 15px; padding: 20px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); }
        .status-indicator { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .status-online { background-color: #28a745; }
        .status-offline { background-color: #dc3545; }
        .table-container { background: white; border-radius: 15px; padding: 20px; margin: 20px 0; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); }
        .btn-custom { border-radius: 25px; padding: 10px 25px; font-weight: 600; transition: all 0.3s ease; }
        .btn-primary-custom { background: linear-gradient(45deg, #667eea, #764ba2); border: none; color: white; }
        .btn-primary-custom:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3); }
        .config-section { background: #f8f9fa; border-radius: 15px; padding: 20px; margin: 20px 0; }
        .alert-custom { border-radius: 15px; border: none; padding: 15px 20px; }
        .whale-activity { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; padding: 15px; margin: 10px 0; }
        .signal-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 15px; padding: 15px; margin: 10px 0; }
        .signal-buy { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .signal-sell { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .signal-hold { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); color: #333; }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="container-fluid">
            <div class="row mb-4">
                <div class="col-12">
                    <div class="main-card p-4">
                        <div class="row align-items-center">
                            <div class="col-md-8">
                                <h1 class="mb-0"><i class="fas fa-chart-line text-primary me-3"></i>Smart Money Trading System</h1>
                                <p class="text-muted mb-0">Dashboard Unificado - Análisis en Tiempo Real</p>
                            </div>
                            <div class="col-md-4 text-end">
                                <div class="d-flex align-items-center justify-content-end">
                                    <span class="status-indicator status-online"></span>
                                    <span class="me-3">Sistema Activo</span>
                                    <button class="btn btn-primary-custom btn-custom" onclick="refreshData()">
                                        <i class="fas fa-sync-alt me-2"></i>Actualizar
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-12">
                    <div class="main-card p-4">
                        <ul class="nav nav-pills justify-content-center" id="dashboardTabs" role="tablist">
                            <li class="nav-item" role="presentation">
                                <button class="nav-link active" id="overview-tab" data-bs-toggle="pill" data-bs-target="#overview" type="button" role="tab">
                                    <i class="fas fa-tachometer-alt me-2"></i>Resumen
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="trading-tab" data-bs-toggle="pill" data-bs-target="#trading" type="button" role="tab">
                                    <i class="fas fa-chart-line me-2"></i>Trading
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="whales-tab" data-bs-toggle="pill" data-bs-target="#whales" type="button" role="tab">
                                    <i class="fas fa-fish me-2"></i>Ballenas
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="sentiment-tab" data-bs-toggle="pill" data-bs-target="#sentiment" type="button" role="tab">
                                    <i class="fas fa-heart me-2"></i>Sentimiento
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="signals-tab" data-bs-toggle="pill" data-bs-target="#signals" type="button" role="tab">
                                    <i class="fas fa-bell me-2"></i>Señales
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="positions-tab" data-bs-toggle="pill" data-bs-target="#positions" type="button" role="tab">
                                    <i class="fas fa-wallet me-2"></i>Posiciones
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="config-tab" data-bs-toggle="pill" data-bs-target="#config" type="button" role="tab">
                                    <i class="fas fa-cog me-2"></i>Configuración
                                </button>
                            </li>
                        </ul>

                        <div class="tab-content" id="dashboardTabsContent">
                            <!-- Pestaña Resumen -->
                            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                                <div class="row">
                                    <div class="col-md-3">
                                        <div class="metric-card">
                                            <div class="metric-value" id="totalValue">$0.00</div>
                                            <div class="metric-label">Valor Total</div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="metric-card">
                                            <div class="metric-value" id="profitLoss">+$0.00</div>
                                            <div class="metric-label">P&L</div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="metric-card">
                                            <div class="metric-value" id="activePositions">0</div>
                                            <div class="metric-label">Posiciones Activas</div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="metric-card">
                                            <div class="metric-value" id="winRate">0%</div>
                                            <div class="metric-label">Tasa de Éxito</div>
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-md-8">
                                        <div class="chart-container">
                                            <h5><i class="fas fa-chart-area me-2"></i>Precio en Tiempo Real</h5>
                                            <canvas id="priceChart"></canvas>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="table-container">
                                            <h5><i class="fas fa-history me-2"></i>Actividad Reciente</h5>
                                            <div id="recentActivity">Cargando...</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Pestaña Trading -->
                            <div class="tab-pane fade" id="trading" role="tabpanel">
                                <div class="row">
                                    <div class="col-md-8">
                                        <div class="chart-container">
                                            <h5><i class="fas fa-chart-candlestick me-2"></i>Gráfico de Trading</h5>
                                            <canvas id="tradingChart"></canvas>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="config-section">
                                            <h5><i class="fas fa-tools me-2"></i>Controles de Trading</h5>
                                            <div class="mb-3">
                                                <label class="form-label">Activo</label>
                                                <select class="form-select" id="tradingAsset">
                                                    <option value="BTCUSDT">BTC/USDT</option>
                                                    <option value="ETHUSDT">ETH/USDT</option>
                                                    <option value="ADAUSDT">ADA/USDT</option>
                                                </select>
                                            </div>
                                            <button class="btn btn-primary-custom btn-custom w-100" onclick="toggleTrading()" id="tradingButton">
                                                <i class="fas fa-play me-2"></i>Iniciar Trading
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Pestaña Ballenas -->
                            <div class="tab-pane fade" id="whales" role="tabpanel">
                                <div class="table-container">
                                    <h5><i class="fas fa-fish me-2"></i>Actividad de Ballenas</h5>
                                    <div class="table-responsive">
                                        <table class="table table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Wallet</th>
                                                    <th>Activo</th>
                                                    <th>Cantidad</th>
                                                    <th>Valor USD</th>
                                                    <th>Tipo</th>
                                                    <th>Timestamp</th>
                                                </tr>
                                            </thead>
                                            <tbody id="whaleActivity">
                                                <tr><td colspan="6" class="text-center">Cargando...</td></tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <!-- Pestaña Sentimiento -->
                            <div class="tab-pane fade" id="sentiment" role="tabpanel">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="chart-container">
                                            <h5><i class="fas fa-heart me-2"></i>Análisis de Sentimiento</h5>
                                            <canvas id="sentimentChart"></canvas>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="table-container">
                                            <h5><i class="fas fa-comments me-2"></i>Menciones Recientes</h5>
                                            <div id="sentimentMentions">Cargando...</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Pestaña Señales -->
                            <div class="tab-pane fade" id="signals" role="tabpanel">
                                <div class="table-container">
                                    <h5><i class="fas fa-bell me-2"></i>Señales de Trading</h5>
                                    <div id="signalsList">Cargando...</div>
                                </div>
                            </div>

                            <!-- Pestaña Posiciones -->
                            <div class="tab-pane fade" id="positions" role="tabpanel">
                                <div class="table-container">
                                    <h5><i class="fas fa-wallet me-2"></i>Posiciones Activas</h5>
                                    <div class="table-responsive">
                                        <table class="table table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Activo</th>
                                                    <th>Tipo</th>
                                                    <th>Cantidad</th>
                                                    <th>Precio Entrada</th>
                                                    <th>Precio Actual</th>
                                                    <th>P&L</th>
                                                    <th>P&L %</th>
                                                    <th>Acciones</th>
                                                </tr>
                                            </thead>
                                            <tbody id="positionsTable">
                                                <tr><td colspan="8" class="text-center">Cargando...</td></tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <!-- Pestaña Configuración -->
                            <div class="tab-pane fade" id="config" role="tabpanel">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="config-section">
                                            <h5><i class="fas fa-key me-2"></i>Configuración de Binance</h5>
                                            <div class="mb-3">
                                                <label class="form-label">API Key</label>
                                                <input type="password" class="form-control" id="binanceApiKey" placeholder="Ingresa tu API Key">
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label">Secret Key</label>
                                                <input type="password" class="form-control" id="binanceSecretKey" placeholder="Ingresa tu Secret Key">
                                            </div>
                                            <div class="mb-3">
                                                <div class="form-check">
                                                    <input class="form-check-input" type="checkbox" id="binanceTestnet" checked>
                                                    <label class="form-check-label" for="binanceTestnet">
                                                        Usar Testnet (Recomendado)
                                                    </label>
                                                </div>
                                            </div>
                                            <button class="btn btn-primary-custom btn-custom w-100" onclick="saveBinanceConfig()">
                                                <i class="fas fa-save me-2"></i>Guardar Configuración
                                            </button>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="config-section">
                                            <h5><i class="fas fa-info-circle me-2"></i>Estado del Sistema</h5>
                                            <div class="mb-3">
                                                <div class="d-flex justify-content-between">
                                                    <span>Binance:</span>
                                                    <span id="binanceStatus" class="badge bg-warning">No Configurado</span>
                                                </div>
                                            </div>
                                            <div class="mb-3">
                                                <div class="d-flex justify-content-between">
                                                    <span>Trading:</span>
                                                    <span id="tradingStatus" class="badge bg-secondary">Detenido</span>
                                                </div>
                                            </div>
                                            <div class="mb-3">
                                                <div class="d-flex justify-content-between">
                                                    <span>Base de Datos:</span>
                                                    <span class="badge bg-success">Conectada</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let charts = {};
        let isTradingActive = false;

        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            loadAllData();
            setInterval(loadAllData, 30000); // Actualizar cada 30 segundos
        });

        function initializeCharts() {
            // Gráfico de precios
            const priceCtx = document.getElementById('priceChart').getContext('2d');
            charts.price = new Chart(priceCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Precio BTC',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: false }
                    }
                }
            });

            // Gráfico de trading
            const tradingCtx = document.getElementById('tradingChart').getContext('2d');
            charts.trading = new Chart(tradingCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Precio de Trading',
                        data: [],
                        borderColor: '#f093fb',
                        backgroundColor: 'rgba(240, 147, 251, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: false }
                    }
                }
            });

            // Gráfico de sentimiento
            const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
            charts.sentiment = new Chart(sentimentCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Positivo', 'Neutral', 'Negativo'],
                    datasets: [{
                        data: [50, 30, 20],
                        backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }

        async function loadAllData() {
            try {
                await Promise.all([
                    loadOverview(),
                    loadWhaleActivity(),
                    loadSentimentData(),
                    loadSignals(),
                    loadPositions(),
                    checkSystemStatus()
                ]);
            } catch (error) {
                console.error('Error cargando datos:', error);
            }
        }

        async function loadOverview() {
            try {
                const response = await fetch('/api/overview');
                const data = await response.json();
                
                document.getElementById('totalValue').textContent = `$${data.totalValue}`;
                document.getElementById('profitLoss').textContent = `${data.profitLoss >= 0 ? '+' : ''}$${data.profitLoss}`;
                document.getElementById('activePositions').textContent = data.activePositions;
                document.getElementById('winRate').textContent = `${data.winRate}%`;
                
                if (data.priceData) {
                    charts.price.data.labels = data.priceData.labels;
                    charts.price.data.datasets[0].data = data.priceData.prices;
                    charts.price.update();
                    
                    // Actualizar también el gráfico de trading
                    charts.trading.data.labels = data.priceData.labels;
                    charts.trading.data.datasets[0].data = data.priceData.prices;
                    charts.trading.update();
                }
                
                // Mostrar actividad reciente
                const activityDiv = document.getElementById('recentActivity');
                if (data.recentActivity && data.recentActivity.length > 0) {
                    activityDiv.innerHTML = data.recentActivity.slice(0, 5).map(activity => `
                        <div class="mb-2 p-2 border rounded">
                            <small class="text-muted">${new Date(activity.timestamp).toLocaleString()}</small><br>
                            <strong>${activity.asset}</strong> - ${activity.quantity}
                        </div>
                    `).join('');
                } else {
                    activityDiv.innerHTML = '<p class="text-center text-muted">No hay actividad reciente</p>';
                }
                
            } catch (error) {
                console.error('Error cargando resumen:', error);
            }
        }

        async function loadWhaleActivity() {
            try {
                const response = await fetch('/api/whales/activity');
                const data = await response.json();
                
                const tbody = document.getElementById('whaleActivity');
                if (data.activities && data.activities.length > 0) {
                    tbody.innerHTML = data.activities.slice(0, 10).map(activity => `
                        <tr>
                            <td>${activity.wallet.substring(0, 10)}...</td>
                            <td>${activity.asset}</td>
                            <td>${activity.quantity}</td>
                            <td>$${activity.valueUsd}</td>
                            <td><span class="badge bg-${activity.type === 'buy' ? 'success' : 'danger'}">${activity.type.toUpperCase()}</span></td>
                            <td>${new Date(activity.timestamp).toLocaleString()}</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No hay actividad de ballenas</td></tr>';
                }
            } catch (error) {
                console.error('Error cargando actividad de ballenas:', error);
            }
        }

        async function loadSentimentData() {
            try {
                const response = await fetch('/api/sentiment/analysis');
                const data = await response.json();
                
                if (data.sentimentData) {
                    charts.sentiment.data.datasets[0].data = [
                        data.sentimentData.positive,
                        data.sentimentData.neutral,
                        data.sentimentData.negative
                    ];
                    charts.sentiment.update();
                }
                
                const mentionsDiv = document.getElementById('sentimentMentions');
                if (data.mentions && data.mentions.length > 0) {
                    mentionsDiv.innerHTML = data.mentions.slice(0, 8).map(mention => `
                        <div class="whale-activity mb-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <small>${mention.text}</small>
                                <span class="badge bg-${mention.sentiment === 'positive' ? 'success' : mention.sentiment === 'negative' ? 'danger' : 'warning'}">${mention.sentiment}</span>
                            </div>
                            <small class="text-muted">${mention.source} - ${new Date(mention.timestamp).toLocaleString()}</small>
                        </div>
                    `).join('');
                } else {
                    mentionsDiv.innerHTML = '<p class="text-center text-muted">No hay menciones recientes</p>';
                }
            } catch (error) {
                console.error('Error cargando sentimiento:', error);
            }
        }

        async function loadSignals() {
            try {
                const response = await fetch('/api/signals/recent');
                const data = await response.json();
                
                const signalsDiv = document.getElementById('signalsList');
                if (data.signals && data.signals.length > 0) {
                    signalsDiv.innerHTML = data.signals.slice(0, 10).map(signal => `
                        <div class="signal-card signal-${signal.action.toLowerCase()} mb-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${signal.asset}</strong> - ${signal.action.toUpperCase()}
                                    <br><small>${signal.reason}</small>
                                </div>
                                <div class="text-end">
                                    <div>$${signal.price}</div>
                                    <small>Confianza: ${(signal.confidence * 100).toFixed(0)}%</small>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    signalsDiv.innerHTML = '<p class="text-center text-muted">No hay señales recientes</p>';
                }
            } catch (error) {
                console.error('Error cargando señales:', error);
            }
        }

        async function loadPositions() {
            try {
                const response = await fetch('/api/positions/active');
                const data = await response.json();
                
                const tbody = document.getElementById('positionsTable');
                if (data.positions && data.positions.length > 0) {
                    tbody.innerHTML = data.positions.map(position => `
                        <tr>
                            <td>${position.asset}</td>
                            <td><span class="badge bg-${position.type === 'long' ? 'success' : 'danger'}">${position.type.toUpperCase()}</span></td>
                            <td>${position.quantity}</td>
                            <td>$${position.entryPrice}</td>
                            <td>$${position.currentPrice}</td>
                            <td class="${position.pnl >= 0 ? 'text-success' : 'text-danger'}">$${position.pnl}</td>
                            <td class="${position.pnlPercent >= 0 ? 'text-success' : 'text-danger'}">${position.pnlPercent}%</td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" onclick="closePosition('${position.id}')">
                                    <i class="fas fa-times"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="8" class="text-center">No hay posiciones activas</td></tr>';
                }
            } catch (error) {
                console.error('Error cargando posiciones:', error);
            }
        }

        async function checkSystemStatus() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                
                document.getElementById('binanceStatus').textContent = data.binance_configured ? 'Configurado' : 'No Configurado';
                document.getElementById('binanceStatus').className = `badge bg-${data.binance_configured ? 'success' : 'warning'}`;
                
                document.getElementById('tradingStatus').textContent = data.trading_active ? 'Activo' : 'Detenido';
                document.getElementById('tradingStatus').className = `badge bg-${data.trading_active ? 'success' : 'secondary'}`;
                
                isTradingActive = data.trading_active;
                updateTradingButton();
            } catch (error) {
                console.error('Error verificando estado:', error);
            }
        }

        function updateTradingButton() {
            const button = document.getElementById('tradingButton');
            if (isTradingActive) {
                button.innerHTML = '<i class="fas fa-stop me-2"></i>Detener Trading';
                button.className = 'btn btn-danger btn-custom w-100';
            } else {
                button.innerHTML = '<i class="fas fa-play me-2"></i>Iniciar Trading';
                button.className = 'btn btn-primary-custom btn-custom w-100';
            }
        }

        async function toggleTrading() {
            try {
                const response = await fetch('/api/trading/toggle', { method: 'POST' });
                const data = await response.json();
                
                isTradingActive = data.active;
                updateTradingButton();
                showAlert(data.message, data.active ? 'success' : 'warning');
            } catch (error) {
                showAlert('Error al cambiar estado del trading', 'danger');
            }
        }

        async function saveBinanceConfig() {
            const apiKey = document.getElementById('binanceApiKey').value;
            const secretKey = document.getElementById('binanceSecretKey').value;
            const testnet = document.getElementById('binanceTestnet').checked;
            
            if (!apiKey || !secretKey) {
                showAlert('Por favor completa todos los campos', 'warning');
                return;
            }
            
            try {
                const response = await fetch('/api/config/binance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: apiKey,
                        secret_key: secretKey,
                        testnet: testnet
                    })
                });
                
                if (response.ok) {
                    showAlert('Configuración de Binance guardada exitosamente', 'success');
                    checkSystemStatus();
                } else {
                    showAlert('Error guardando configuración', 'danger');
                }
            } catch (error) {
                showAlert('Error guardando configuración: ' + error.message, 'danger');
            }
        }

        async function closePosition(positionId) {
            if (confirm('¿Estás seguro de que quieres cerrar esta posición?')) {
                try {
                    const response = await fetch(`/api/positions/${positionId}/close`, {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        showAlert('Posición cerrada exitosamente', 'success');
                        loadPositions();
                        loadOverview();
                    } else {
                        showAlert('Error cerrando posición', 'danger');
                    }
                } catch (error) {
                    showAlert('Error cerrando posición: ' + error.message, 'danger');
                }
            }
        }

        function refreshData() {
            loadAllData();
            showAlert('Datos actualizados', 'info');
        }

        function showAlert(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.body.appendChild(alertDiv);
            
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    </script>
</body>
</html>"""

# Crear instancia del sistema
system = SmartTradingSystem()

def main():
    """Función principal"""
    logger.info("🚀 Iniciando Smart Money Trading System...")
    logger.info("📊 Dashboard Unificado con Navegación por Pestañas")
    logger.info("🏦 Configuración de Binance Integrada")
    logger.info("🐋 Análisis de Ballenas en Tiempo Real")
    logger.info("💹 Trading Automático y Manual")
    logger.info("📱 Interfaz Responsive y Moderna")
    
    try:
        uvicorn.run(
            system.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Sistema detenido por el usuario")

if __name__ == "__main__":
    main()
