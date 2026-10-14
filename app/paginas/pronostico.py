import plotly.graph_objects as go
import streamlit as st

from comun import (AZUL, BANDA, GRIS, NEGRO, ajustar_grafico, cambio_texto, conectar, elegir_zona_y_fecha,
                   encabezado, fecha_larga, fila_de_metricas, nombre_fecha, pedir_pronostico, tabla_horas)

encabezado(
    "Pronóstico por zona",
    "Cuántos viajes se esperan hora por hora en una zona, y entre qué valores es probable que termine cada hora.",
    [
        "Elegí una **zona** y un **día**. El 1 de febrero es *mañana*: todavía no tiene viajes reales.",
        "La **línea negra** es lo esperado: lo más probable (la mitad de las veces la realidad queda arriba y "
        "la mitad abajo).",
        "La **franja amarilla** es el rango probable: en 8 de cada 10 horas la demanda real cae adentro.",
        "Los **puntos azules** son los viajes que de verdad ocurrieron. La línea gris punteada es lo que pasó "
        "el mismo día de la semana anterior.",
        "Una franja ancha no es un error: indica una hora **difícil de predecir**, donde conviene tener margen.",
    ],
)

info = conectar()
zona, fecha = elegir_zona_y_fecha(info)

datos = pedir_pronostico(zona, fecha)
tabla = tabla_horas(datos)
nombre = datos["zona"]["nombre"]
hay_real = tabla["real"].notna().all()

total = tabla["p50"].sum()
semana = tabla["hace_una_semana"].sum()
pico = tabla.loc[tabla["p50"].idxmax()]

# La lectura en una frase, para quien no quiere interpretar gráficos
frase = (f"El {fecha_larga(fecha)} en **{nombre}** se esperan **{total:,.0f} viajes**, "
         f"{cambio_texto(total, semana)} que el mismo día de la semana anterior. "
         f"La hora más fuerte será a las **{int(pico['hora'])}:00**.")
if hay_real:
    error = (tabla["real"] - tabla["p50"]).abs().mean()
    frase += (f" En realidad hubo {tabla['real'].sum():,.0f} viajes: el pronóstico se equivocó en promedio por "
              f"{error:.0f} viajes en cada hora.")
st.info(frase, icon=":material/record_voice_over:")

if hay_real:
    cuarta = dict(label="Error por hora", value=f"{error:.1f} viajes",
                  delta=f"{tabla['real'].sum():,.0f} viajes reales", delta_color="off", delta_arrow="off",
                  help="En promedio, por cuántos viajes se equivocó lo esperado en cada hora (MAE).")
else:
    cuarta = dict(label="Viajes reales", value="Pendiente", delta="es un pronóstico a futuro",
                  delta_color="off", delta_arrow="off")
fila_de_metricas([
    dict(label="Viajes esperados en el día", value=f"{total:,.0f}",
         delta=f"{total / semana - 1:+.0%} vs. hace una semana", chart_data=tabla["p50"].round(1).tolist(),
         chart_type="area", help="Suma de lo esperado (la mediana, p50) en las 24 horas."),
    dict(label="Hora más fuerte", value=f"{int(pico['hora'])}:00", delta=f"{pico['p50']:,.0f} viajes esperados",
         delta_color="off", delta_arrow="off"),
    dict(label="Rango probable del día", value=f"{tabla['p10'].sum():,.0f}", delta=f"a {tabla['p90'].sum():,.0f} viajes",
         delta_color="off", delta_arrow="off",
         help="Suma de los mínimos y máximos probables de cada hora (cuantiles 10% y 90%). Es una aproximación."),
    cuarta,
], alto=180)  # un poco más alta: la primera tarjeta lleva un mini gráfico

# La franja se dibuja con dos líneas invisibles (máximo y mínimo probable) y el relleno entre ellas
fig = go.Figure()
fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["p90"], line=dict(width=0), hoverinfo="skip", showlegend=False))
fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["p10"], fill="tonexty", fillcolor=BANDA, line=dict(width=0),
                         name="Rango probable (8 de cada 10 horas)", hoverinfo="skip"))
fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["hace_una_semana"], name="Hace una semana",
                         line=dict(color=GRIS, dash="dot", width=2)))
fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["p50"], name="Lo esperado", line=dict(color=NEGRO, width=3)))
if hay_real:
    fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["real"], name="Lo que pasó", mode="markers",
                             marker=dict(color=AZUL, size=9, line=dict(color="white", width=1))))
fig.update_layout(title=f"{nombre} · {nombre_fecha(fecha, con_mes=True)}")
fig.update_xaxes(title_text="Hora del día", tickmode="linear", dtick=2)
fig.update_yaxes(title_text="Viajes", rangemode="tozero")
st.plotly_chart(ajustar_grafico(fig, alto=420))

with st.expander("Ver hora por hora", icon=":material/table_rows:"):
    st.dataframe(
        tabla[["hora", "p10", "p50", "p90", "hace_una_semana", "real"]],
        hide_index=True,
        width="stretch",
        column_config={
            "hora": st.column_config.NumberColumn("Hora", format="%d:00"),
            "p10": st.column_config.NumberColumn("Mínimo probable", format="%.0f", help="Cuantil 10% (p10)"),
            "p50": st.column_config.ProgressColumn("Lo esperado", format="%.0f", min_value=0,
                                                   max_value=float(tabla["p90"].max()), help="Mediana (p50)"),
            "p90": st.column_config.NumberColumn("Máximo probable", format="%.0f", help="Cuantil 90% (p90)"),
            "hace_una_semana": st.column_config.NumberColumn("Hace una semana"),
            "real": st.column_config.NumberColumn("Lo que pasó"),
        },
    )
