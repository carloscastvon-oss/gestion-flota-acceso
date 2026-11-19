import streamlit as st

from config import consultar
from reportes import OPCIONES_FRENOS, OPCIONES_NEUMATICOS, guardar_reporte
from utilidades import normalizar_rut


def perfil_conductor():
    st.header("Bitácora y estado del vehículo")
    st.caption("Perfil Conductor. Reporte periódico de condiciones operativas.")

    rut_ingresado = st.text_input("RUT del conductor", key="rut_conductor")
    if not rut_ingresado.strip():
        st.info("Ingrese su RUT para consultar sus vehículos autorizados.")
        return
    rut = normalizar_rut(rut_ingresado)
    if rut is None:
        st.warning("Ingrese un RUT válido.")
        return

    conductores = consultar("conductores", filtros={"rut": rut}, limite=1)
    if conductores is None:
        return
    if not conductores or conductores[0]["estado"] != "Activo":
        st.error("No se encontró un conductor activo con ese RUT.")
        return
    st.write(f"Conductor: **{conductores[0]['nombre_completo']}**")

    autorizaciones = consultar("autorizaciones", filtros={"rut_conductor": rut, "vigente": True})
    if autorizaciones is None:
        return
    patentes = sorted({registro["patente"] for registro in autorizaciones})
    if not patentes:
        st.warning("No tiene vehículos con autorización vigente.")
        return

    todos_vehiculos = consultar("vehiculos")
    if todos_vehiculos is None:
        return
    vehiculos = {v["patente"]: v for v in todos_vehiculos}
    patentes = [p for p in patentes if p in vehiculos]
    if not patentes:
        st.warning("No se encontraron vehículos asociados a sus autorizaciones.")
        return

    patente = st.selectbox(
        "Vehículo",
        patentes,
        format_func=lambda valor: f"{valor} · {vehiculos[valor]['tipo_vehiculo']}",
    )
    vehiculo = vehiculos[patente]
    st.write(
        f"Kilometraje registrado: **{vehiculo['kilometraje_actual']} km** · "
        f"Estado operativo: **{vehiculo['estado_operativo']}**"
    )

    st.subheader("Evidencia fotográfica")
    foto_camara = st.camera_input("Tomar fotografía", key="foto_conductor_camara")
    foto_archivo = st.file_uploader(
        "O adjuntar fotografía desde el dispositivo",
        type=["jpg", "jpeg", "png"],
        key="foto_conductor_archivo",
    )
    with st.form("form_reporte_conductor"):
        kilometraje = st.number_input(
            "Kilometraje actual",
            min_value=int(vehiculo["kilometraje_actual"]),
            value=int(vehiculo["kilometraje_actual"]),
            step=1,
        )
        combustible = st.number_input(
            "Nivel de combustible (%)", min_value=0, max_value=100, value=50, step=1
        )
        estado_neumaticos = st.selectbox("Estado de neumáticos", OPCIONES_NEUMATICOS)
        estado_frenos = st.selectbox("Sistema de frenos", OPCIONES_FRENOS)
        luces = st.checkbox("Luces operativas", value=True)
        novedades = st.text_area("Novedades mecánicas u observaciones")
        registrar = st.form_submit_button("Enviar reporte de estado", type="primary")

    if registrar:
        foto = foto_camara if foto_camara is not None else foto_archivo
        guardar_reporte(
            patente, rut, "REPORTE", kilometraje, combustible,
            estado_neumaticos, estado_frenos, luces, novedades, foto,
        )
