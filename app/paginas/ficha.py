import pandas as pd
import plotly.express as px
import streamlit as st

from comun import AMARILLO, GRUPOS, NEGRO, ROJO, bloques_de_texto, cargar_metricas, encabezado, fila_de_metricas

ALTO_GRAFICO = 420  # los dos recuadros de gráficos miden lo mismo

m = cargar_metricas()
errores = m["errores"]
error_modelo = errores["Modelo (mediana)"]
error_semana = errores["Igual que hace una semana"]
lunes = next(d for d in m["por_dia"] if d["fecha"] == "2024-01-29")
peor = max(m["por_grupo"], key=lambda g: g["error_modelo"])  # el tipo de zona con más error

encabezado(
    "¿Cuánto confiar en el pronóstico?",
    "",
    [
        "**En una frase** resume si conviene confiar y dónde tener cuidado.",
        "**Error promedio**: por cuántos viajes se equivoca, en promedio, cada hora. Se compara con lo que "
        "haría alguien sin modelo (repetir lo de la semana anterior).",
        "**Aciertos del rango**: en qué parte de las horas la realidad cayó dentro del rango probable. "
        "Lo prometido es 8 de cada 10 (80%).",
        "Las **limitaciones** dicen qué no sabe el modelo; los **usos no recomendados**, para qué no usarlo.",
    ],
)

st.info(
    f"**En una frase:** el pronóstico sirve para planificar el día siguiente. Se equivoca en promedio por "
    f"{error_modelo:.0f} viajes por hora y su rango probable acierta {m['cobertura']:.0%} de las veces, como "
    f"promete. Hay que revisar a mano **{peor['grupo'].lower()}** y los días especiales.",
    icon=":material/verified:",
)

with st.container(border=True):
    st.markdown("#### :material/target: Para qué sirve")
    st.markdown(
        f"Pronostica cuántos viajes en taxi empezarán **cada hora** en {m['zonas_pronostico']} zonas de "
        "Nueva York, con un rango probable (del cuantil 10% al 90%). Está pensado para **planificar la flota con "
        "un día de anticipación**: mira los viajes de ayer, de anteayer y de hace una semana, la hora, el día de "
        "la semana y si es feriado."
    )
    with st.container(horizontal=True):  # las tres etiquetas en una fila
        st.badge("Modelo: XGBoost con 9 cuantiles", icon=":material/model_training:", color="gray")
        st.badge("Datos: NYC TLC, enero 2024", icon=":material/database:", color="gray")
        st.badge("Anticipación: 24 horas", icon=":material/schedule:", color="gray")

st.subheader("Qué tan bien funciona")
st.caption(f"Aprendió con el 8 al 24 de enero ({m['filas_entrenamiento']:,} horas-zona) y se evaluó con la última "
           f"semana de enero ({m['horas_prueba']:,} horas-zona).")
fila_de_metricas([
    dict(label="Error promedio por hora", value=f"{error_modelo:.1f} viajes",
         delta=f"{error_modelo / error_semana - 1:+.0%} vs. repetir la semana anterior", delta_color="inverse",
         help="Error absoluto medio (MAE) de la mediana en la semana de prueba."),
    dict(label="Aciertos del rango", value=f"{m['cobertura']:.0%}", delta="lo prometido: 80%", delta_color="off",
         delta_arrow="off", help="Cobertura: horas en que la realidad cayó entre el cuantil 10% y el 90%."),
    dict(label="Zonas agrupadas por tipo", value=m["zonas_segmentadas"],
         delta=f"{m['k_elegido']} tipos de zona (K-Means)", delta_color="off", delta_arrow="off"),
])

izquierda, derecha = st.columns(2)
with izquierda, st.container(border=True, height=ALTO_GRAFICO):
    st.markdown("**Frente a no usar modelo**")
    nombres = {"Igual que ayer": "Repetir lo de ayer", "Igual que hace una semana": "Repetir la semana anterior",
               "Modelo (mediana)": "Este modelo"}
    df_reglas = pd.DataFrame({"regla": [nombres[k] for k in errores], "error": list(errores.values())})
    fig = px.bar(df_reglas, x="error", y="regla", orientation="h", text_auto=".1f",
                 color=df_reglas["regla"] == "Este modelo", color_discrete_map={True: AMARILLO, False: "#C9C9C2"},
                 labels={"error": "Error promedio (viajes por hora)", "regla": ""})
    fig.update_traces(marker_line_color=NEGRO, marker_line_width=1)
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig)
    st.caption(f"Le gana por poco a repetir la semana anterior ({error_semana:.1f} → {error_modelo:.1f}). "
               "Su valor principal es el rango probable, que las reglas simples no dan.")
with derecha, st.container(border=True, height=ALTO_GRAFICO):
    st.markdown("**Según el tipo de zona**")
    df_grupo = pd.DataFrame(m["por_grupo"])
    fig = px.bar(df_grupo, x="error_modelo", y="grupo", orientation="h", text_auto=".1f", color="grupo",
                 color_discrete_map={g: d["color"] for g, d in GRUPOS.items()},
                 labels={"error_modelo": "Error promedio (viajes por hora)", "grupo": ""},
                 hover_data={"cobertura": ":.0%", "error_relativo": ":.0%", "zonas": True})
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig)
    st.caption("En los aeropuertos el error es mayor: dependen de vuelos y retrasos que el modelo no ve. En los "
               "barrios el error es chico en viajes, pero grande en proporción.")

with st.expander("¿Qué mira el modelo para decidir? (valores SHAP)", icon=":material/psychology:"):
    traduccion = {"lag_168": "Hace una semana, a la misma hora", "lag_24": "Ayer, a la misma hora",
                  "zona": "La zona", "lag_169": "Hace una semana, una hora después",
                  "lag_167": "Hace una semana, una hora antes", "hora_del_dia": "La hora del día",
                  "dia_semana": "El día de la semana", "media_dia_ant": "El promedio de ayer",
                  "lag_48": "Anteayer, a la misma hora", "feriado": "Si es feriado"}
    importancia = pd.DataFrame({"pista": [traduccion.get(k, k) for k in m["importancia"]],
                                "impacto": list(m["importancia"].values())}).sort_values("impacto")
    fig = px.bar(importancia, x="impacto", y="pista", orientation="h", color_discrete_sequence=[NEGRO],
                 labels={"impacto": "Cuántos viajes mueve el pronóstico, en promedio", "pista": ""})
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig)
    st.caption("Valor SHAP medio, en valor absoluto, para la mediana. Explica cómo decide el modelo, no por qué la "
               "gente toma taxis.")

bloques_de_texto([
    ("Limitaciones", AMARILLO, [
        "Aprendió con <b>un solo mes</b>: Un mes que cae en invierno y no conoce meses de verano, vacaciones ni eventos.",
        "Solo mira la demanda pasada y el calendario: <b>no sabe de clima, conciertos ni cierres de calles</b>.",
        f"Solo {m['zonas_pronostico']} de 263 zonas tienen pronóstico (las de 3,000 viajes al mes o más), casi "
        "todas en Manhattan.",
        f"El rango acierta {m['cobertura']:.0%} en promedio, pero varía por zona: de "
        f"{m['cobertura_zona_min']:.0%} a {m['cobertura_zona_max']:.0%}.",
        f"El lunes 29 se equivocó más que repetir la semana anterior ({lunes['error_modelo']:.1f} contra "
        f"{lunes['error_semana']:.1f}): el domingo anterior se parece poco a un lunes.",
    ]),
    ("Usos no recomendados", ROJO, [
        "Decidir <b>qué conductores trabajan</b> o evaluar su desempeño.",
        "<b>Recortar el servicio en barrios periféricos</b> porque \"el modelo predice poca demanda\": ahí se usan "
        "más los taxis verdes y las apps, que no están en estos datos. Poca demanda de taxi amarillo no "
        "significa poca necesidad de transporte.",
        "Usarlo <b>más de un día hacia adelante</b>: está pensado para el día siguiente.",
        "Usarlo en días especiales (tormentas, feriados distintos al 15 de enero, grandes eventos) sin "
        "revisión humana.",
    ]),
])

st.divider()
st.markdown("**¿Te resultó clara esta ficha?**")


def agradecer():
    estrellas = st.session_state.opinion
    if estrellas is None:  # al tocar otra vez la misma estrella se borra la calificación
        st.toast("Quitaste tu calificación.", icon=":material/undo:")
        return

    # st.feedback devuelve 0 a 4: se suma 1 para mostrar de 1 a 5 estrellas
    st.toast(f"¡Gracias! Calificaste la ficha con {estrellas + 1} de 5 estrellas.",
             icon=":material/favorite:")



st.feedback("stars", key="opinion", on_change=agradecer)
