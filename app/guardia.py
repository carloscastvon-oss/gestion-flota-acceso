import io

import numpy as np
import streamlit as st
from PIL import Image

from config import consultar, supabase
from reportes import OPCIONES_FRENOS, OPCIONES_NEUMATICOS, guardar_reporte
from utilidades import normalizar_patente, normalizar_rut


@st.cache_resource
def init_ocr():
    import easyocr

    return easyocr.Reader(["es", "en"], gpu=False)


def validar_acceso(patente, rut):
    """Valida conductor y vehiculo en una sola consulta.

    Se parte desde 'autorizaciones' y se incorporan, por sus llaves foraneas,
    el vehiculo y el conductor. Una fila devuelta significa que existe una
    autorizacion vigente para ese par; el estado del conductor y del vehiculo
    se evalua sobre los datos incorporados.
    """
    try:
        return (
            supabase.table("autorizaciones")
            .select("*, vehiculos(*), conductores(*)")
            .eq("patente", patente)
            .eq("rut_conductor", rut)
            .eq("vigente", True)
            .limit(1)
            .execute()
            .data
        )
    except Exception as error:
        st.error(f"No se pudo validar el acceso: {error}")
        return None


def mostrar_resolucion(vehiculo, conductor, patente, rut):
    """Muestra Autorizado / Denegado / Alerta de Estado. Devuelve True si se puede registrar."""
    estado = vehiculo["estado_operativo"]
    if conductor["estado"] != "Activo":
        st.error(f"DENEGADO: el conductor {rut} no se encuentra activo.")
        return False
    if estado == "Crítico":
        st.error(f"DENEGADO: el vehículo {patente} está en estado Crítico.")
        return False
    if estado == "Requiere Mantención":
        st.warning(
            f"ALERTA DE ESTADO: {conductor['nombre_completo']} está autorizado para "
            f"{patente}, pero el vehículo requiere mantención."
        )
        return True
    st.success(f"AUTORIZADO: {conductor['nombre_completo']} para {patente}.")
    return True


def perfil_guardia():
    st.header("Control de acceso vehicular")
    st.caption("Perfil Guardia. Verificación de autorización y registro de movimientos.")

    imagen_patente = st.camera_input("Fotografiar la patente")
    patente_detectada = ""
    if imagen_patente is not None:
        try:
            with st.spinner("Leyendo patente..."):
                resultados = init_ocr().readtext(
                    np.array(Image.open(io.BytesIO(imagen_patente.getvalue())).convert("RGB"))
                )
            if resultados:
                patente_detectada = max(resultados, key=lambda r: r[2])[1]
                st.info(f"Lectura OCR: {patente_detectada}")
            else:
                st.warning("No se detectó una patente. Puede ingresarla manualmente.")
        except Exception as error:
            st.warning(f"No se pudo procesar la imagen con OCR: {error}")

    patente_ingresada = st.text_input(
        "Confirmar o ingresar patente", value=patente_detectada, key="patente_guardia"
    )
    rut_ingresado = st.text_input("RUT del conductor", key="rut_guardia")
    if not patente_ingresada.strip() or not rut_ingresado.strip():
        return

    patente = normalizar_patente(patente_ingresada)
    rut = normalizar_rut(rut_ingresado)
    if rut is None:
        st.warning("Ingrese un RUT válido.")
        return

    resultado = validar_acceso(patente, rut)
    if resultado is None:
        return
    if not resultado:
        # Diagnostico: se indica cual de los tres elementos falla.
        if not consultar("vehiculos", filtros={"patente": patente}, limite=1):
            st.error(f"DENEGADO: la patente {patente} no está registrada.")
        elif not consultar("conductores", filtros={"rut": rut}, limite=1):
            st.error(f"DENEGADO: el RUT {rut} no está registrado.")
        else:
            st.error(f"DENEGADO: {rut} no tiene autorización vigente para {patente}.")
        return

    vehiculo = resultado[0]["vehiculos"]
    conductor = resultado[0]["conductores"]
    st.write(
        f"**{vehiculo['tipo_vehiculo']}** · {vehiculo['marca_modelo']} · "
        f"Estado: **{vehiculo['estado_operativo']}** · "
        f"Kilometraje: **{vehiculo['kilometraje_actual']} km**"
    )
    if not mostrar_resolucion(vehiculo, conductor, patente, rut):
        return

    st.subheader("Registrar movimiento")
    foto_camara = st.camera_input("Fotografía de evidencia del vehículo", key="foto_guardia")
    foto_archivo = st.file_uploader(
        "O adjuntar fotografía desde el dispositivo",
        type=["jpg", "jpeg", "png"],
        key="foto_guardia_archivo",
    )
    with st.form("form_movimiento"):
        movimiento = st.selectbox("Movimiento", ["ENTRADA", "SALIDA"])
        kilometraje = st.number_input(
            "Kilometraje",
            min_value=int(vehiculo["kilometraje_actual"]),
            value=int(vehiculo["kilometraje_actual"]),
            step=1,
        )
        combustible = st.number_input(
            "Combustible (%)", min_value=0, max_value=100, value=50, step=1
        )
        estado_neumaticos = st.selectbox("Neumáticos", OPCIONES_NEUMATICOS)
        estado_frenos = st.selectbox("Frenos", OPCIONES_FRENOS)
        luces = st.checkbox("Luces operativas", value=True)
        observaciones = st.text_area("Observaciones")
        registrar = st.form_submit_button("Confirmar y registrar acceso", type="primary")

    if registrar:
        foto = foto_camara if foto_camara is not None else foto_archivo
        guardar_reporte(
            patente, rut, movimiento, kilometraje, combustible,
            estado_neumaticos, estado_frenos, luces, observaciones, foto,
        )
