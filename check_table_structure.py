#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla whale_wallets
"""
import sqlite3

def check_table_structure():
    """Verificar la estructura de la tabla whale_wallets"""
    try:
        conn = sqlite3.connect('smartmoney.db')
        cursor = conn.cursor()
        
        # Obtener información de la tabla
        cursor.execute("PRAGMA table_info(whale_wallets)")
        columns = cursor.fetchall()
        
        print("📋 Estructura de la tabla whale_wallets:")
        print("=" * 50)
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
        
        # Verificar si hay datos
        cursor.execute("SELECT COUNT(*) FROM whale_wallets")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total de registros: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_table_structure()
