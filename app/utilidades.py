import io
import re

import streamlit as st
from PIL import Image, ImageOps

from config import BUCKET, supabase

LIMITE_BYTES = 800 * 1024


def normalizar_patente(patente):
    patente = re.sub(r"[^A-Z0-9]", "", patente.upper())
    if len(patente) == 6:
        return f"{patente[:4]}-{patente[4:]}"
    return patente


def normalizar_rut(rut):
    rut = rut.strip().upper().replace(".", "").replace("-", "").replace(" ", "")
    if len(rut) < 2 or not rut[:-1].isdigit() or rut[-1] not in "0123456789K":
        return None
    numero = f"{int(rut[:-1]):,}".replace(",", ".")
    return f"{numero}-{rut[-1]}"


def comprimir_foto(contenido):
    """Redimensiona y recomprime a JPEG hasta quedar bajo 800 KB."""
    with Image.open(io.BytesIO(contenido)) as imagen_original:
        imagen = ImageOps.exif_transpose(imagen_original).convert("RGB")

    imagen.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
    calidad = 85
    while True:
        buffer = io.BytesIO()
        imagen.save(buffer, format="JPEG", quality=calidad, optimize=True)
        foto_comprimida = buffer.getvalue()
        if len(foto_comprimida) <= LIMITE_BYTES:
            return foto_comprimida

        if calidad > 35:
            calidad -= 10
            continue

        ancho, alto = imagen.size
        if max(ancho, alto) <= 320:
            raise ValueError("No se pudo comprimir la fotografía a 800 KB o menos.")

        imagen = imagen.resize(
            (max(1, int(ancho * 0.8)), max(1, int(alto * 0.8))),
            Image.Resampling.LANCZOS,
        )
        calidad = 80


@st.cache_data(ttl=3000, show_spinner=False)
def url_foto(ruta):
    """URL firmada y temporal de una evidencia del bucket privado."""
    try:
        respuesta = supabase.storage.from_(BUCKET).create_signed_url(ruta, 3600)
        return respuesta.get("signedURL") or respuesta.get("signedUrl")
    except Exception:
        return None
