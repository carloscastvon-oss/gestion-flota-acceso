import altair as alt
import pandas as pd
import streamlit as st

from config import consultar
from utilidades import url_foto

COLORES = {
    "Operativo": "#2e9e4f",
    "Requiere Mantención": "#e3b505",
    "Crítico": "#d1352b",
}


def cargar_datos():
    vehiculos = consultar("vehiculos", orden=("patente", False))
    conductores = consultar("conductores")
    reportes = consultar("reportes_estado", orden=("fecha_reporte", True), limite=5000)
    if vehiculos is None or conductores is None or reportes is None:
        return None
    datos_reportes = pd.DataFrame(reportes)
    if not datos_reportes.empty:
        datos_reportes["fecha_reporte"] = pd.to_datetime(
            datos_reportes["fecha_reporte"], errors="coerce", utc=True
        )
        datos_reportes = datos_reportes.merge(
            pd.DataFrame(conductores)[["rut", "nombre_completo", "unidad_destino"]],
            left_on="rut_conductor",
            right_on="rut",
            how="left",
        )
    return pd.DataFrame(vehiculos), datos_reportes


def construir_flota(vehiculos, reportes):
    """Une cada vehiculo con su ultimo reporte y calcula si tiene alerta."""
    flota = vehiculos.copy()
    columnas_reporte = [
        "fecha_reporte", "kilometraje_salida", "nivel_combustible",
        "luces_operativas", "estado_frenos", "estado_neumaticos", "critico",
    ]
    if reportes.empty:
        for columna in columnas_reporte:
            flota[columna] = None
    else:
        ultimos = reportes.sort_values("fecha_reporte").drop_duplicates("patente", keep="last")
        flota = flota.merge(ultimos[["patente"] + columnas_reporte], on="patente", how="left")

    sin_luces = flota["luces_operativas"].eq(False)
    mal_neumaticos = flota["estado_neumaticos"].fillna("Óptimo").ne("Óptimo")
    mal_frenos = flota["estado_frenos"].fillna("Operativo").ne("Operativo")
    flota["alerta"] = (
        flota["estado_operativo"].ne("Operativo") | sin_luces | mal_neumaticos | mal_frenos
    )
    return flota


def mostrar_indicadores(flota, reportes):
    total = len(flota)
    operativos = int(flota["estado_operativo"].eq("Operativo").sum())
    inmovilizadas = int(flota["estado_operativo"].isin(["Crítico", "Requiere Mantención"]).sum())
    criticos = int(flota["estado_operativo"].eq("Crítico").sum())
    accesos = 0 if reportes.empty else int(reportes["tipo_registro"].isin(["ENTRADA", "SALIDA"]).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vehículos en flota", total)
    c2.metric(
        "Disponibilidad de flota",
        f"{operativos / total:.1%}",
        help=f"{operativos} de {total} vehículos están operativos.",
    )
    c3.metric(
        "Inmovilizadas o en mantención",
        inmovilizadas,
        help=f"{criticos} en estado Crítico y {inmovilizadas - criticos} que requieren mantención.",
    )
    c4.metric("Accesos registrados", accesos)


def mostrar_matriz(flota):
    st.subheader("Matriz de estado por vehículo")
    st.caption("Verde: operativo. Amarillo: requiere mantención. Rojo: crítico.")
    tarjetas = []
    for _, fila in flota.sort_values("patente").iterrows():
        color = COLORES.get(fila["estado_operativo"], COLORES["Crítico"])
        marca_alerta = " (alerta en último reporte)" if fila["alerta"] and fila["estado_operativo"] == "Operativo" else ""
        tarjetas.append(
            f"<div style='background:{color};color:#fff;padding:10px 14px;border-radius:6px;"
            f"min-width:170px;flex:1 1 170px'>"
            f"<b>{fila['patente']}</b><br>{fila['tipo_vehiculo']}<br>"
            f"{fila['estado_operativo']}{marca_alerta}</div>"
        )
    st.markdown(
        "<div style='display:flex;flex-wrap:wrap;gap:8px'>" + "".join(tarjetas) + "</div>",
        unsafe_allow_html=True,
    )

    con_alerta = flota[flota["alerta"]]
    st.write("")
    if con_alerta.empty:
        st.success("No se detectan alertas en la flota.")
    else:
        st.warning("Requieren atención: " + ", ".join(con_alerta["patente"].tolist()))
        detalle = con_alerta[
            ["patente", "estado_operativo", "estado_frenos", "estado_neumaticos",
             "luces_operativas", "fecha_reporte"]
        ]
        st.dataframe(detalle, width="stretch", hide_index=True)


def mostrar_analitica(flota, reportes):
    st.subheader("Kilometraje acumulado por vehículo")
    grafico_km = (
        alt.Chart(flota)
        .mark_bar()
        .encode(
            x=alt.X("patente:N", sort="-y", title="Patente"),
            y=alt.Y("kilometraje_actual:Q", title="Kilometraje (km)"),
            color=alt.Color(
                "estado_operativo:N",
                scale=alt.Scale(domain=list(COLORES), range=list(COLORES.values())),
                title="Estado",
            ),
            tooltip=["patente", "tipo_vehiculo", "marca_modelo", "kilometraje_actual", "estado_operativo"],
        )
    )
    st.altair_chart(grafico_km, width="stretch")

    st.subheader("Frecuencia de accesos")
    accesos = reportes[reportes["tipo_registro"].isin(["ENTRADA", "SALIDA"])] if not reportes.empty else reportes
    if accesos.empty:
        st.info("Todavía no hay accesos registrados.")
        return

    agrupar = st.radio("Agrupar por", ["Unidad táctica", "Vehículo"], horizontal=True)
    movimiento = st.radio("Movimiento", ["Todos", "ENTRADA", "SALIDA"], horizontal=True)
    if movimiento != "Todos":
        accesos = accesos[accesos["tipo_registro"] == movimiento]
    columna = "unidad_destino" if agrupar == "Unidad táctica" else "patente"
    frecuencia = (
        accesos.assign(**{columna: accesos[columna].fillna("Sin unidad")})
        .groupby(columna)
        .size()
        .reset_index(name="accesos")
    )
    grafico_accesos = (
        alt.Chart(frecuencia)
        .mark_bar()
        .encode(
            x=alt.X("accesos:Q", title="Accesos", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y(f"{columna}:N", sort="-x", title=agrupar),
            tooltip=[columna, "accesos"],
        )
    )
    st.altair_chart(grafico_accesos, width="stretch")

    st.subheader("Combustible promedio reportado por vehículo")
    consumo = (
        reportes.dropna(subset=["nivel_combustible"])
        .groupby("patente")["nivel_combustible"]
        .mean()
        .round(1)
        .reset_index(name="combustible_promedio")
    )
    grafico_consumo = (
        alt.Chart(consumo)
        .mark_bar()
        .encode(
            x=alt.X("patente:N", title="Patente"),
            y=alt.Y("combustible_promedio:Q", title="Combustible promedio (%)", scale=alt.Scale(domain=[0, 100])),
            tooltip=["patente", "combustible_promedio"],
        )
    )
    st.altair_chart(grafico_consumo, width="stretch")


def mostrar_foto(ruta):
    if pd.isna(ruta) or not ruta:
        st.caption("Sin evidencia fotográfica.")
        return
    url = url_foto(ruta)
    if url:
        st.image(url, width="stretch")
    else:
        st.caption("No se pudo cargar la fotografía.")


def mostrar_feed(reportes):
    st.subheader("Feed cronológico de accesos")
    accesos = reportes[reportes["tipo_registro"].isin(["ENTRADA", "SALIDA"])] if not reportes.empty else reportes
    if accesos.empty:
        st.info("Todavía no hay movimientos de entrada o salida registrados.")
        return
    cantidad = st.slider("Cantidad de accesos a mostrar", 5, 50, 10)
    for _, acceso in accesos.sort_values("fecha_reporte", ascending=False).head(cantidad).iterrows():
        columna_foto, columna_texto = st.columns([1, 3])
        with columna_foto:
            mostrar_foto(acceso.get("foto_evidencia_url"))
        with columna_texto:
            st.markdown(
                f"**{acceso['tipo_registro']}** · {acceso['patente']} · "
                f"{acceso['fecha_reporte']:%d-%m-%Y %H:%M} UTC"
            )
            st.write(
                f"Conductor: {acceso['nombre_completo']} ({acceso['rut_conductor']}) · "
                f"{acceso['unidad_destino']}"
            )
            st.write(
                f"Kilometraje: {acceso['kilometraje_salida']} km · "
                f"Combustible: {acceso['nivel_combustible']}%"
            )
            if acceso["critico"]:
                st.error("Parámetro crítico reportado.")
            if pd.notna(acceso["observaciones"]):
                st.caption(acceso["observaciones"])
        st.divider()


def mostrar_auditoria(flota, reportes):
    st.subheader("Auditoría de incidencias por vehículo")
    patente = st.selectbox("Patente", flota["patente"].sort_values().tolist())
    vehiculo = flota[flota["patente"] == patente].iloc[0]

    st.markdown("**Ficha del vehículo**")
    kilometraje = f"{int(vehiculo['kilometraje_actual']):,} km".replace(",", ".")
    st.write(
        f"Tipo: **{vehiculo['tipo_vehiculo']}** · "
        f"Marca y modelo: **{vehiculo['marca_modelo']}** · "
        f"Año: **{int(vehiculo['anio'])}** · "
        f"Kilometraje: **{kilometraje}** · "
        f"Estado operativo: **{vehiculo['estado_operativo']}**"
    )

    historial = reportes[reportes["patente"] == patente] if not reportes.empty else reportes
    if historial.empty:
        st.info("Este vehículo no tiene reportes registrados.")
        return
    solo_criticos = st.checkbox("Mostrar solo reportes críticos o con novedades")
    if solo_criticos:
        historial = historial[
            historial["critico"]
            | historial["estado_neumaticos"].ne("Óptimo")
            | historial["luces_operativas"].eq(False)
        ]
    for _, reporte in historial.sort_values("fecha_reporte", ascending=False).iterrows():
        columna_foto, columna_texto = st.columns([1, 3])
        with columna_foto:
            mostrar_foto(reporte.get("foto_evidencia_url"))
        with columna_texto:
            st.markdown(
                f"**{reporte['tipo_registro']}** · {reporte['fecha_reporte']:%d-%m-%Y %H:%M} UTC"
            )
            st.write(
                f"Conductor: {reporte['nombre_completo']} ({reporte['rut_conductor']})"
            )
            st.write(
                f"Km: {reporte['kilometraje_salida']} · Combustible: {reporte['nivel_combustible']}% · "
                f"Neumáticos: {reporte['estado_neumaticos']} · Frenos: {reporte['estado_frenos']} · "
                f"Luces: {'operativas' if reporte['luces_operativas'] else 'con falla'}"
            )
            if reporte["critico"]:
                st.error("Parámetro crítico reportado.")
            if pd.notna(reporte["observaciones"]):
                st.caption(reporte["observaciones"])
        st.divider()


@st.fragment(run_every=30)
def panel():
    """Se vuelve a ejecutar cada 30 segundos para reflejar datos nuevos."""
    cargados = cargar_datos()
    if cargados is None:
        return
    vehiculos, reportes = cargados
    if vehiculos.empty:
        st.info("No hay vehículos registrados para mostrar.")
        return

    flota = construir_flota(vehiculos, reportes)
    mostrar_indicadores(flota, reportes)
    st.caption("Los datos se actualizan automáticamente cada 30 segundos.")

    pestana_estado, pestana_analitica, pestana_feed, pestana_auditoria = st.tabs(
        ["Estado de la flota", "Uso y consumo", "Feed de accesos", "Auditoría"]
    )
    with pestana_estado:
        mostrar_matriz(flota)
    with pestana_analitica:
        mostrar_analitica(flota, reportes)
    with pestana_feed:
        mostrar_feed(reportes)
    with pestana_auditoria:
        mostrar_auditoria(flota, reportes)


def perfil_puesto_mando():
    st.header("Panel de inteligencia de negocios")
    st.caption("Perfil Administrador de Puesto de Mando. Apresto, alertas y trazabilidad.")
    panel()
