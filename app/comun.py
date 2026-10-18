"""Funciones que comparten todas las paginas: hablar con la API, el estilo visual, los selectores y la decision."""
import json
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st

CARPETA_DATA = Path(__file__).parent / "data"
URL_LOCAL = "http://localhost:8000"
FECHA_MANANA = "2024-02-01"
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["", "enero", "febrero"]
HORAS = [f"h{h:02d}" for h in range(24)]

# Colores de la app (los mismos de .streamlit/config.toml)
NEGRO = "#111111"
AMARILLO = "#FCCC0A"
AZUL = "#0039A6"
ROJO = "#EE352E"
VERDE = "#00933C"
GRIS = "#808183"
BANDA = "rgba(252, 204, 10, 0.35)"  # amarillo taxi transparente para el rango probable

# Cada tipo de zona tiene el color y la letra de una línea del metro de Nueva York
GRUPOS = {
    "Manhattan central": {"color": "#00933C", "badge": "green", "letra": "M"},
    "Vida nocturna": {"color": "#B933AD", "badge": "violet", "letra": "N"},
    "Aeropuertos": {"color": "#FF6319", "badge": "orange", "letra": "A"},
    "Barrios periféricos": {"color": "#0039A6", "badge": "blue", "letra": "B"},
}

# Valores iniciales de los dos costos (los cambia la gerente en Decisión o en el Plan de la ciudad)
COSTO_OCIOSO = 10
COSTO_PERDIDO = 40
ALTO_TARJETA = 140  # todas las tarjetas de una fila miden lo mismo


# ---------------------------------------------------------------- Estilo
def estilos():
    """Los detalles visuales que el tema no cubre: franja de taxi, círculos de línea y tarjeta de recomendación."""
    st.html("""<style>
    .franja{height:10px;margin:-.4rem 0 .2rem;border-radius:2px;
            background:repeating-conic-gradient(#111 0 25%, #FCCC0A 0 50%) 0 0/10px 10px}
    .bajada{font-size:1.05rem;color:#3c3c3a;max-width:70ch;margin:0}
    .linea{display:inline-flex;align-items:center;justify-content:center;width:1.65em;height:1.65em;
           border-radius:50%;color:#fff;font-family:Archivo,sans-serif;font-weight:800;font-size:.9em;
           margin-right:.45em;vertical-align:middle;flex:none}
    .grupo-nombre{display:flex;align-items:center;font-weight:700;font-size:1.02rem}
    .recomendacion{background:#FCCC0A;color:#111;border-radius:8px;padding:18px 22px;display:grid;gap:4px;
                   border:2px solid #111}
    .recomendacion .et{font-size:.85rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
    .recomendacion .valor{font-family:Archivo,sans-serif;font-size:2.4rem;font-weight:800;line-height:1.1;
                          font-variant-numeric:tabular-nums}
    .recomendacion .det{font-size:1rem}
    .grupos{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1rem}
    .tarjeta-grupo{border:1px solid #D6D6CF;border-top-width:6px;border-radius:6px;padding:14px 16px;
                   display:grid;gap:8px;align-content:start}
    .tarjeta-grupo .cifra{font-family:Archivo,sans-serif;font-size:1.9rem;font-weight:800;line-height:1}
    .tarjeta-grupo .cifra span{font-size:1rem;font-weight:600;margin-left:.35em}
    .tarjeta-grupo ul{margin:0;padding-left:1.1em;display:grid;gap:2px}
    .tarjeta-grupo p{margin:0;color:#55554f;font-size:.92rem}
    .bloques{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem}
    .bloque{border:1px solid #D6D6CF;border-top-width:6px;border-radius:6px;padding:16px 20px}
    .bloque h4{font-family:Archivo,sans-serif;font-size:1.3rem;font-weight:700;margin:0 0 10px}
    .bloque ul{margin:0;padding-left:1.2em;display:grid;gap:8px;line-height:1.5}
    .marca{display:grid;gap:2px;padding:4px 0 6px}
    .marca .damero{height:12px;width:96px;border-radius:2px;margin-bottom:8px;
                   background:repeating-conic-gradient(#F5F5F2 0 25%, #FCCC0A 0 50%) 0 0/12px 12px}
    .marca b{font-family:Archivo,sans-serif;font-size:1.35rem;letter-spacing:.04em;color:#F5F5F2}
    .marca span{font-size:.85rem;color:#c9c9c4}
    [data-testid="stMetricValue"]{font-variant-numeric:tabular-nums}
    </style>""")


def encabezado(titulo, bajada, ayuda):
    """Título de la página con la franja de taxi, una frase que explica la página y el botón de ayuda."""
    izquierda, derecha = st.columns([4, 1], vertical_alignment="bottom")
    izquierda.title(titulo)
    if derecha.button("¿Cómo leo esto?", icon=":material/help:", width="stretch", key="boton_ayuda"):
        ventana_ayuda(titulo, ayuda)
    st.html('<div class="franja"></div>')
    if bajada:
        st.html(f'<p class="bajada">{bajada}</p>')


@st.dialog("¿Cómo leo esta página?", width="medium")
def ventana_ayuda(titulo, puntos):
    st.markdown(f"#### {titulo}")
    st.markdown("\n".join(f"- {punto}" for punto in puntos))
    st.caption("Las palabras técnicas están explicadas en la página Glosario y ayuda.")


def fila_de_metricas(metricas, alto=ALTO_TARJETA):
    """Una fila de tarjetas del mismo ancho y el mismo alto. Cada métrica es un diccionario para st.metric."""
    for columna, metrica in zip(st.columns(len(metricas)), metricas):
        columna.metric(border=True, height=alto, **metrica)


def bloques_de_texto(bloques):
    """Tarjetas de texto lado a lado y del mismo alto. Cada bloque es (título, color, lista de frases en HTML)."""
    tarjetas = "".join(
        f'<div class="bloque" style="border-top-color:{color}"><h4>{titulo}</h4><ul>'
        + "".join(f"<li>{frase}</li>" for frase in frases) + "</ul></div>"
        for titulo, color, frases in bloques)
    st.html(f'<div class="bloques">{tarjetas}</div>')


def recomendacion(titulo, valor, detalle):
    """La tarjeta amarilla con lo que hay que hacer: es lo primero que tiene que ver la gerente."""
    st.html(f'<div class="recomendacion"><span class="et">{titulo}</span>'
            f'<span class="valor">{valor}</span><span class="det">{detalle}</span></div>')


def circulo(grupo):
    """El círculo de color con la letra del tipo de zona, como el de una línea del metro, y su nombre."""
    datos = GRUPOS.get(grupo, {"color": GRIS, "letra": "?"})
    return (f'<span class="grupo-nombre"><span class="linea" style="background:{datos["color"]}">'
            f'{datos["letra"]}</span>{grupo}</span>')


def colorear_grupo(grupo):
    """Para las tablas: pinta la celda del tipo de zona con el color de su línea."""
    color = GRUPOS.get(grupo, {"color": GRIS})["color"]
    return f"background-color: {color}; color: white; font-weight: 600"


def ajustar_grafico(fig, alto=380):
    """El mismo aspecto para todos los gráficos: leyenda abajo, márgenes chicos y todos los valores al pasar el mouse."""
    fig.update_layout(height=alto, hovermode="x unified", margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=-0.22, x=0, title_text=""))
    return fig


# ---------------------------------------------------------------- Textos
def nombre_fecha(texto, con_mes=False):
    """'2024-01-25' -> 'jue 25' (o 'jue 25 de enero'). El 1 de febrero se marca como mañana."""
    f = date.fromisoformat(texto)
    etiqueta = f"{DIAS[f.weekday()]} {f.day}"
    if con_mes:
        etiqueta += f" de {MESES[f.month]}"
    if texto == FECHA_MANANA:
        etiqueta += " (mañana)" if not con_mes else " (pronóstico a futuro)"
    return etiqueta


def fecha_larga(texto):
    """'2024-02-01' -> 'jueves 1 de febrero'."""
    f = date.fromisoformat(texto)
    return f"{DIAS_LARGOS[f.weekday()]} {f.day} de {MESES[f.month]}"


def cambio_texto(nuevo, viejo):
    """'12% más' o '5% menos' que antes, en palabras."""
    cambio = nuevo / viejo - 1 if viejo else 0
    return f"{abs(cambio):.0%} {'más' if cambio >= 0 else 'menos'}"


# ---------------------------------------------------------------- Datos del notebook
def sin_tildes(texto):
    """'periféricos' -> 'perifericos'. Sirve para comparar nombres aunque uno venga sin tildes."""
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()


def nombre_grupo(texto):
    """Devuelve el nombre oficial del grupo aunque el archivo lo traiga sin tildes."""
    for nombre in GRUPOS:
        if sin_tildes(nombre) == sin_tildes(texto):
            return nombre
    return texto


@st.cache_data
def cargar_zonas():
    """Las 90 zonas segmentadas por el notebook, con su grupo y sus 24 proporciones horarias."""
    zonas = pd.read_csv(CARPETA_DATA / "zonas_segmentadas.csv")
    zonas["grupo"] = zonas["grupo"].map(nombre_grupo)
    zonas["perfil"] = zonas[HORAS].values.tolist()
    return zonas


@st.cache_data
def cargar_metricas():
    """Las cifras de la ficha que guardó el notebook en metricas.json."""
    with open(CARPETA_DATA / "metricas.json", encoding="utf-8") as f:
        metricas = json.load(f)
    for fila in metricas["por_grupo"]:
        fila["grupo"] = nombre_grupo(fila["grupo"])
    return metricas


@st.cache_data
def cargar_siluetas():
    return pd.read_csv(CARPETA_DATA / "siluetas.csv")


def grupo_por_zona():
    """Diccionario número de zona -> tipo de zona."""
    zonas = cargar_zonas()
    return dict(zip(zonas["zona_id"], zonas["grupo"]))


# ---------------------------------------------------------------- API
def url_api():
    """La dirección de la API: la que se escribió en la barra lateral, la de Secrets o la local."""
    if st.session_state.get("url_api"):
        return st.session_state["url_api"].rstrip("/")
    try:
        return st.secrets["API_URL"].rstrip("/")
    except Exception:  # no hay secrets.toml o no tiene API_URL
        return URL_LOCAL


@st.cache_data(ttl=3600, show_spinner=False)
def _consultar(url, ruta, params=None):
    """Hace la petición. Si falla, lanza la excepción (y no se guarda en caché)."""
    respuesta = requests.get(f"{url}{ruta}", params=params, timeout=90)
    respuesta.raise_for_status()
    return respuesta.json()


def conectar():
    """Pide /info mostrando el avance. Si la API no responde, lo explica y detiene la página."""
    error = None
    with st.status("Conectando con el servicio de pronósticos...", expanded=False) as estado:
        try:
            info = _consultar(url_api(), "/info")
            estado.update(label="Pronósticos al día", state="complete")
            # Lo que se ve al desplegar el recuadro
            st.markdown(f"- **{len(info['zonas'])} zonas** con pronóstico, del {fecha_larga(info['fechas'][0])} al "
                        f"{fecha_larga(info['fechas'][-1])} (mañana).")
            st.caption(f"Servicio de pronósticos: {url_api()}")
        except requests.RequestException as e:
            error = e
            estado.update(label="El servicio de pronósticos no respondió", state="error")

    if error is not None:
        st.sidebar.badge("Pronósticos sin conexión", icon=":material/cloud_off:", color="red")
        st.error(
            "No pudimos traer los pronósticos. El servicio se apaga solo cuando nadie lo usa y tarda cerca de "
            f"un minuto en despertar: esperá un momento y recargá la página.\n\nDetalle técnico: {error}",
            icon=":material/cloud_off:",
        )
        st.stop()
    st.sidebar.badge("Pronósticos en línea", icon=":material/cloud_done:", color="green")
    return info


def _pedir(ruta, params):
    """Pide algo a la API; si falla, muestra un mensaje claro y detiene la página."""
    try:
        return _consultar(url_api(), ruta, params)
    except requests.HTTPError as e:
        detalle = e.response.json().get("detail", str(e)) if e.response is not None else str(e)
        st.warning(f"No hay pronóstico para lo que pediste: {detalle}", icon=":material/search_off:")
        st.stop()
    except requests.RequestException as e:
        st.error(f"Se perdió la conexión con el servicio de pronósticos. Recargá la página en un minuto.\n\n"
                 f"Detalle técnico: {e}", icon=":material/cloud_off:")
        st.stop()


def pedir_pronostico(zona_id, fecha):
    """Las 24 horas de una zona y fecha, tal como las devuelve /pronostico."""
    return _pedir("/pronostico", {"zona_id": zona_id, "fecha": fecha})


def pedir_ciudad(fecha):
    """Las 58 zonas de un día en un solo pedido (endpoint extra /pronostico_ciudad)."""
    return _pedir("/pronostico_ciudad", {"fecha": fecha})


def tabla_horas(datos):
    """De JSON a tabla: una fila por hora con el real, el de hace una semana y los 9 cuantiles."""
    return pd.DataFrame([{"hora": h["hora"], "real": h["real"], "hace_una_semana": h["hace_una_semana"],
                          **h["cuantiles"]} for h in datos["horas"]])


def tabla_ciudad(ciudad):
    """De JSON a tabla: una fila por zona y hora, con el tipo de zona de la segmentación."""
    grupos = grupo_por_zona()
    tabla = pd.DataFrame([{"zona_id": z["id"], "zona": z["nombre"], "distrito": z["distrito"], "hora": h["hora"],
                           "real": h["real"], "hace_una_semana": h["hace_una_semana"], **h["cuantiles"]}
                          for z in ciudad["zonas"] for h in z["horas"]])
    tabla["tipo"] = tabla["zona_id"].map(grupos)
    return tabla


def resumen_por_zona(tabla):
    """Una fila por zona: viajes esperados, taxis del plan, su hora más fuerte y el cambio frente a hace una semana.
    La tabla tiene que traer la columna 'taxis' (los taxis recomendados en cada hora)."""
    por_zona = tabla.groupby(["zona_id", "zona", "distrito", "tipo"], as_index=False, dropna=False).agg(
        esperados=("p50", "sum"), semana=("hace_una_semana", "sum"), taxis=("taxis", "sum"))
    picos = tabla.loc[tabla.groupby("zona_id")["taxis"].idxmax(), ["zona_id", "hora", "taxis"]]
    picos = picos.rename(columns={"hora": "hora_pico", "taxis": "taxis_pico"})
    por_zona = por_zona.merge(picos, on="zona_id")
    por_zona["cambio"] = por_zona["esperados"] / por_zona["semana"] - 1
    return por_zona.sort_values("taxis", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- Decisión
def nivel_de_servicio(costo_ocioso, costo_perdido):
    """El cuantil óptimo (problema del vendedor de periódicos) y el más cercano que entrega la API."""
    optimo = costo_perdido / (costo_perdido + costo_ocioso)
    usado = min(max(round(optimo * 10) / 10, 0.1), 0.9)  # la API da del p10 al p90
    return optimo, usado, f"p{round(usado * 100)}"


def costo(enviados, real, costo_ocioso, costo_perdido):
    """Costo total: taxis de más por su costo + pasajeros sin taxi por el suyo."""
    sobran = np.maximum(enviados - real, 0)
    faltan = np.maximum(real - enviados, 0)
    return float((sobran * costo_ocioso + faltan * costo_perdido).sum())


def costos_actuales():
    """Los costos que eligió la gerente (o los iniciales si todavía no tocó los controles)."""
    return (st.session_state.get("costo_ocioso", COSTO_OCIOSO),
            st.session_state.get("costo_perdido", COSTO_PERDIDO))


def controles_de_costo():
    """Los dos controles de costo. Arrancan con los últimos valores elegidos, así se recuerdan entre páginas."""
    ocioso, perdido = costos_actuales()
    c1, c2 = st.columns(2)
    costo_ocioso = c1.slider(
        "¿Cuánto cuesta un taxi una hora sin pasajero? (USD)", 1, 100, ocioso, key="control_ocioso",
        help="Combustible y horas de conductor que se pagan sin ingresos.")
    costo_perdido = c2.slider(
        "¿Cuánto cuesta un pasajero que no encontró taxi? (USD)", 1, 100, perdido, key="control_perdido",
        help="El viaje que se pierde y el cliente que se va a la competencia.")
    # La memoria de la sesión: la leen el Inicio, la Decisión y el Plan de la ciudad
    st.session_state["costo_ocioso"] = costo_ocioso
    st.session_state["costo_perdido"] = costo_perdido
    return costo_ocioso, costo_perdido


# ---------------------------------------------------------------- Selectores y barra lateral
def elegir_zona(info):
    """Selector de zona. Arranca con la última zona elegida (o la del link) y la deja en el link (?zona=161)."""
    zonas = {z["id"]: f"{z['nombre']} ({z['distrito']})" for z in info["zonas"]}
    ids = list(zonas)
    elegida = st.session_state.get("zona_elegida")
    if elegida not in ids:  # primera vez en la sesión: la del link compartido, o Midtown Center
        del_link = st.query_params.get("zona", "")
        elegida = int(del_link) if del_link.isdigit() and int(del_link) in ids else (161 if 161 in ids else ids[0])
    zona = st.selectbox("Zona", ids, index=ids.index(elegida), format_func=zonas.get,
                        filter_mode="contains", key="selector_zona",
                        help="Hacé clic y escribí parte del nombre o del distrito, por ejemplo «airport» o «Queens».")
    st.session_state["zona_elegida"] = zona
    st.query_params["zona"] = str(zona)
    return zona


def elegir_fecha(info):
    """Botones de fecha. Arrancan con el último día elegido (o el del link) y lo dejan en el link."""
    fechas = info["fechas"]
    elegida = st.session_state.get("fecha_elegida")
    if elegida not in fechas:  # primera vez en la sesión: el del link compartido, o el primero
        del_link = st.query_params.get("fecha", "")
        elegida = del_link if del_link in fechas else fechas[0]
    fecha = st.segmented_control("Día", fechas, default=elegida, required=True, format_func=nombre_fecha,
                                 key="selector_fecha")
    st.session_state["fecha_elegida"] = fecha
    st.query_params["fecha"] = fecha
    return fecha


def elegir_zona_y_fecha(info):
    """Selector de zona (en una columna, para que no quede enorme) y, debajo, los botones de fecha."""
    columna, _ = st.columns([2, 3])
    with columna:
        zona = elegir_zona(info)
    return zona, elegir_fecha(info)


def barra_lateral(paginas):
    """Lo que se ve en la barra lateral en todas las páginas: la marca, el menú y la conexión."""
    with st.sidebar:
        st.html('<div class="marca"><div class="damero"></div><b>TAXIS NYC</b>'
                '<span>Centro de operaciones</span></div>')
        for seccion, lista in paginas.items():
            if seccion:  # "Resumen de mañana" no tiene sección
                st.caption(f"**{seccion}**")
            for pagina in lista:
                st.page_link(pagina)  # usa el título y el ícono de cada st.Page
        st.divider()
        st.caption("Pronósticos de taxis de Nueva York con datos de enero de 2024.")
        with st.popover("Configurar conexión", icon=":material/settings:"):
            st.text_input("Dirección del servicio de pronósticos (API)", value=url_api(), key="url_api",
                          help="Por defecto se usa API_URL de Secrets. Cámbiala para probar otra API.")
            st.caption(f"Ahora se usa: {url_api()}")
