import streamlit as st
from supabase import Client, create_client

BUCKET = "evidencias-vehiculares"

try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
except (KeyError, FileNotFoundError):
    st.error(
        "No se encontraron las credenciales de Supabase. "
        "Cree .streamlit/secrets.toml a partir de secrets.toml.example."
    )
    st.stop()


@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase: Client = init_supabase()


def consultar(tabla, columnas="*", filtros=None, orden=None, limite=None):
    """Consulta simple con filtros de igualdad. Devuelve None si hay error."""
    try:
        consulta = supabase.table(tabla).select(columnas)
        for columna, valor in (filtros or {}).items():
            consulta = consulta.eq(columna, valor)
        if orden:
            consulta = consulta.order(orden[0], desc=orden[1])
        if limite:
            consulta = consulta.limit(limite)
        return consulta.execute().data
    except Exception as error:
        st.error(f"No se pudo consultar la tabla {tabla}: {error}")
        return None
