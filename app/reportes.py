from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from config import BUCKET, consultar, supabase
from utilidades import comprimir_foto

OPCIONES_NEUMATICOS = ["Óptimo", "Baja presión", "Baja presión severa"]
OPCIONES_FRENOS = ["Operativo", "Con falla"]


def guardar_reporte(patente, rut, tipo_registro, kilometraje, combustible,
                    estado_neumaticos, estado_frenos, luces, observaciones, foto):
    """Sube la foto, inserta el reporte y muestra el resultado.

    Si el reporte es critico, el trigger trg_aplicar_reporte (database/schema.sql)
    cambia el vehiculo a 'Requiere Mantención'. Aqui se vuelve a leer el
    vehiculo para informar el estado resultante.
    """
    if foto is None:
        st.error("Debe adjuntar una fotografía como evidencia.")
        return

    bucket = supabase.storage.from_(BUCKET)
    ruta_foto = f"{patente}/{uuid4().hex}.jpg"
    foto_subida = False
    try:
        foto_comprimida = comprimir_foto(foto.getvalue())
        bucket.upload(
            ruta_foto,
            foto_comprimida,
            file_options={"content-type": "image/jpeg", "upsert": "false"},
        )
        foto_subida = True
        supabase.table("reportes_estado").insert(
            {
                "patente": patente,
                "rut_conductor": rut,
                "fecha_reporte": datetime.now(timezone.utc).isoformat(),
                "tipo_registro": tipo_registro,
                "kilometraje_salida": kilometraje,
                "nivel_combustible": combustible,
                "presion_neumaticos": estado_neumaticos == "Óptimo",
                "luces_operativas": luces,
                "estado_frenos": estado_frenos,
                "estado_neumaticos": estado_neumaticos,
                "observaciones": observaciones.strip() or None,
                "foto_evidencia_url": ruta_foto,
            }
        ).execute()
    except Exception as error:
        if foto_subida:
            try:
                bucket.remove([ruta_foto])
            except Exception as error_limpieza:
                st.error(f"No se pudo eliminar la evidencia sin registro: {error_limpieza}")
        st.error(f"No se pudo guardar el registro: {error}")
        return

    st.success(
        f"Registro guardado. Evidencia comprimida a {len(foto_comprimida) // 1024} KB."
    )
    critico = estado_frenos == "Con falla" or estado_neumaticos == "Baja presión severa"
    if critico:
        vehiculos = consultar("vehiculos", filtros={"patente": patente}, limite=1)
        estado = vehiculos[0]["estado_operativo"] if vehiculos else "desconocido"
        st.error(
            f"Parámetro crítico reportado. El vehículo {patente} quedó en estado: {estado}."
        )
    elif not luces or estado_neumaticos != "Óptimo":
        st.warning("Se reportaron novedades en luces o neumáticos.")
    else:
        st.success("Estado reportado como óptimo.")
