"""
Configuración de Binance para Smart Money Trading System
"""

import os
from typing import Dict, Any

class BinanceConfig:
    """Configuración centralizada para Binance"""
    
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY', '')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY', '')
        self.testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        self.base_url = self._get_base_url()
        
    def _get_base_url(self) -> str:
        """Obtiene la URL base según el entorno"""
        if self.testnet:
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
    
    def is_configured(self) -> bool:
        """Verifica si Binance está configurado"""
        return bool(self.api_key and self.secret_key)
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración completa"""
        return {
            'api_key': self.api_key,
            'secret_key': self.secret_key,
            'testnet': self.testnet,
            'base_url': self.base_url,
            'is_configured': self.is_configured()
        }
    
    def get_headers(self) -> Dict[str, str]:
        """Retorna los headers para las peticiones"""
        return {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }

# Instancia global
binance_config = BinanceConfig()

# Configuración por defecto para testing
DEFAULT_BINANCE_CONFIG = {
    'api_key': 'tu_api_key_aqui',
    'secret_key': 'tu_secret_key_aqui',
    'testnet': True,
    'base_url': 'https://testnet.binance.vision',
    'is_configured': False
}

def setup_binance_credentials(api_key: str, secret_key: str, testnet: bool = True):
    """Configura las credenciales de Binance"""
    os.environ['BINANCE_API_KEY'] = api_key
    os.environ['BINANCE_SECRET_KEY'] = secret_key
    os.environ['BINANCE_TESTNET'] = str(testnet).lower()
    
    # Recargar configuración
    global binance_config
    binance_config = BinanceConfig()
    
    return binance_config.get_config()
