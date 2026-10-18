import pandas as pd
import streamlit as st

from comun import GRUPOS, circulo, encabezado, sin_tildes

ALTO_PASO = 230  # las tres tarjetas de pasos miden lo mismo

GLOSARIO = pd.DataFrame([
    ("Lo esperado", "Mediana · cuantil 50% (p50)",
     "El número más probable. La mitad de las veces la realidad queda arriba y la mitad abajo."),
    ("Rango probable", "Del cuantil 10% al 90% (p10 a p90)",
     "Entre estos dos valores cae la realidad en 8 de cada 10 horas."),
    ("Mínimo probable", "Cuantil 10% (p10)", "Un valor que la realidad supera 9 de cada 10 veces."),
    ("Máximo probable", "Cuantil 90% (p90)", "Un valor que la realidad supera solo 1 de cada 10 veces."),
    ("Nivel de servicio", "Cuantil óptimo",
     "En cuántas horas de cada 10 alcanzan los taxis. Sale de comparar lo que cuesta un taxi vacío con lo que "
     "cuesta un pasajero perdido."),
    ("Taxis-hora", "—", "Un taxi trabajando una hora. Diez taxis durante 3 horas son 30 taxis-hora."),
    ("Error promedio", "Error absoluto medio (MAE)",
     "Por cuántos viajes se equivoca el pronóstico, en promedio, en cada hora."),
    ("Aciertos del rango", "Cobertura",
     "En qué parte de las horas la realidad cayó dentro del rango probable. Lo prometido es 80%."),
    ("Repetir la semana anterior", "Regla simple · baseline (lag 168)",
     "Lo que haría alguien sin modelo: suponer que pasará lo mismo que el mismo día de la semana pasada."),
    ("Tipo de zona", "Grupo de K-Means",
     "Zonas que se usan de forma parecida (horarios, distancias, tarifas), agrupadas automáticamente."),
    ("Mapa de parecidos", "Análisis de componentes principales (PCA)",
     "Un dibujo que resume 8 características de cada zona en 2 ejes: zonas cercanas se parecen."),
    ("Coeficiente de silueta", "Silueta",
     "Una nota de −1 a 1 que dice qué tan bien separados quedaron los grupos. Más es mejor."),
    ("Qué mira el modelo", "Valores SHAP",
     "Cuánto pesa cada pista (ayer, hace una semana, la hora…) en el pronóstico."),
    ("Ficha del modelo", "Model card",
     "Un documento corto que explica para qué sirve un modelo, qué tan bien funciona y cuándo no confiar en él."),
    ("Servicio de pronósticos", "API (FastAPI)",
     "El programa que calcula los pronósticos y se los entrega a esta app."),
    ("Mañana", "1 de febrero de 2024", "El día que se pronostica y que todavía no tiene viajes reales."),
], columns=["Palabra en la app", "Nombre técnico", "Qué significa"])

encabezado(
    "Glosario y ayuda",
    "Cómo usar la app y qué significa cada palabra.",
    [
        "Arriba están los **tres pasos** para usar la app en el día a día.",
        "**Qué significan los colores** explica los círculos de cada tipo de zona y los colores de los gráficos.",
        "En el **glosario** podés buscar cualquier palabra de la app; al lado está su nombre técnico.",
    ],
)

st.subheader("La app en tres pasos")
pasos = [
    ("1", "Mirá el resumen", "Cuántos viajes se esperan mañana en la ciudad, la hora más exigente y las zonas "
     "que más taxis necesitan.", "paginas/inicio.py", "Ir al resumen", ":material/space_dashboard:"),
    ("2", "Elegí los costos", "Cuánto cuesta un taxi vacío y cuánto un pasajero perdido. Con eso, la app "
     "dice cuántos taxis mandar a cada zona.", "paginas/decision.py", "Ir a la decisión", ":material/local_taxi:"),
    ("3", "Descargá el plan", "El plan hora por hora de las 58 zonas, en un archivo para compartir con los "
     "despachadores.", "paginas/plan.py", "Ir al plan de la ciudad", ":material/location_city:"),
]
for columna, (numero, titulo, texto, pagina, enlace, icono) in zip(st.columns(3), pasos):
    with columna.container(border=True, height=ALTO_PASO):
        st.markdown(f"#### {numero} · {titulo}")
        st.markdown(texto)
        st.page_link(pagina, label=enlace, icon=icono)

st.subheader("Qué significan los colores")
izquierda, derecha = st.columns(2)
with izquierda, st.container(border=True, height=260):
    st.markdown("**Tipos de zona**")
    st.html("".join(f'<div style="margin:.45rem 0">{circulo(g)}</div>' for g in GRUPOS))
with derecha, st.container(border=True, height=260):
    st.markdown("**En los gráficos**")
    muestras = [
        ("height:4px;background:#111", "Lo esperado"),
        ("height:14px;background:rgba(252,204,10,.45)", "Rango probable (8 de cada 10 horas)"),
        ("height:12px;width:12px;border-radius:50%;background:#0039A6", "Lo que pasó"),
        ("height:0;border-top:3px dotted #808183", "Hace una semana"),
        ("height:14px;background:#FCCC0A;border:1px solid #111", "Taxis a mandar"),
        ("height:14px;background:#EE352E", "Alerta: el error superó el límite"),
    ]
    st.html("".join(f'<div style="display:flex;align-items:center;gap:12px;margin:.45rem 0">'
                    f'<span style="display:inline-block;width:34px;{estilo}"></span>{texto}</div>'
                    for estilo, texto in muestras))

st.subheader("Glosario")
buscar = st.text_input("Buscar una palabra", placeholder="Por ejemplo: rango, servicio, SHAP…",
                       icon=":material/search:")
glosario = GLOSARIO
if buscar:
    texto = sin_tildes(buscar)
    coincide = glosario.apply(lambda fila: texto in sin_tildes(" ".join(fila)), axis=1)
    glosario = glosario[coincide]
if glosario.empty:
    st.info("No encontramos esa palabra. Probá con otra, o mirá la lista completa borrando la búsqueda.")
else:
    st.table(glosario.set_index("Palabra en la app"))

st.subheader("Preguntas frecuentes")
with st.expander("¿Por qué la app recomienda mandar más taxis que los viajes esperados?"):
    st.markdown("Porque quedarse corto cuesta más que pasarse: un pasajero que no encuentra taxi se pierde y puede "
                "irse a la competencia, mientras que un taxi vacío solo gasta combustible y horas de conductor. "
                "Cuanto más caro es perder un pasajero, más alto conviene el nivel de servicio.")
with st.expander("¿Por qué a veces dice \"Pronósticos sin conexión\"?"):
    st.markdown("El servicio que calcula los pronósticos se apaga solo cuando nadie lo usa durante un rato, para "
                "ahorrar. Tarda cerca de un minuto en despertar: esperá y recargá la página.")
with st.expander("¿De qué época son los datos?"):
    st.markdown("De enero de 2024, publicados por la comisión de taxis de Nueva York (NYC TLC). La app trata el "
                "1 de febrero de 2024 como \"mañana\": se pronostica, pero todavía no tiene viajes reales.")
with st.expander("¿Puedo compartir lo que estoy viendo?"):
    st.markdown("Sí. El link de la barra del navegador guarda la zona y el día elegidos: quien lo abra verá lo mismo.")
with st.expander("¿El pronóstico tiene en cuenta el clima o los eventos?"):
    st.markdown("No. Solo mira la demanda de los días anteriores y el calendario. En días de tormenta, conciertos "
                "o cortes de calles conviene revisar el plan a mano (ver *¿Cuánto confiar?*).")
