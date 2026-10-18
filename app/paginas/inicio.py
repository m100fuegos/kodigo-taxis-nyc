from datetime import date

import plotly.graph_objects as go
import streamlit as st

from comun import (AMARILLO, DIAS_LARGOS, FECHA_MANANA, GRIS, NEGRO, ajustar_grafico, cambio_texto, colorear_grupo,
                   conectar, costos_actuales, encabezado, fecha_larga, fila_de_metricas, nivel_de_servicio,
                   pedir_ciudad, recomendacion, resumen_por_zona, tabla_ciudad)

dia_semana = DIAS_LARGOS[date.fromisoformat(FECHA_MANANA).weekday()]

encabezado(
    f"Resumen de mañana {fecha_larga(FECHA_MANANA)}" ,
    f"Lo que se espera en las 58 zonas con pronóstico, y cuántos taxis preparar.",
    [
        "La tarjeta amarilla dice **qué hacer**: cuántos taxis tener en la calle en la hora más exigente.",
        "**Viajes esperados** es lo más probable que ocurra mañana, sumando todas las zonas.",
        "**Nivel de servicio** es en cuántas horas de cada 10 alcanzarán los taxis. Depende de los costos "
        "que se eligen en la página de *Decisión*",
        "En el gráfico, las barras amarillas son los taxis a preparar y la línea negra los viajes esperados.",
        f"La tabla muestra las 10 zonas que más taxis necesitan y cuánto cambian frente al {dia_semana} pasado.",
    ],
)

conectar()
costo_ocioso, costo_perdido = costos_actuales()
_, usado, columna = nivel_de_servicio(costo_ocioso, costo_perdido)

tabla = tabla_ciudad(pedir_ciudad(FECHA_MANANA))
tabla["taxis"] = tabla[columna].round().astype(int)  # taxis recomendados en cada zona y hora

por_hora = tabla.groupby("hora")[["p50", "hace_una_semana", "taxis"]].sum()  # toda la ciudad, hora por hora
por_zona = resumen_por_zona(tabla)

esperados = por_hora["p50"].sum()
semana = por_hora["hace_una_semana"].sum()
hora_pico = int(por_hora["taxis"].idxmax())
taxis_pico = int(por_hora.loc[hora_pico, "taxis"])
fuertes = por_hora.index[por_hora["taxis"] >= 0.85 * taxis_pico]  # horas cerca del máximo
suben = por_zona[por_zona["cambio"] >= 0.15]
bajan = por_zona[por_zona["cambio"] <= -0.15]

recomendacion(
    "Qué preparar para mañana",
    f"{taxis_pico:,} taxis a las {hora_pico}:00",
    f"Es la hora más exigente del día. Conviene tener la flota completa de {fuertes.min()}:00 a "
    f"{fuertes.max() + 1}:00. Con este plan alcanzan los taxis en {round(usado * 10)} de cada 10 horas.",
)

fila_de_metricas([
    dict(label="Viajes esperados mañana", value=f"{esperados:,.0f}",
         delta=f"{esperados / semana - 1:+.0%} vs. el {dia_semana} pasado",
         help="Lo más probable (la mediana del pronóstico), sumando las 58 zonas y las 24 horas."),
    dict(label="Taxis en la hora pico", value=f"{taxis_pico:,}", delta=f"a las {hora_pico}:00",
         delta_color="off", delta_arrow="off",
         help="Taxis que tienen que estar en la calle al mismo tiempo en la hora más exigente."),
    dict(label="Nivel de servicio", value=f"{usado:.0%}", delta=f"costos USD {costo_ocioso} y USD {costo_perdido}",
         delta_color="off", delta_arrow="off",
         help="En cuántas horas de cada 10 alcanzarán los taxis. Se cambia en la página de Decisión"),
    dict(label="Zonas con cambios fuertes", value=f"{len(suben) + len(bajan)}",
         delta=f"{len(suben)} suben · {len(bajan)} bajan", delta_color="off", delta_arrow="off",
         help=f"Zonas cuya demanda esperada cambia más de 15% frente al {dia_semana} pasado."),
])

with st.container(border=True):
    st.markdown("#### :material/checklist: Para tener en cuenta")
    top = por_zona.head(3)
    puntos = [
        "Las zonas que más taxis necesitan son " +
        ", ".join(f"**{fila.zona}** ({fila.taxis:,})" for fila in top.itertuples()) + ".",
        f"En toda la ciudad se esperan **{cambio_texto(esperados, semana)}** viajes que el {dia_semana} pasado.",
    ]
    if len(suben):
        puntos.append(f"Suben más de 15%: {', '.join(suben['zona'].head(4))}.")
    if len(bajan):
        puntos.append(f"Bajan más de 15%: {', '.join(bajan['zona'].head(4))}.")
    if not len(suben) and not len(bajan):
        puntos.append(f"Ninguna zona cambia más de 15% frente al {dia_semana} pasado: un día parecido.")
    st.markdown("\n".join(f"- {punto}" for punto in puntos))

st.subheader("Toda la ciudad, hora por hora")
fig = go.Figure()
fig.add_trace(go.Bar(x=por_hora.index, y=por_hora["taxis"], name="Taxis a preparar", marker_color=AMARILLO,
                     marker_line_color=NEGRO, marker_line_width=1))
fig.add_trace(go.Scatter(x=por_hora.index, y=por_hora["p50"], name="Viajes esperados",
                         line=dict(color=NEGRO, width=3)))
fig.add_trace(go.Scatter(x=por_hora.index, y=por_hora["hace_una_semana"], name=f"El {dia_semana} pasado",
                         line=dict(color=GRIS, dash="dot", width=2)))
fig.update_xaxes(title_text="Hora del día", tickmode="linear", dtick=2)
fig.update_yaxes(title_text="Taxis / viajes")
st.plotly_chart(ajustar_grafico(fig))

st.subheader("Las 10 zonas que más taxis necesitan")
top10 = por_zona.head(10)[["zona", "tipo", "taxis", "taxis_pico", "hora_pico", "esperados", "cambio"]].copy()
top10["cambio"] = (top10["cambio"] * 100).round() + 0.0  # en %, sin decimales (el + 0.0 evita un "-0%")
st.dataframe(
    top10.style.map(colorear_grupo, subset=["tipo"]),
    hide_index=True,
    width="stretch",
    column_config={
        "zona": st.column_config.TextColumn("Zona", width="medium"),
        "tipo": st.column_config.TextColumn("Tipo de zona", width="medium"),
        "taxis": st.column_config.ProgressColumn("Taxis en el día", format="%d", min_value=0,
                                                 max_value=int(por_zona["taxis"].max()), width="medium"),
        "taxis_pico": st.column_config.NumberColumn("En el pico", format="%d", width="small",
                                                    help="Taxis a la vez en la hora pico de la zona."),
        "hora_pico": st.column_config.NumberColumn("Hora pico", format="%d:00", width="small"),
        "esperados": st.column_config.NumberColumn("Viajes", format="%.0f", width="small"),
        "cambio": st.column_config.NumberColumn(f"vs. {dia_semana} pasado", format="%+.0f%%", width="small"),
    },
)

c1, c2, c3 = st.columns(3)
c1.page_link("paginas/pronostico.py", label="Ver una zona en detalle", icon=":material/query_stats:")
c2.page_link("paginas/plan.py", label="Plan completo y descarga", icon=":material/location_city:")
c3.page_link("paginas/decision.py", label="Cambiar los costos", icon=":material/tune:")
