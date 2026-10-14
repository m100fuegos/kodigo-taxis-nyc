# Taxis NYC: una app para quien toma decisiones

Pronóstico de viajes por hora con incertidumbre, segmentación de zonas y una recomendación de cuántos taxis
enviar, para la gerencia de operaciones de una flota de taxis en Nueva York (datos de enero de 2024).

## Links

| Qué | Dónde |
|---|---|
| App (Streamlit Community Cloud) | https://kodigo-taxis-nyc.streamlit.app/ |
| API (Render) | https://kodigo-taxis-nyc.onrender.com/ |
| Documentación de la API | https://kodigo-taxis-nyc.onrender.com/docs |

La API está en el plan gratuito de Render: si nadie la usó en 15 minutos, tarda cerca de un minuto en despertar.

## Integrante

- William Medina (trabajo individual)

## Cómo está armado

```
taxis-nyc/
├── preparacion.ipynb       # datos, modelos y métricas
├── .streamlit/config.toml  # tema de colores (Streamlit Cloud lo lee desde la raíz)
├── api/                    # FastAPI, publicada en Render
│   ├── main.py
│   ├── modelo_pronostico.ubj
│   ├── demanda.parquet
│   └── requirements.txt
└── app/                    # Streamlit, publicada en Streamlit Community Cloud
    ├── streamlit_app.py    # punto de entrada (st.navigation)
    ├── comun.py            # conexión con la API, estilo visual, selectores y regla de decisión
    ├── paginas/            # las 8 páginas (abajo)
    ├── data/               # zonas segmentadas y métricas para la ficha
    └── requirements.txt
```

La app nunca carga el modelo: le pide el pronóstico a la API. Además del contrato (`/`, `/info` y
`/pronostico`), la API tiene un endpoint extra, `/pronostico_ciudad?fecha=...`, que devuelve las 58 zonas de un día
en un solo pedido.

## Qué ve la gerente

La app está escrita para alguien que no sabe de machine learning: lenguaje simple (con el término técnico al lado),
un botón "¿Cómo leo esto?" en cada página y un estilo inspirado en el metro de Nueva York, donde cada tipo de zona tiene el color y la letra de una línea.

| Página | Para qué |
|---|---|
| Resumen de mañana | Qué preparar para el 1 de febrero en toda la ciudad: taxis en la hora pico, zonas que más necesitan y cambios frente a la semana anterior |
| Pronóstico por zona | Parte 1: viajes esperados hora por hora con su rango probable (cuantiles 10% a 90%) y los valores reales |
| ¿Cuántos taxis enviar? | Parte 3: dos costos, el cuantil óptimo con su fórmula, la recomendación explicada, costos de días reales y descarga |
| Plan de la ciudad | Extra: el plan de las 58 zonas a la vez, con mapa de calor de dónde y cuándo, y descarga en un archivo |
| Tipos de zona | Parte 2: K-Means, silueta, PCA, grupos con nombre y descripción, y selección de zonas en el gráfico |
| ¿Cuánto confiar? (ficha) | Parte 4: métricas frente a reglas simples, cobertura, error por tipo de zona, SHAP, limitaciones y usos no recomendados |
| Alertas del modelo | Extra: error día por día de la semana de prueba con un límite configurable |
| Glosario y ayuda | Extra: cómo usar la app en tres pasos, qué significa cada color y un glosario con buscador |

## Resultados (semana de prueba, 25 al 31 de enero)

| Regla | Error promedio por hora |
|---|---|
| Igual que ayer | 21.3 viajes |
| Igual que hace una semana | 11.9 viajes |
| Modelo (mediana, XGBoost con 9 cuantiles) | 11.6 viajes |

- El modelo le gana por poco (2%) a "igual que hace una semana". Su valor está en el rango: la banda del
  10% al 90% contiene la demanda real en el 81% de las horas.
- Con costos de USD 10 (taxi ocioso) y USD 40 (pasajero perdido), enviar el cuantil 80% costó 24% menos
  que enviar el pronóstico central y 30% menos que enviar lo de hace una semana, sumando las 58 zonas.
- K-Means agrupa 90 zonas en 4 tipos (silueta máxima en k = 4): Manhattan central, Vida nocturna,
  Aeropuertos y Barrios periféricos.

## Cómo correrlo en tu computadora

```bash
pip install -r api/requirements.txt -r app/requirements.txt jupyter

# 1. Generar el modelo y los datos (descarga 50 MB la primera vez)
jupyter nbconvert --to notebook --execute --inplace preparacion.ipynb

# 2. La API, en una terminal
uvicorn main:app --reload --app-dir api        # http://localhost:8000/docs

# 3. La app, en otra terminal, desde la raíz del proyecto
streamlit run app/streamlit_app.py
```

Sin `.streamlit/secrets.toml`, la app usa `http://localhost:8000`. Para usar otra API, créalo con
`API_URL = "https://..."` (no se sube a GitHub).

## Funciones avanzadas de Streamlit que usa

`st.navigation` + `st.Page`, `@st.fragment`, `@st.dialog`, `st.plotly_chart(on_select="rerun")`,
`st.column_config` (barras y mini gráficos), `@st.cache_data`, `st.secrets`, `st.session_state` y
`st.query_params` (la zona, el día y los costos se recuerdan entre páginas y el link se puede compartir),
`st.status` y `st.toast`, `st.pills` y `st.segmented_control`, `st.badge` y `st.popover`,
`st.metric(chart_data=...)`, `st.feedback`, `st.page_link` y un tema propio en `.streamlit/config.toml`
(colores, tipografías Public Sans y Archivo, y barra lateral negra).