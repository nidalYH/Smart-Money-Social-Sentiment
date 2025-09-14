"""
Script de configuración rápida de Binance
"""

import os
import sys
from pathlib import Path

def setup_binance_credentials():
    """Configurar credenciales de Binance de forma interactiva"""
    
    print("🏦 CONFIGURACIÓN DE BINANCE")
    print("=" * 50)
    print()
    
    print("Para obtener tus credenciales de Binance:")
    print("1. Ve a https://www.binance.com")
    print("2. Inicia sesión en tu cuenta")
    print("3. Ve a 'API Management' en tu perfil")
    print("4. Crea una nueva API Key")
    print("5. Copia la API Key y Secret Key")
    print()
    
    # Configuración de API Key
    api_key = input("Ingresa tu API Key de Binance: ").strip()
    if not api_key:
        print("❌ API Key es requerida")
        return False
    
    # Configuración de Secret Key
    secret_key = input("Ingresa tu Secret Key de Binance: ").strip()
    if not secret_key:
        print("❌ Secret Key es requerida")
        return False
    
    # Configuración de Testnet
    testnet_input = input("¿Usar Testnet? (s/n) [s]: ").strip().lower()
    use_testnet = testnet_input in ['', 's', 'si', 'sí', 'y', 'yes']
    
    # Crear archivo .env
    env_content = f"""# Configuración de Binance
BINANCE_API_KEY={api_key}
BINANCE_SECRET_KEY={secret_key}
BINANCE_TESTNET={str(use_testnet).lower()}

# Configuración de la base de datos
DATABASE_URL=sqlite:///./unified_trading.db

# Configuración del servidor
HOST=0.0.0.0
PORT=8000
DEBUG=true
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print()
        print("✅ Configuración guardada exitosamente")
        print(f"📁 Archivo creado: .env")
        print(f"🔧 Testnet: {'Activado' if use_testnet else 'Desactivado'}")
        print()
        
        if use_testnet:
            print("🧪 MODO TESTNET ACTIVADO")
            print("   - Usarás el entorno de pruebas de Binance")
            print("   - No se realizarán trades reales")
            print("   - Perfecto para testing y desarrollo")
        else:
            print("⚠️  MODO PRODUCCIÓN ACTIVADO")
            print("   - Se realizarán trades reales")
            print("   - Usa con precaución")
            print("   - Verifica tu configuración antes de continuar")
        
        print()
        print("🚀 Para iniciar el sistema:")
        print("   python unified_trading_system.py")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando configuración: {e}")
        return False

def test_binance_connection():
    """Probar conexión con Binance"""
    try:
        from config.binance_config import binance_config
        
        if binance_config.is_configured():
            print("✅ Binance configurado correctamente")
            print(f"🔗 URL Base: {binance_config.base_url}")
            print(f"🧪 Testnet: {'Sí' if binance_config.testnet else 'No'}")
            return True
        else:
            print("❌ Binance no está configurado")
            return False
            
    except ImportError:
        print("❌ No se pudo importar la configuración de Binance")
        return False
    except Exception as e:
        print(f"❌ Error probando conexión: {e}")
        return False

def main():
    """Función principal"""
    print("🎯 SMART MONEY TRADING SYSTEM - CONFIGURACIÓN")
    print("=" * 60)
    print()
    
    # Verificar si ya existe configuración
    if os.path.exists('.env'):
        print("📁 Archivo .env encontrado")
        overwrite = input("¿Sobrescribir configuración existente? (s/n) [n]: ").strip().lower()
        if overwrite not in ['s', 'si', 'sí', 'y', 'yes']:
            print("✅ Configuración existente mantenida")
            test_binance_connection()
            return
    
    # Configurar credenciales
    if setup_binance_credentials():
        print()
        print("🧪 Probando configuración...")
        test_binance_connection()
    
    print()
    print("📚 PRÓXIMOS PASOS:")
    print("1. Ejecuta: python unified_trading_system.py")
    print("2. Abre tu navegador en: http://localhost:8000")
    print("3. Ve a la pestaña 'Configuración' para verificar")
    print("4. Comienza a usar el sistema de trading")
    print()
    print("🎉 ¡Configuración completada!")

if __name__ == "__main__":
    main()
