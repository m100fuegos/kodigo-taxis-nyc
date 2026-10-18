"""API de pronostico de demanda de taxis en Nueva York.
Carga el modelo de cuantiles y las horas ya preparadas por el notebook, y responde
a /info y /pronostico.
"""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException

CARPETA = Path(__file__).parent
CUANTILES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
NOMBRES_CUANTILES = [f"p{int(q * 100)}" for q in CUANTILES]
VARIABLES = ["lag_24", "lag_48", "lag_167", "lag_168", "lag_169", "media_dia_ant",
             "hora_del_dia", "dia_semana", "feriado", "zona"]

# Se ejecuta cuando arranca la API
modelo = xgb.XGBRegressor()
modelo.load_model(CARPETA / "modelo_pronostico.ubj")

demanda = pd.read_parquet(CARPETA / "demanda.parquet")
ZONAS = sorted(demanda["PULocationID"].unique().tolist())
demanda["zona"] = pd.Categorical(demanda["PULocationID"], categories=ZONAS)
demanda["fecha"] = demanda["hora"].dt.date
FECHAS = sorted(demanda["fecha"].unique())

app = FastAPI(
    title="Taxis NYC - API de pronostico",
    description="Viajes por hora que se esperan en cada zona, con cuantiles del 10% al 90%.",
    version="1.0",
)


def predecir(filas):
    """Los 9 cuantiles de cada fila, ordenados y sin negativos."""
    predicciones = modelo.predict(filas[VARIABLES])
    return np.clip(np.sort(predicciones, axis=1), 0, None)  # sin cuantiles cruzados ni negativos


def armar_horas(filas, predicciones):
    """Arma la lista de horas del contrato con las 24 filas de una zona y sus predicciones."""
    horas = []
    for fila, cuantiles in zip(filas.itertuples(), predicciones):
        horas.append({
            "hora": int(fila.hora_del_dia),
            "real": None if pd.isna(fila.viajes) else int(fila.viajes),
            "hace_una_semana": int(fila.lag_168),
            "cuantiles": {nombre: round(float(valor), 1) for nombre, valor in zip(NOMBRES_CUANTILES, cuantiles)},
        })
    return horas


def revisar_fecha(fecha):
    """Si la fecha no esta disponible, responde 404 con las fechas validas."""
    if fecha not in FECHAS:
        raise HTTPException(status_code=404, detail=f"No hay pronostico para {fecha}. Fechas disponibles: "
                                                    f"{FECHAS[0]} a {FECHAS[-1]}.")


@app.get("/")
def inicio():
    return {"estado": "en linea", "mensaje": "Prueba los endpoints en /docs"}


@app.get("/info")
def info():
    zonas = demanda.drop_duplicates("PULocationID").sort_values("nombre")
    return {
        "zonas": [
            {"id": int(fila.PULocationID), "nombre": fila.nombre, "distrito": fila.distrito}
            for fila in zonas.itertuples()
        ],
        "fechas": [f.isoformat() for f in FECHAS],
        "cuantiles": NOMBRES_CUANTILES,
    }


@app.get("/pronostico")
def pronostico(zona_id: int, fecha: date):
    if zona_id not in ZONAS:
        raise HTTPException(status_code=404, detail=f"La zona {zona_id} no tiene pronostico. Consulta /info.")
    revisar_fecha(fecha)

    filas = demanda[(demanda["PULocationID"] == zona_id) & (demanda["fecha"] == fecha)]
    primera = filas.iloc[0]
    return {
        "zona": {"id": zona_id, "nombre": primera["nombre"], "distrito": primera["distrito"]},
        "fecha": fecha.isoformat(),
        "horas": armar_horas(filas, predecir(filas)),
    }


@app.get("/pronostico_ciudad")
def pronostico_ciudad(fecha: date):
    """Extra: las 58 zonas de un dia en un solo pedido (lo usan el Inicio y el Plan de la ciudad)."""
    revisar_fecha(fecha)

    del_dia = demanda[demanda["fecha"] == fecha]
    predicciones = predecir(del_dia)  # las 58 zonas x 24 horas de una sola vez: mucho mas rapido

    zonas = []
    for zona_id, posiciones in del_dia.groupby("PULocationID").indices.items():
        filas = del_dia.iloc[posiciones]
        zonas.append({"id": int(zona_id), "nombre": filas["nombre"].iloc[0], "distrito": filas["distrito"].iloc[0],
                      "horas": armar_horas(filas, predicciones[posiciones])})
    return {"fecha": fecha.isoformat(), "zonas": zonas}