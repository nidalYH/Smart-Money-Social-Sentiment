#!/usr/bin/env python3
"""
Script para agregar carteras de ballenas a la base de datos
"""
import asyncio
import logging
from datetime import datetime
from app.core.data_manager import DataManager
from app.models.whale import WhaleWallet

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lista de carteras de ballenas proporcionadas
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

async def add_whale_wallets():
    """Agregar carteras de ballenas a la base de datos"""
    try:
        # Inicializar data manager
        data_manager = DataManager()
        await data_manager.initialize()
        
        logger.info(f"Agregando {len(WHALE_WALLETS)} carteras de ballenas...")
        
        async with data_manager.get_db_session() as session:
            added_count = 0
            existing_count = 0
            
            for wallet_address in WHALE_WALLETS:
                try:
                    # Verificar si la cartera ya existe
                    from sqlalchemy import select
                    stmt = select(WhaleWallet).where(WhaleWallet.address == wallet_address)
                    result = await session.execute(stmt)
                    existing_wallet = result.scalar_one_or_none()
                    
                    if existing_wallet:
                        logger.info(f"Cartera {wallet_address} ya existe")
                        existing_count += 1
                        continue
                    
                    # Crear nueva cartera de ballena
                    whale_wallet = WhaleWallet(
                        address=wallet_address,
                        label=f"Whale Wallet {wallet_address[:8]}...",
                        is_active=True,
                        total_value_usd=0.0,  # Se actualizará cuando se obtengan datos
                        last_activity=datetime.utcnow(),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        notes="Added via script"
                    )
                    
                    session.add(whale_wallet)
                    added_count += 1
                    logger.info(f"Agregada cartera: {wallet_address}")
                    
                except Exception as e:
                    logger.error(f"Error agregando cartera {wallet_address}: {e}")
                    continue
            
            # Confirmar cambios
            await session.commit()
            
            logger.info(f"✅ Proceso completado:")
            logger.info(f"   - Carteras agregadas: {added_count}")
            logger.info(f"   - Carteras existentes: {existing_count}")
            logger.info(f"   - Total procesadas: {len(WHALE_WALLETS)}")
            
    except Exception as e:
        logger.error(f"Error en el proceso: {e}")
    finally:
        if 'data_manager' in locals():
            await data_manager.close()

async def main():
    """Función principal"""
    print("🐋 Agregando Carteras de Ballenas al Sistema de Trading")
    print("=" * 60)
    
    await add_whale_wallets()
    
    print("=" * 60)
    print("✅ Proceso completado exitosamente")

if __name__ == "__main__":
    asyncio.run(main())
