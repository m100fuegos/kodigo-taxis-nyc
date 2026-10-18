import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from comun import (AMARILLO, NEGRO, ajustar_grafico, colorear_grupo, conectar, controles_de_costo, costo,
                   elegir_fecha, encabezado, fila_de_metricas, nivel_de_servicio, nombre_fecha, pedir_ciudad,
                   resumen_por_zona, tabla_ciudad)

encabezado(
    "Plan de la ciudad",
    "El plan de taxis hora por hora para las 58 zonas a la vez, con los mismos costos de la página anterior. "
    "Se descarga en un solo archivo.",
    [
        "Elegí el **día**. Los costos son los mismos de la página *Decisión*: si los cambiás acá, cambian allá.",
        "Las **tarjetas** resumen el día: cuántos taxis hacen falta, cuándo y dónde.",
        "En el **mapa de calor**, cada fila es una zona y cada columna una hora: cuanto más oscuro, más taxis "
        "hacen falta.",
        "La **tabla** tiene las 58 zonas. Se puede ordenar haciendo clic en el título de cada columna, y buscar "
        "con la lupa que aparece arriba a la derecha.",
        "El botón **Descargar** baja el plan completo (zona por zona y hora por hora) para compartirlo.",
    ],
)

info = conectar()
fecha = elegir_fecha(info)
with st.container(border=True):
    costo_ocioso, costo_perdido = controles_de_costo()
_, usado, columna = nivel_de_servicio(costo_ocioso, costo_perdido)

tabla = tabla_ciudad(pedir_ciudad(fecha))
tabla["taxis"] = tabla[columna].round().astype(int)
por_hora = tabla.groupby("hora")[["p50", "taxis"]].sum()
por_zona = resumen_por_zona(tabla)
hay_real = tabla["real"].notna().all()

hora_pico = int(por_hora["taxis"].idxmax())
mayor = por_zona.iloc[0]
metricas = [
    dict(label="Taxis-hora en el día", value=f"{por_hora['taxis'].sum():,}",
         help="La suma de los taxis de todas las zonas y horas. Un taxi que trabaja 8 horas cuenta 8."),
    dict(label="Hora más exigente", value=f"{hora_pico}:00", delta=f"{por_hora['taxis'].max():,} taxis a la vez",
         delta_color="off", delta_arrow="off"),
    dict(label="La zona que más necesita", value=f"{mayor['taxis']:,}", delta=mayor["zona"],
         delta_color="off", delta_arrow="off", help="Taxis-hora en el día de la zona que más taxis necesita."),
]
if hay_real:
    real = tabla["real"].to_numpy()
    c_plan = costo(tabla["taxis"].to_numpy(), real, costo_ocioso, costo_perdido)
    c_p50 = costo(np.round(tabla["p50"]).to_numpy(), real, costo_ocioso, costo_perdido)
    metricas.append(dict(label="Ahorro del plan ese día", value=f"${c_p50 - c_plan:,.0f}",
                         delta=f"{1 - c_plan / c_p50:.0%} más barato", delta_color="off",
                         help="Costo de mandar la mediana (p50) en cada zona menos el costo de este plan, ese día."))
else:
    metricas.append(dict(label="Nivel de servicio", value=f"{usado:.0%}",
                         delta=f"alcanzan en {round(usado * 10)} de cada 10 horas", delta_color="off",
                         delta_arrow="off"))
fila_de_metricas(metricas)

st.subheader(f"Toda la ciudad · {nombre_fecha(fecha, con_mes=True)}")
fig = go.Figure()
fig.add_trace(go.Bar(x=por_hora.index, y=por_hora["taxis"], name=f"Taxis a mandar (nivel {usado:.0%})",
                     marker_color=AMARILLO, marker_line_color=NEGRO, marker_line_width=1))
fig.add_trace(go.Scatter(x=por_hora.index, y=por_hora["p50"], name="Viajes esperados",
                         line=dict(color=NEGRO, width=3)))
fig.update_xaxes(title_text="Hora del día", tickmode="linear", dtick=2)
fig.update_yaxes(title_text="Taxis / viajes")
st.plotly_chart(ajustar_grafico(fig, alto=340))

st.subheader("¿Dónde y cuándo? Las 15 zonas que más taxis necesitan")
top = por_zona.head(15)["zona"].tolist()
calor = tabla[tabla["zona"].isin(top)].pivot_table(index="zona", columns="hora", values="taxis").loc[top]
fig_calor = px.imshow(calor, aspect="auto", color_continuous_scale=[[0, "#F5F5F2"], [0.45, AMARILLO], [1, NEGRO]],
                      labels={"x": "Hora del día", "y": "", "color": "Taxis"})
fig_calor.update_xaxes(tickmode="linear", dtick=2, side="top")
fig_calor.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig_calor)

st.subheader("Las 58 zonas")
tabla_zonas = por_zona[["zona", "tipo", "taxis", "hora_pico", "taxis_pico", "esperados", "cambio"]].copy()
tabla_zonas["cambio"] = (tabla_zonas["cambio"] * 100).round() + 0.0  # en %, sin decimales (evita un "-0%")
st.dataframe(
    tabla_zonas.style.map(colorear_grupo, subset=["tipo"]),
    hide_index=True,
    width="stretch",
    height=420,
    column_config={
        "zona": st.column_config.TextColumn("Zona", width="medium"),
        "tipo": st.column_config.TextColumn("Tipo de zona", width="medium"),
        "taxis": st.column_config.ProgressColumn("Taxis-hora", format="%d", min_value=0,
                                                 max_value=int(por_zona["taxis"].max()), width="medium"),
        "hora_pico": st.column_config.NumberColumn("Hora pico", format="%d:00", width="small"),
        "taxis_pico": st.column_config.NumberColumn("En la hora pico", format="%d", width="small"),
        "esperados": st.column_config.NumberColumn("Viajes", format="%.0f", width="small"),
        "cambio": st.column_config.NumberColumn("vs. semana anterior", format="%+.0f%%", width="small"),
    },
)

plan = tabla[["zona_id", "zona", "distrito", "tipo", "hora", "taxis", "p50"]].rename(
    columns={"taxis": "taxis_a_mandar", "p50": "viajes_esperados"})
plan["viajes_esperados"] = plan["viajes_esperados"].round(1)
plan["nivel_de_servicio"] = f"{usado:.0%}"
st.download_button("Descargar el plan de toda la ciudad (CSV)", plan.to_csv(index=False).encode("utf-8"),
                   file_name=f"plan_ciudad_{fecha}.csv", mime="text/csv", icon=":material/download:", type="primary")
st.caption(f"{len(plan):,} filas: las {tabla['zona_id'].nunique()} zonas por 24 horas.")
