import streamlit as st

st.set_page_config(page_title="Gestión de flota y acceso", layout="wide")

from conductor import perfil_conductor  # noqa: E402  (st.set_page_config debe ir primero)
from guardia import perfil_guardia  # noqa: E402
from puesto_mando import perfil_puesto_mando  # noqa: E402

# Perfil -> funcion que dibuja su vista.
PERFILES = {
    "Guardia de Garita": perfil_guardia,
    "Conductor Operativo": perfil_conductor,
    "Administrador de Puesto de Mando": perfil_puesto_mando,
}


def elegir_perfil(nombre):
    st.session_state["perfil"] = nombre


def cambiar_perfil():
    st.session_state.clear()


st.title("Gestión de flota y control de acceso")

perfil = st.session_state.get("perfil")
if perfil is None:
    st.subheader("Seleccione su perfil")
    columnas = st.columns(len(PERFILES))
    for columna, nombre in zip(columnas, PERFILES):
        columna.button(
            nombre,
            on_click=elegir_perfil,
            args=(nombre,),
            width="stretch",
        )
    st.stop()

with st.sidebar:
    st.write(f"Perfil activo: **{perfil}**")
    st.button("Cambiar perfil", on_click=cambiar_perfil)

# Navegacion condicional: se dibuja solo la vista del perfil elegido.
PERFILES[perfil]()
