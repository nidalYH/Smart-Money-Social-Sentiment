# 🎯 Smart Money Trading System - Versión Unificada

Sistema de trading avanzado con dashboard unificado, configuración de Binance y análisis en tiempo real.

## ✨ Características Principales

### 🖥️ Dashboard Unificado
- **Navegación por pestañas** - Todas las funcionalidades en una sola pantalla
- **Interfaz responsive** - Funciona en desktop, tablet y móvil
- **Tiempo real** - Actualización automática de datos
- **Gráficos interactivos** - Visualización avanzada con Chart.js

### 🏦 Integración con Binance
- **Configuración fácil** - Script interactivo de configuración
- **Testnet y Producción** - Soporte para ambos entornos
- **API Key segura** - Almacenamiento seguro de credenciales
- **Trading automático** - Ejecución automática de trades

### 🐋 Análisis de Ballenas
- **Seguimiento en tiempo real** - Monitoreo de transacciones grandes
- **Alertas automáticas** - Notificaciones de actividad importante
- **Análisis de patrones** - Identificación de comportamientos

### 💹 Trading Inteligente
- **Señales automáticas** - Generación basada en múltiples indicadores
- **Gestión de riesgo** - Control de posiciones y pérdidas
- **Backtesting** - Prueba de estrategias con datos históricos

### 📊 Análisis de Sentimiento
- **Redes sociales** - Monitoreo de Twitter, Reddit, Telegram
- **IA avanzada** - Análisis de sentimiento con machine learning
- **Correlación** - Relación entre sentimiento y precios

## 🚀 Instalación Rápida

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd smart-money-trading-system
```

### 2. Instalar dependencias
```bash
pip install -r requirements_unified.txt
```

### 3. Configurar Binance
```bash
python setup_binance.py
```

### 4. Iniciar el sistema
```bash
python start_system.py
```

## 📋 Configuración Detallada

### Configuración de Binance

1. **Obtener credenciales**:
   - Ve a [Binance](https://www.binance.com)
   - Inicia sesión en tu cuenta
   - Ve a "API Management" en tu perfil
   - Crea una nueva API Key
   - Copia la API Key y Secret Key

2. **Configurar el sistema**:
   ```bash
   python setup_binance.py
   ```

3. **Verificar configuración**:
   - Abre http://localhost:8000
   - Ve a la pestaña "Configuración"
   - Verifica que Binance esté configurado

### Variables de Entorno

Crea un archivo `.env` con la siguiente configuración:

```env
# Configuración de Binance
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui
BINANCE_TESTNET=true

# Configuración de la base de datos
DATABASE_URL=sqlite:///./unified_trading.db

# Configuración del servidor
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

## 🖥️ Uso del Dashboard

### Pestañas Disponibles

1. **📊 Resumen**
   - Métricas principales del sistema
   - Gráficos de precio y volumen
   - Actividad reciente

2. **💹 Trading**
   - Gráfico de trading interactivo
   - Controles de trading
   - Configuración de activos

3. **🐋 Ballenas**
   - Actividad de ballenas en tiempo real
   - Transacciones grandes
   - Análisis de patrones

4. **💖 Sentimiento**
   - Análisis de sentimiento del mercado
   - Menciones en redes sociales
   - Correlación con precios

5. **🔔 Señales**
   - Señales de trading generadas
   - Recomendaciones de compra/venta
   - Nivel de confianza

6. **💰 Posiciones**
   - Posiciones activas
   - P&L en tiempo real
   - Gestión de posiciones

7. **⚙️ Configuración**
   - Configuración de Binance
   - Parámetros del sistema
   - Configuración de alertas

### Funcionalidades Principales

#### Trading Automático
- Configuración de activos a monitorear
- Intervalos de actualización personalizables
- Límites de posiciones
- Stop loss y take profit automáticos

#### Análisis de Ballenas
- Monitoreo de wallets grandes
- Alertas de transacciones importantes
- Análisis de patrones de comportamiento
- Correlación con movimientos de precio

#### Análisis de Sentimiento
- Monitoreo de redes sociales
- Análisis de IA del sentimiento
- Correlación con movimientos de precio
- Alertas de cambios de sentimiento

## 🔧 API Endpoints

### Endpoints Principales

- `GET /` - Dashboard principal
- `GET /health` - Health check
- `GET /api/overview` - Datos del resumen
- `GET /api/trading/status` - Estado del trading
- `GET /api/whales/activity` - Actividad de ballenas
- `GET /api/sentiment/analysis` - Análisis de sentimiento
- `GET /api/signals/recent` - Señales recientes
- `GET /api/positions/active` - Posiciones activas

### Endpoints de Configuración

- `POST /api/config/binance` - Configurar Binance
- `POST /api/config/system` - Configurar sistema
- `POST /api/positions/{id}/close` - Cerrar posición

## 📊 Estructura del Proyecto

```
smart-money-trading-system/
├── unified_trading_system.py      # Sistema principal
├── setup_binance.py              # Configuración de Binance
├── start_system.py               # Script de inicio
├── requirements_unified.txt      # Dependencias
├── config/
│   └── binance_config.py         # Configuración de Binance
├── templates/
│   └── unified_dashboard.html    # Dashboard HTML
├── logs/                         # Archivos de log
├── unified_trading.db            # Base de datos SQLite
└── README_UNIFIED.md            # Este archivo
```

## 🛡️ Seguridad

### Mejores Prácticas

1. **API Keys**:
   - Nunca compartas tus API Keys
   - Usa testnet para desarrollo
   - Restringe permisos de la API Key

2. **Configuración**:
   - Mantén el archivo `.env` privado
   - No subas credenciales al repositorio
   - Usa variables de entorno en producción

3. **Trading**:
   - Comienza con cantidades pequeñas
   - Usa stop loss siempre
   - Monitorea tus posiciones regularmente

## 🐛 Solución de Problemas

### Problemas Comunes

1. **Error de conexión a Binance**:
   - Verifica tus credenciales
   - Asegúrate de que la API Key esté activa
   - Verifica que no estés en una IP restringida

2. **Dashboard no carga**:
   - Verifica que el puerto 8000 esté libre
   - Revisa los logs en `logs/unified_system.log`
   - Reinicia el sistema

3. **Datos no se actualizan**:
   - Verifica la conexión a internet
   - Revisa la configuración de Binance
   - Verifica los logs de error

### Logs

Los logs se guardan en:
- `logs/unified_system.log` - Log principal del sistema
- `logs/binance.log` - Log de operaciones de Binance
- `logs/trading.log` - Log de operaciones de trading

## 📈 Rendimiento

### Optimizaciones

1. **Base de datos**:
   - Índices en campos frecuentemente consultados
   - Limpieza periódica de datos antiguos
   - Compresión de datos históricos

2. **API**:
   - Cache de respuestas frecuentes
   - Paginación de resultados grandes
   - Compresión de respuestas

3. **Frontend**:
   - Actualización incremental de datos
   - Lazy loading de componentes
   - Optimización de gráficos

## 🔄 Actualizaciones

### Actualizar el Sistema

1. **Backup**:
   ```bash
   cp unified_trading.db unified_trading.db.backup
   ```

2. **Actualizar código**:
   ```bash
   git pull origin main
   pip install -r requirements_unified.txt
   ```

3. **Reiniciar sistema**:
   ```bash
   python start_system.py
   ```

## 📞 Soporte

### Recursos

- **Documentación**: Este README
- **Issues**: GitHub Issues
- **Logs**: Directorio `logs/`
- **Configuración**: Archivo `.env`

### Contacto

Para soporte técnico o preguntas:
- Crea un issue en GitHub
- Revisa los logs de error
- Verifica la configuración

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

## ⚠️ Disclaimer

Este software es para fines educativos y de investigación. El trading de criptomonedas conlleva riesgos significativos. Siempre:

- Usa testnet para pruebas
- Comienza con cantidades pequeñas
- No inviertas más de lo que puedes permitirte perder
- Consulta con un asesor financiero profesional

---

## 🎉 ¡Disfruta del Trading!

¡Tu sistema de trading inteligente está listo! Navega por las pestañas del dashboard para explorar todas las funcionalidades disponibles.

**¡Happy Trading! 🚀📈💰**
