import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (FECHA_MANANA, GRIS, NEGRO, ROJO, VERDE, ajustar_grafico, cargar_metricas, conectar, elegir_zona,
                   encabezado, fecha_larga, fila_de_metricas, nombre_fecha, pedir_pronostico, tabla_horas)

encabezado(
    "Alertas del modelo",
    "¿El pronóstico sigue funcionando bien? Compara, día por día de la última semana, lo que pronosticó con lo que "
    "de verdad pasó, y avisa cuando el error supera el límite que elijas.",
    [
        "Elegí una **zona** y un **límite de error**. Un día con más error que el límite se marca en **rojo**.",
        "El error del día se mide **en porcentaje de los viajes**: así el mismo límite sirve para zonas grandes y "
        "chicas. Con 25%, si hubo 1,000 viajes, se aceptan hasta 250 de error en total.",
        "La línea gris es el error de **repetir lo de la semana anterior**. Si gana muchos días seguidos, el "
        "modelo necesita volver a entrenarse.",
        "Abajo está el mismo análisis para **todas las zonas juntas**.",
    ],
)

info = conectar()
izquierda, derecha = st.columns(2, vertical_alignment="bottom")
with izquierda:
    zona = elegir_zona(info)
with derecha:
    limite = st.slider("Límite de error aceptable (% de los viajes del día)", 5, 60, 25, step=5, format="%d%%",
                       help="Error del día = suma de los errores de cada hora ÷ viajes reales del día.") / 100

# Pedir a la API cada día de la semana de prueba (el 1 de febrero todavía no tiene viajes reales)
dias = [f for f in info["fechas"] if f != FECHA_MANANA]
filas = []
with st.status(f"Revisando {len(dias)} días...", expanded=False) as estado:
    for fecha in dias:
        datos = pedir_pronostico(zona, fecha)
        horas = tabla_horas(datos)
        reales = horas["real"].sum()
        filas.append({
            "fecha": fecha,
            "dia": nombre_fecha(fecha),
            "viajes_reales": int(reales),
            "error_por_hora": (horas["real"] - horas["p50"]).abs().mean(),
            "error_pct": (horas["real"] - horas["p50"]).abs().sum() / max(reales, 1),
            "error_pct_semana": (horas["real"] - horas["hace_una_semana"]).abs().sum() / max(reales, 1),
            "cobertura": ((horas["real"] >= horas["p10"]) & (horas["real"] <= horas["p90"])).mean(),
        })
        st.markdown(f":material/check: {nombre_fecha(fecha)}: {int(reales):,} viajes reales")  # al desplegar
    estado.update(label="Semana revisada", state="complete")
nombre = datos["zona"]["nombre"]

semana = pd.DataFrame(filas)
semana["alerta"] = semana["error_pct"] > limite
alertas = semana[semana["alerta"]]
gana_regla = semana[semana["error_pct_semana"] < semana["error_pct"]]
peor = semana.loc[semana["error_pct"].idxmax()]

fila_de_metricas([
    dict(label="Días con alerta", value=f"{len(alertas)} de {len(semana)}",
         delta="todo en orden" if alertas.empty else "revisar", delta_color="off", delta_arrow="off"),
    dict(label="Peor día", value=peor["dia"], delta=f"{peor['error_pct']:.0%} de error", delta_color="off",
         delta_arrow="off"),
    dict(label="Ganó la regla simple", value=f"{len(gana_regla)} de {len(semana)}",
         help="Días en que repetir lo de la semana anterior se equivocó menos que el modelo."),
    dict(label="Aciertos del rango", value=f"{semana['cobertura'].mean():.0%}",
         delta="lo prometido: 80%", delta_color="off", delta_arrow="off"),
])

colores = [ROJO if a else VERDE for a in semana["alerta"]]
fig = go.Figure()
fig.add_trace(go.Bar(x=semana["dia"], y=semana["error_pct"], name="Error del modelo", marker_color=colores))
fig.add_trace(go.Scatter(x=semana["dia"], y=semana["error_pct_semana"], name="Error de repetir la semana anterior",
                         mode="lines+markers", line=dict(color=GRIS, dash="dot", width=2)))
fig.add_hline(y=limite, line_dash="dash", line_color=NEGRO, annotation_text=f"Límite {limite:.0%}")
fig.update_layout(title=f"{nombre} · última semana de enero")
fig.update_yaxes(tickformat=".0%", title_text="Error (% de los viajes del día)", rangemode="tozero")
st.plotly_chart(ajustar_grafico(fig))

if alertas.empty:
    st.success(f"Ningún día superó el límite de {limite:.0%} en {nombre}. El pronóstico se comportó como se "
               "esperaba.", icon=":material/check_circle:")
else:
    st.toast(f"{len(alertas)} de {len(semana)} días superaron el límite de error.", icon=":material/warning:")
    for _, dia in alertas.iterrows():
        st.error(f"**{fecha_larga(dia['fecha']).capitalize()}**: error de {dia['error_pct']:.0%} (límite "
                 f"{limite:.0%}), unos {dia['error_por_hora']:.0f} viajes por hora.",
                 icon=":material/notification_important:")

if not gana_regla.empty:
    st.warning("Repetir la semana anterior funcionó mejor el " + ", ".join(gana_regla["dia"]) +
               ". Si pasa muchos días seguidos, conviene volver a entrenar el modelo.", icon=":material/info:")

with st.expander("Ver los 7 días en una tabla", icon=":material/table_rows:"):
    st.dataframe(
        semana[["dia", "viajes_reales", "error_por_hora", "error_pct", "error_pct_semana", "cobertura", "alerta"]],
        hide_index=True,
        width="stretch",
        column_config={
            "dia": "Día",
            "viajes_reales": st.column_config.NumberColumn("Viajes reales", format="%d"),
            "error_por_hora": st.column_config.NumberColumn("Error por hora", format="%.1f"),
            "error_pct": st.column_config.NumberColumn("Error del modelo", format="percent"),
            "error_pct_semana": st.column_config.NumberColumn("Error de la regla simple", format="percent"),
            "cobertura": st.column_config.ProgressColumn("Aciertos del rango", format="percent", min_value=0,
                                                         max_value=1),
            "alerta": st.column_config.CheckboxColumn("¿Alerta?"),
        },
    )

st.subheader("Todas las zonas juntas")
por_dia = pd.DataFrame(cargar_metricas()["por_dia"])
por_dia["dia"] = por_dia["fecha"].map(nombre_fecha)
fig_global = go.Figure()
fig_global.add_trace(go.Scatter(x=por_dia["dia"], y=por_dia["error_modelo"], name="Modelo", mode="lines+markers",
                                line=dict(color=NEGRO, width=3), marker=dict(size=9)))
fig_global.add_trace(go.Scatter(x=por_dia["dia"], y=por_dia["error_semana"], name="Repetir la semana anterior",
                                mode="lines+markers", line=dict(color=GRIS, dash="dot", width=2)))
fig_global.update_yaxes(title_text="Error promedio (viajes por hora)", rangemode="tozero")
st.plotly_chart(ajustar_grafico(fig_global, alto=320))
st.caption("Promedio de las 58 zonas, calculado en el notebook. El fin de semana es más difícil para los dos.")
