import os
from typing import Any, Dict, List

import requests


class AviationApiClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("AVIATION_API_KEY", "").strip()
        self.base_url = os.getenv("AVIATION_API_BASE", "http://api.aviationstack.com/v1").strip()

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("Missing AVIATION_API_KEY environment variable.")

    def _get(self, endpoint: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._ensure_key()
        url = f"{self.base_url}/{endpoint}"
        params = {**params, "access_key": self.api_key}
        response = requests.get(url, params=params, timeout=20)
        if response.status_code == 429:
            raise RuntimeError("API rate limit exceeded. Try again later.")
        if response.status_code >= 400:
            raise RuntimeError(f"API error: {response.status_code}")
        payload = response.json()
        return payload.get("data", [])

    def get_flight_by_number(self, flight_number: str) -> List[Dict[str, Any]]:
        return self._get("flights", {"flight_iata": flight_number})

    def get_departures(self, airport_iata: str) -> List[Dict[str, Any]]:
        return self._get("flights", {"dep_iata": airport_iata, "limit": 100})

    def get_arrivals(self, airport_iata: str) -> List[Dict[str, Any]]:
        return self._get("flights", {"arr_iata": airport_iata, "limit": 100})

    def get_airport_country(self, airport_iata: str) -> str:
        if not airport_iata:
            return ""
        data = self._get("airports", {"iata_code": airport_iata, "limit": 1})
        if not data:
            return ""
        return (data[0].get("country_name") or "").strip()
