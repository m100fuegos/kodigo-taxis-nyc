import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (AMARILLO, AZUL, FECHA_MANANA, NEGRO, ajustar_grafico, conectar, controles_de_costo, costo,
                   elegir_zona_y_fecha, encabezado, fila_de_metricas, nivel_de_servicio, nombre_fecha,
                   pedir_pronostico, recomendacion, tabla_horas)

encabezado(
    "¿Cuántos taxis enviar?",
    "El pronóstico dice cuántos viajes se esperan. Esta página decide cuántos taxis mandar, según lo que cuesta "
    "equivocarse para cada lado.",
    [
        "**Paso 1.** Mové los dos controles: cuánto cuesta un taxi dando vueltas vacío y cuánto cuesta un "
        "pasajero que no encuentra taxi.",
        "**Paso 2.** La tarjeta amarilla dice cuántos taxis mandar. Si perder un pasajero cuesta más, conviene "
        "mandar más taxis que los viajes esperados.",
        "El **nivel de servicio** es en cuántas horas de cada 10 alcanzarán los taxis.",
        "**Paso 3.** Para los días que ya pasaron, la página calcula cuánto habría costado decidir así, frente a "
        "mandar lo esperado o lo de la semana anterior.",
        "El botón de abajo descarga el plan hora por hora para compartirlo.",
    ],
)

info = conectar()
zona, fecha = elegir_zona_y_fecha(info)

datos = pedir_pronostico(zona, fecha)
tabla = tabla_horas(datos)
nombre = datos["zona"]["nombre"]
hay_real = tabla["real"].notna().all()


def tres_costos(t, columna, costo_ocioso, costo_perdido):
    """Costo de la recomendación, de mandar lo esperado (p50) y de mandar lo de hace una semana."""
    real = t["real"].to_numpy()
    return (costo(np.round(t[columna]), real, costo_ocioso, costo_perdido),
            costo(np.round(t["p50"]), real, costo_ocioso, costo_perdido),
            costo(t["hace_una_semana"], real, costo_ocioso, costo_perdido))


def mostrar_costos(c_rec, c_p50, c_sem):
    fila_de_metricas([
        dict(label="Con la recomendación", value=f"${c_rec:,.0f}"),
        dict(label="Mandando lo esperado", value=f"${c_p50:,.0f}", delta=f"{c_p50 / c_rec - 1:+.0%} vs. la recomendación",
             delta_color="inverse", help="Mandar la mediana del pronóstico (p50)."),
        dict(label="Mandando lo de hace una semana", value=f"${c_sem:,.0f}",
             delta=f"{c_sem / c_rec - 1:+.0%} vs. la recomendación", delta_color="inverse"),
    ])


@st.fragment
def decision():
    st.subheader("1 · ¿Cuánto cuesta equivocarse?")
    with st.container(border=True):
        costo_ocioso, costo_perdido = controles_de_costo()

    # El problema del vendedor de periódicos: cubrir la demanda hasta este cuantil
    optimo, usado, columna = nivel_de_servicio(costo_ocioso, costo_perdido)
    recomendados = np.round(tabla[columna]).astype(int)
    hora_max = int(tabla["hora"][recomendados.idxmax()])

    st.subheader("2 · La recomendación")
    recomendacion(
        f"{nombre} · {nombre_fecha(fecha, con_mes=True)}",
        f"{recomendados.sum():,} taxis en el día",
        f"Hasta {recomendados.max():,} al mismo tiempo, a las {hora_max}:00. Con este plan alcanzan los taxis en "
        f"{round(usado * 10)} de cada 10 horas (nivel de servicio {usado:.0%}).",
    )

    veces = costo_perdido / costo_ocioso
    if veces >= 1:
        frase = f"Perder un pasajero cuesta **{veces:.1f} veces** lo que cuesta un taxi vacío"
    else:
        frase = f"Un taxi vacío cuesta **{1 / veces:.1f} veces** lo que cuesta perder un pasajero"
    with st.container(border=True):
        st.markdown(f"{frase}. Por eso conviene cubrir la demanda hasta el **{usado:.0%}**: mandar tantos taxis "
                    f"como los viajes que no se superan en {round(usado * 10)} de cada 10 horas:")
        st.latex(rf"\text{{cuantil óptimo}} = \frac{{C_{{perdido}}}}{{C_{{perdido}} + C_{{ocioso}}}} = "
                 rf"\frac{{{costo_perdido}}}{{{costo_perdido} + {costo_ocioso}}} = {optimo:.2f}")
        if abs(optimo - usado) > 0.05:
            st.caption(f"El cuantil exacto sería {optimo:.0%}, pero el pronóstico llega del 10% al 90%: "
                       f"se usa el {usado:.0%}.")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=tabla["hora"], y=recomendados, name=f"Taxis a mandar (nivel {usado:.0%})",
                         marker_color=AMARILLO, marker_line_color=NEGRO, marker_line_width=1))
    fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["p50"], name="Viajes esperados",
                             line=dict(color=NEGRO, width=3)))
    if hay_real:
        fig.add_trace(go.Scatter(x=tabla["hora"], y=tabla["real"], name="Lo que pasó", mode="markers",
                                 marker=dict(color=AZUL, size=9, line=dict(color="white", width=1))))
    fig.update_xaxes(title_text="Hora del día", tickmode="linear", dtick=2)
    fig.update_yaxes(title_text="Taxis / viajes")
    st.plotly_chart(ajustar_grafico(fig))

    st.subheader("3 · ¿Cuánto habría costado?")
    if hay_real:
        st.markdown(f"**Ese día ({nombre_fecha(fecha, con_mes=True)})**")
        mostrar_costos(*tres_costos(tabla, columna, costo_ocioso, costo_perdido))
    else:
        st.info("El 1 de febrero todavía no tiene viajes reales: el costo de ese día se podrá calcular cuando pase. "
                "Abajo está el de la semana anterior.", icon=":material/schedule:")

    # Una regla de decisión se juzga en muchos días, no en uno: la semana de prueba completa
    dias = [f for f in info["fechas"] if f != FECHA_MANANA]
    semana = [tres_costos(tabla_horas(pedir_pronostico(zona, f)), columna, costo_ocioso, costo_perdido)
              for f in dias]
    st.markdown(f"**Sumando los {len(dias)} días de la semana de prueba**")
    mostrar_costos(*np.sum(semana, axis=0))
    st.caption("Un día suelto puede salir más barato mandando lo esperado, por suerte. Lo que importa es el costo "
               "de usar la regla todos los días.")

    plan = pd.DataFrame({"hora": tabla["hora"], "taxis_a_mandar": recomendados,
                         "viajes_esperados": tabla["p50"].round(1), "nivel_de_servicio": f"{usado:.0%}"})
    with st.expander("Ver el plan hora por hora", icon=":material/table_rows:"):
        st.dataframe(plan, hide_index=True, width="stretch",
                     column_config={"hora": st.column_config.NumberColumn("Hora", format="%d:00"),
                                    "taxis_a_mandar": st.column_config.ProgressColumn(
                                        "Taxis a mandar", format="%d", min_value=0,
                                        max_value=int(recomendados.max())),
                                    "viajes_esperados": "Viajes esperados", "nivel_de_servicio": "Nivel de servicio"})
    st.download_button("Descargar el plan (CSV)", plan.to_csv(index=False).encode("utf-8"),
                       file_name=f"plan_taxis_{zona}_{fecha}.csv", mime="text/csv", icon=":material/download:",
                       type="primary")


decision()

with st.expander("¿Por qué no mandar simplemente los viajes esperados?", icon=":material/lightbulb:"):
    st.markdown(
        "Lo esperado (la mediana) se equivoca hacia arriba y hacia abajo con la misma frecuencia. Eso solo "
        "conviene si los dos errores cuestan lo mismo. Si un pasajero perdido cuesta 4 veces más que un taxi "
        "vacío, quedarse corto duele más, y conviene mandar de más: por eso se usa un nivel de servicio alto. "
        "Es la misma idea del umbral por costo que se usa en clasificación."
    )
