"""Exporta las tablas de Supabase a CSV (script de la clase, usando secrets.toml).

Uso, desde la raiz del proyecto:
    python scripts/exportar_tablas.py
"""
import tomllib
from pathlib import Path

import pandas as pd
from supabase import create_client

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = ["conductores", "vehiculos", "autorizaciones", "reportes_estado"]

with open(RAIZ / ".streamlit" / "secrets.toml", "rb") as archivo:
    secretos = tomllib.load(archivo)["supabase"]
supabase = create_client(secretos["url"], secretos["key"])

for tabla in TABLAS:
    datos = supabase.table(tabla).select("*").execute().data
    if datos:
        pd.DataFrame(datos).to_csv(
            RAIZ / "data" / f"{tabla}.csv", index=False, encoding="utf-8-sig"
        )
        print(f"Tabla {tabla} descargada correctamente.")
    else:
        print(f"La tabla {tabla} esta vacia.")
