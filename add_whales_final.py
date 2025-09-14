#!/usr/bin/env python3
"""
Script final para agregar carteras de ballenas usando la estructura real de la tabla
"""
import sqlite3
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lista de carteras de ballenas
WHALE_WALLETS = [
    "CWvdyvKHEu8Z6QqGraJT3sLPyp9bJfFhoXcxUYRKC8ou",
    "5q7Xwc2T57sK1DKU6zuwVXvMPsxqB2xrJ3T5AonFYtcY", 
    "5CP6zv8a17mz91v6rMruVH6ziC5qAL8GFaJzwrX9Fvup",
    "8xucMh5W5qAgNfpXQ7z8xgs3T5uDrDrtbTSPanhGgBb",
    "3JPYL9xEPFjefV3tccrUwhLzME1mMq2dQSDeDebgzQi6",
    "EbNr5s54pCUFzEyBDjJWwqYQc7R5E8udmPEpDLwpbjKq",
    "CtGmga4qsW59fd4GCUB287bBQbAUH7A4jibCG3o3Uspr",
    "3QJs9g2JPruNx6p4cgdKZ1uw22iDP59R9uC64f9E4fhV",
    "G9fmyVHqWS94YRfyQjYVUdf8oPufkoxbUWCLiHJyR8Br",
    "vHRSMB5mSEYJvwiW55fHquPsH67hhGYe4iGPcJchto"
]

def add_whale_wallets():
    """Agregar carteras de ballenas usando la estructura real de la tabla"""
    try:
        # Conectar a la base de datos SQLite
        conn = sqlite3.connect('smartmoney.db')
        cursor = conn.cursor()
        
        logger.info(f"🐋 Agregando {len(WHALE_WALLETS)} carteras de ballenas...")
        
        added_count = 0
        existing_count = 0
        current_time = datetime.utcnow().isoformat()
        
        for i, wallet_address in enumerate(WHALE_WALLETS, 1):
            try:
                # Verificar si la cartera ya existe
                cursor.execute("SELECT id FROM whale_wallets WHERE address = ?", (wallet_address,))
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"  {i:2d}. Cartera {wallet_address} ya existe")
                    existing_count += 1
                    continue
                
                # Insertar nueva cartera usando solo los campos existentes
                cursor.execute("""
                    INSERT INTO whale_wallets (
                        id, address, label, balance_eth, balance_usd, success_rate, 
                        total_profit_loss, avg_hold_time, wallet_type, is_exchange, 
                        is_contract, risk_score, first_seen, last_activity, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"whale_{wallet_address[:8]}",  # id
                    wallet_address,  # address
                    f"Whale Wallet {wallet_address[:8]}...",  # label
                    0.0,  # balance_eth
                    0.0,  # balance_usd
                    0.0,  # success_rate
                    0.0,  # total_profit_loss
                    0,    # avg_hold_time
                    "unknown",  # wallet_type
                    False,  # is_exchange
                    False,  # is_contract
                    0.0,   # risk_score
                    current_time,  # first_seen
                    current_time,  # last_activity
                    True   # is_active
                ))
                
                added_count += 1
                logger.info(f"  {i:2d}. ✅ Agregada: {wallet_address}")
                
            except Exception as e:
                logger.error(f"  {i:2d}. ❌ Error con {wallet_address}: {e}")
                continue
        
        # Confirmar cambios
        conn.commit()
        conn.close()
        
        logger.info(f"\n✅ Proceso completado:")
        logger.info(f"   📊 Carteras agregadas: {added_count}")
        logger.info(f"   📊 Carteras existentes: {existing_count}")
        logger.info(f"   📊 Total procesadas: {len(WHALE_WALLETS)}")
        
        return added_count, existing_count
        
    except Exception as e:
        logger.error(f"❌ Error en el proceso: {e}")
        return 0, 0

def main():
    """Función principal"""
    print("🐋 Agregando Carteras de Ballenas al Sistema de Trading")
    print("=" * 60)
    
    added, existing = add_whale_wallets()
    
    print("=" * 60)
    if added > 0:
        print(f"🎉 ¡ÉXITO! Se agregaron {added} carteras de ballenas")
        print(f"📈 El sistema ahora rastreará estas carteras para señales de trading")
    else:
        print(f"ℹ️  No se agregaron nuevas carteras (ya existían: {existing})")
    
    print(f"📊 Total procesadas: {len(WHALE_WALLETS)}")

if __name__ == "__main__":
    main()
