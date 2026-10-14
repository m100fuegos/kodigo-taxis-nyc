import streamlit as st

from comun import barra_lateral, estilos

st.set_page_config(page_title="Taxis NYC · Operaciones", page_icon=":material/local_taxi:", layout="wide")
estilos()

paginas = {
    "": [
        st.Page("paginas/inicio.py", title="Resumen de mañana", icon=":material/space_dashboard:", default=True),
    ],
    "Planificar": [
        st.Page("paginas/pronostico.py", title="Pronóstico por zona", icon=":material/query_stats:"),
        st.Page("paginas/decision.py", title="¿Cuántos taxis enviar?", icon=":material/local_taxi:"),
        st.Page("paginas/plan.py", title="Plan de la ciudad", icon=":material/location_city:"),
    ],
    "Entender": [
        st.Page("paginas/segmentacion.py", title="Tipos de zona", icon=":material/hub:"),
        st.Page("paginas/ficha.py", title="¿Cuánto confiar? (ficha)", icon=":material/verified:"),
    ],
    "Vigilar": [
        st.Page("paginas/monitoreo.py", title="Alertas del modelo", icon=":material/notifications_active:"),
    ],
    "Ayuda": [
        st.Page("paginas/ayuda.py", title="Glosario y ayuda", icon=":material/menu_book:"),
    ],
}

pagina = st.navigation(paginas)
barra_lateral()
pagina.run()
