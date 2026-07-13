import csv
import json
import logging
import os
from pathlib import Path

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "objetos.csv"


class ObtenerTiempoSchema(BaseModel):
    ciudad: str


class ObtenerObjetosSchema(BaseModel):
    pass


def make_obtener_tiempo_coroutine():
    async def call_obtener_tiempo(ciudad: str) -> str:
        """Consults current weather for a city using the wttr.in public API."""
        url = f"https://wttr.in/{httpx.utils.quote(ciudad)}?format=j1&lang=es"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            current = data["current_condition"][0]
            result = {
                "ciudad": ciudad,
                "temperatura_c": int(current["temp_C"]),
                "sensacion_termica_c": int(current["FeelsLikeC"]),
                "descripcion": current["lang_es"][0]["value"],
                "humedad_pct": int(current["humidity"]),
                "precipitacion_mm": float(current["precipMM"]),
            }
            logger.info("Weather retrieved for '%s': %s°C, %s", ciudad, result["temperatura_c"], result["descripcion"])
            return json.dumps(result, ensure_ascii=False)
        except httpx.HTTPError as exc:
            logger.warning("HTTP error fetching weather for '%s': %s", ciudad, exc)
            return json.dumps({"error": f"Could not retrieve weather for '{ciudad}': {exc}"})
        except (KeyError, IndexError, ValueError) as exc:
            logger.warning("Unexpected wttr.in response for '%s': %s", ciudad, exc)
            return json.dumps({"error": f"Unexpected weather service response: {exc}"})

    return call_obtener_tiempo


def make_obtener_objetos_coroutine():
    async def call_obtener_objetos() -> str:
        """Returns the default packing list from the bundled CSV file."""
        try:
            objetos = []
            with open(_DATA_PATH, newline="", encoding="utf-8") as f:
                for fila in csv.reader(f):
                    if fila and fila[0].strip():
                        objetos.append(fila[0].strip())
            if not objetos:
                return json.dumps({"error": "The objects file is empty."})
            logger.info("Loaded %d objects from default packing list", len(objetos))
            return json.dumps({"objetos": objetos, "total": len(objetos)}, ensure_ascii=False)
        except (OSError, csv.Error) as exc:
            logger.error("Error reading objects CSV: %s", exc)
            return json.dumps({"error": f"Error reading packing list: {exc}"})

    return call_obtener_objetos


def get_recommender_tools() -> list:
    return [
        StructuredTool(
            name="obtener_tiempo",
            description=(
                "Retrieves current weather conditions for a city: temperature, "
                "description, humidity and precipitation. Always call this tool first "
                "to know the climate of the travel destination before classifying items."
            ),
            coroutine=make_obtener_tiempo_coroutine(),
            func=lambda **kwargs: "",
            args_schema=ObtenerTiempoSchema,
        ),
        StructuredTool(
            name="obtener_objetos",
            description=(
                "Returns the complete default packing list (items available to classify). "
                "Always call this tool to get the list of items before classifying them."
            ),
            coroutine=make_obtener_objetos_coroutine(),
            func=lambda **kwargs: "",
            args_schema=ObtenerObjetosSchema,
        ),
    ]
