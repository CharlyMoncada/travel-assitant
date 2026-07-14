import csv
import json
import logging
from pathlib import Path
from urllib.parse import quote

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "objetos.csv"


class GetWeatherSchema(BaseModel):
    city: str


class GetPackingItemsSchema(BaseModel):
    pass


def make_get_weather_coroutine():
    async def call_get_weather(city: str) -> str:
        """Consults current weather for a city using the wttr.in public API."""
        url = f"https://wttr.in/{quote(city)}?format=j1"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            current = data["current_condition"][0]
            result = {
                "city": city,
                "temperature_c": int(current["temp_C"]),
                "feels_like_c": int(current["FeelsLikeC"]),
                "description": current["weatherDesc"][0]["value"],
                "humidity_pct": int(current["humidity"]),
                "precipitation_mm": float(current["precipMM"]),
            }
            logger.info("Weather retrieved for '%s': %s°C, %s", city, result["temperature_c"], result["description"])
            return json.dumps(result, ensure_ascii=False)
        except httpx.HTTPError as exc:
            logger.warning("HTTP error fetching weather for '%s': %s", city, exc)
            return json.dumps({"error": f"Could not retrieve weather for '{city}': {exc}"})
        except (KeyError, IndexError, ValueError) as exc:
            logger.warning("Unexpected wttr.in response for '%s': %s", city, exc)
            return json.dumps({"error": f"Unexpected weather service response: {exc}"})

    return call_get_weather


def make_get_packing_items_coroutine():
    async def call_get_packing_items() -> str:
        """Returns the default packing list from the bundled CSV file."""
        try:
            items = []
            with open(_DATA_PATH, newline="", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if row and row[0].strip():
                        items.append(row[0].strip())
            if not items:
                return json.dumps({"error": "The objects file is empty."})
            logger.info("Loaded %d items from default packing list", len(items))
            return json.dumps({"items": items, "total": len(items)}, ensure_ascii=False)
        except (OSError, csv.Error) as exc:
            logger.error("Error reading objects CSV: %s", exc)
            return json.dumps({"error": f"Error reading packing list: {exc}"})

    return call_get_packing_items


def get_recommender_tools() -> list:
    return [
        StructuredTool(
            name="get_weather",
            description=(
                "Retrieves current weather conditions for a city: temperature, "
                "description, humidity and precipitation. Always call this tool first "
                "to know the climate of the travel destination before classifying items."
            ),
            coroutine=make_get_weather_coroutine(),
            func=lambda **kwargs: "",
            args_schema=GetWeatherSchema,
        ),
        StructuredTool(
            name="get_packing_items",
            description=(
                "Returns the complete default packing list (items available to classify). "
                "Always call this tool to get the list of items before classifying them."
            ),
            coroutine=make_get_packing_items_coroutine(),
            func=lambda **kwargs: "",
            args_schema=GetPackingItemsSchema,
        ),
    ]
