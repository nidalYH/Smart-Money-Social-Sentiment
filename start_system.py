"""
Script de inicio rápido del Smart Money Trading System
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_requirements():
    """Verificar que los requisitos estén instalados"""
    print("🔍 Verificando requisitos...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'jinja2',
        'pandas',
        'numpy',
        'requests',
        'python-binance'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - FALTANTE")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Instalando paquetes faltantes: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 
                '-r', 'requirements_unified.txt'
            ])
            print("✅ Paquetes instalados exitosamente")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando paquetes: {e}")
            return False
    
    return True

def check_configuration():
    """Verificar configuración"""
    print("\n🔧 Verificando configuración...")
    
    # Verificar archivo .env
    if not os.path.exists('.env'):
        print("❌ Archivo .env no encontrado")
        print("💡 Ejecuta: python setup_binance.py")
        return False
    
    # Verificar directorio de logs
    if not os.path.exists('logs'):
        os.makedirs('logs', exist_ok=True)
        print("✅ Directorio de logs creado")
    
    # Verificar directorio de templates
    if not os.path.exists('templates'):
        os.makedirs('templates', exist_ok=True)
        print("✅ Directorio de templates creado")
    
    print("✅ Configuración verificada")
    return True

def start_system():
    """Iniciar el sistema"""
    print("\n🚀 Iniciando Smart Money Trading System...")
    print("=" * 60)
    print()
    print("📊 Dashboard Unificado con Navegación por Pestañas")
    print("🏦 Configuración de Binance Integrada")
    print("🐋 Análisis de Ballenas en Tiempo Real")
    print("💹 Trading Automático y Manual")
    print("📱 Interfaz Responsive y Moderna")
    print()
    print("🌐 Acceso al Sistema:")
    print("   📊 Dashboard: http://localhost:8000")
    print("   ❤️  Health Check: http://localhost:8000/health")
    print("   📚 API Docs: http://localhost:8000/docs")
    print()
    print("⌨️  Presiona Ctrl+C para detener el sistema")
    print("=" * 60)
    print()
    
    try:
        # Iniciar el sistema
        subprocess.run([
            sys.executable, 'unified_trading_system.py'
        ])
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error iniciando el sistema: {e}")

def main():
    """Función principal"""
    print("🎯 SMART MONEY TRADING SYSTEM - INICIO RÁPIDO")
    print("=" * 60)
    print()
    
    # Verificar requisitos
    if not check_requirements():
        print("\n❌ No se pudieron instalar todos los requisitos")
        print("💡 Instala manualmente: pip install -r requirements_unified.txt")
        return
    
    # Verificar configuración
    if not check_configuration():
        print("\n❌ Configuración incompleta")
        print("💡 Ejecuta: python setup_binance.py")
        return
    
    # Iniciar sistema
    start_system()

if __name__ == "__main__":
    main()