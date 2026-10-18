import plotly.express as px
import streamlit as st

from comun import (GRUPOS, HORAS, cargar_metricas, cargar_siluetas, cargar_zonas, circulo, colorear_grupo,
                   encabezado)

DESCRIPCION = {
    "Manhattan central": "Muchísimos viajes cortos y baratos, de día y entre semana. El pico es de 16 a 20 h.",
    "Vida nocturna": "Casi la mitad de los viajes son de 22 a 5 h, y muchos en fin de semana.",
    "Aeropuertos": "Viajes largos (más de 10 millas), con tarifas y propinas altas. Demanda todo el día.",
    "Barrios periféricos": "Pocos viajes, más largos que en Manhattan, casi sin propina y más de mañana.",
}
zonas = cargar_zonas()
siluetas = cargar_siluetas()
metricas = cargar_metricas()

encabezado(
    "Tipos de zona",
    "La app agrupó automáticamente las 90 zonas con más viajes según cómo se usan los taxis: a qué hora, qué "
    "tan lejos se viaja y cuánto se paga.",
    [
        "Cada **tipo de zona** tiene un color y una letra, como las líneas del metro.",
        "En el **mapa de puntos**, cada punto es una zona y su tamaño indica cuántos viajes tiene. Las zonas "
        "cercanas se usan de forma parecida.",
        "Podés **seleccionar zonas** en el mapa (clic, o arrastrando una caja o un lazo) y la tabla de abajo "
        "muestra solo esas.",
        "Las **curvas** muestran a qué hora se concentran los viajes de cada zona.",
        "Los botones de arriba sirven para mostrar u ocultar tipos de zona.",
    ],
)

elegidos = st.pills("Mostrar", list(GRUPOS), selection_mode="multi", default=list(GRUPOS))
filtradas = zonas[zonas["grupo"].isin(elegidos)]

# Las cuatro tarjetas en una cuadrícula: así miden siempre lo mismo, aunque una descripción sea más larga
tarjetas = []
for grupo, datos in GRUPOS.items():
    del_grupo = zonas[zonas["grupo"] == grupo]
    tarjetas.append(
        f'<div class="tarjeta-grupo" style="border-top-color:{datos["color"]}">{circulo(grupo)}'
        f'<div class="cifra">{len(del_grupo)}<span>zonas</span></div><ul>'
        f'<li><b>{del_grupo["viajes_por_dia"].sum():,.0f}</b> viajes al día</li>'
        f'<li><b>{del_grupo["distancia_mediana"].median():.1f}</b> millas por viaje</li>'
        f'<li><b>{del_grupo["pct_noche"].mean():.0%}</b> de noche</li></ul>'
        f'<p>{DESCRIPCION[grupo]}</p></div>')
st.html('<div class="grupos">' + "".join(tarjetas) + "</div>")

# Hacia dónde apunta cada eje, calculado con los datos (PCA puede dar los ejes "al revés")
centro_a_la_derecha = (zonas.loc[zonas["grupo"] == "Manhattan central", "pc1"].mean()
                       > zonas.loc[zonas["grupo"] == "Barrios periféricos", "pc1"].mean())
noche_arriba = zonas.loc[zonas["grupo"] == "Vida nocturna", "pc2"].mean() > zonas["pc2"].mean()
eje_x = "← más periférico · más céntrico →" if centro_a_la_derecha else "← más céntrico · más periférico →"
eje_y = "más vida nocturna →" if noche_arriba else "← más vida nocturna"

izquierda, derecha = st.columns([3, 2])
with izquierda:
    st.subheader("Mapa de parecidos")
    fig = px.scatter(filtradas, x="pc1", y="pc2", color="grupo", size="viajes_por_dia",
                     color_discrete_map={g: d["color"] for g, d in GRUPOS.items()}, custom_data=["zona_id"],
                     hover_name="nombre",
                     hover_data={"distrito": True, "viajes_por_dia": ":,.0f", "pc1": False, "pc2": False,
                                 "zona_id": False, "grupo": False},
                     labels={"pc1": eje_x, "pc2": eje_y, "grupo": "Tipo", "viajes_por_dia": "Viajes al día",
                             "distrito": "Distrito"})
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    evento = st.plotly_chart(fig, on_select="rerun", selection_mode=("points", "box", "lasso"), key="mapa")
    st.caption(":material/touch_app: Seleccioná zonas en el mapa (clic, caja o lazo) para compararlas.")

ids = [punto["customdata"][0] for punto in evento.selection.points]
seleccion = filtradas[filtradas["zona_id"].isin(ids)] if ids else filtradas.nlargest(3, "viajes")

with derecha:
    st.subheader("¿A qué hora se usan?")
    curvas = seleccion.head(8).set_index("nombre")[HORAS].T
    curvas.index = range(24)
    fig_perfil = px.line(curvas, labels={"index": "Hora del día", "value": "Parte de los viajes del día",
                                         "nombre": "Zona"})
    fig_perfil.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                             legend=dict(orientation="h", y=-0.3, title_text=""))
    fig_perfil.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_perfil)
    st.caption("Las zonas seleccionadas." if ids else "Las 3 zonas con más viajes. Seleccioná otras en el mapa.")

st.subheader("Detalle por zona")
detalle = seleccion.sort_values("viajes_por_dia", ascending=False)[
    ["nombre", "grupo", "viajes_por_dia", "distancia_mediana", "pct_noche", "pct_fin_de_semana",
     "propina_mediana", "perfil"]]
st.dataframe(
    detalle.style.map(colorear_grupo, subset=["grupo"]),
    hide_index=True,
    width="stretch",
    column_config={
        "nombre": st.column_config.TextColumn("Zona", width="medium"),
        "grupo": st.column_config.TextColumn("Tipo de zona", width="medium"),
        "viajes_por_dia": st.column_config.NumberColumn("Viajes/día", format="%.0f", width="small"),
        "distancia_mediana": st.column_config.NumberColumn("Distancia", format="%.1f mi", width="small"),
        "pct_noche": st.column_config.ProgressColumn("De noche", format="percent", min_value=0, max_value=1,
                                                     width="small"),
        "pct_fin_de_semana": st.column_config.NumberColumn("Finde", format="percent", width="small",
                                                           help="Parte de los viajes en sábado o domingo."),
        "propina_mediana": st.column_config.NumberColumn("Propina", format="dollar", width="small"),
        "perfil": st.column_config.LineChartColumn("Viajes de 0 a 23 h", y_min=0, width="medium"),
    },
)

with st.expander("¿Cómo se armaron los grupos? (K-Means, silueta y PCA)", icon=":material/science:"):
    st.markdown(
        "Cada zona se describió con 8 números: viajes por día (en escala logarítmica), distancia, tarifa y "
        "propina típicas, y qué parte de sus viajes son en fin de semana, de mañana, de tarde y de noche. "
        "Con eso, el algoritmo **K-Means** formó grupos de zonas parecidas. Para elegir cuántos grupos, se usó "
        "el **coeficiente de silueta**, que mide qué tan bien separados quedan (de −1 a 1, más es mejor): "
        f"el máximo está en **{metricas['k_elegido']} grupos**."
    )
    fig_sil = px.line(siluetas, x="k", y="silueta", markers=True,
                      labels={"k": "Cantidad de grupos (k)", "silueta": "Coeficiente de silueta"})
    fig_sil.add_vline(x=metricas["k_elegido"], line_dash="dot", line_color="#111111")
    fig_sil.update_traces(line_color="#111111", marker_color="#FCCC0A", marker_size=10)
    fig_sil.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_sil)
    v1, v2 = metricas["pca_varianza"]
    st.markdown(f"El mapa de parecidos resume las 8 variables en 2 ejes con **PCA**, que conservan el "
                f"**{v1 + v2:.0%}** de la información (eje horizontal: {v1:.0%}, vertical: {v2:.0%}). Es un "
                "resumen: dos zonas cercanas se parecen, pero las distancias no son exactas.")
