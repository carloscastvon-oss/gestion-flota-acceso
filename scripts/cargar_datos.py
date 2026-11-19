"""Carga los datos iniciales en Supabase (despues de ejecutar database/schema.sql).

Uso, desde la raiz del proyecto:
    python scripts/cargar_datos.py

Lee las credenciales de .streamlit/secrets.toml. Es repetible: usa upsert
sobre las llaves naturales (patente, rut).
"""
import tomllib
from pathlib import Path

import pandas as pd
from supabase import create_client

RAIZ = Path(__file__).resolve().parent.parent


def leer_csv(nombre):
    datos = pd.read_csv(RAIZ / "data" / f"{nombre}.csv", encoding="utf-8-sig")
    return datos.drop(columns=["id"]).astype(object).where(datos.notna(), None)


def registros(datos):
    return datos.to_dict(orient="records")


def main():
    with open(RAIZ / ".streamlit" / "secrets.toml", "rb") as archivo:
        secretos = tomllib.load(archivo)["supabase"]
    supabase = create_client(secretos["url"], secretos["key"])

    supabase.table("vehiculos").upsert(
        registros(leer_csv("vehiculos")), on_conflict="patente"
    ).execute()
    supabase.table("conductores").upsert(
        registros(leer_csv("conductores")), on_conflict="rut"
    ).execute()
    supabase.table("autorizaciones").upsert(
        registros(leer_csv("autorizaciones")), on_conflict="patente,rut_conductor"
    ).execute()

    existentes = supabase.table("reportes_estado").select("id").limit(1).execute().data
    if not existentes:
        reportes = leer_csv("reportes_estado")
        reportes["estado_frenos"] = reportes["observaciones"].map(
            lambda texto: "Con falla" if texto and "FRENOS" in texto.upper() else "Operativo"
        )
        supabase.table("reportes_estado").insert(registros(reportes)).execute()

    for tabla in ["vehiculos", "conductores", "autorizaciones", "reportes_estado"]:
        total = supabase.table(tabla).select("id", count="exact").limit(1).execute().count
        print(f"{tabla}: {total} registros")


if __name__ == "__main__":
    main()
