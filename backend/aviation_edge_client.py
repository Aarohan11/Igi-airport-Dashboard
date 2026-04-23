import os
from typing import Any, Dict, List

import requests


class AviationEdgeApiClient:
    """Client for the Aviation Edge API.

    API docs: https://aviation-edge.com/
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("AVIATION_EDGE_API_KEY", "").strip()
        self.base_url = os.getenv("AVIATION_EDGE_BASE", "https://aviation-edge.com/v2/public").strip()

    def _ensure_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("Missing AVIATION_EDGE_API_KEY environment variable.")

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Any:
        self._ensure_key()
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, params={**params, "key": self.api_key}, timeout=20)
        if response.status_code == 429:
            raise RuntimeError("Aviation Edge rate limit exceeded. Try again later.")
        if response.status_code >= 400:
            raise RuntimeError(f"Aviation Edge API error: {response.status_code}")
        payload = response.json()
        if isinstance(payload, dict) and payload.get("error"):
            raise RuntimeError(f"Aviation Edge API error: {payload.get('error')}")
        return payload

    def get_departures(self, airport_iata: str) -> List[Dict[str, Any]]:
        code = (airport_iata or "").strip().upper()
        if not code:
            return []
        payload = self._get("flights", {"depIata": code})
        if isinstance(payload, list):
            return payload
        return []

    def get_arrivals(self, airport_iata: str) -> List[Dict[str, Any]]:
        code = (airport_iata or "").strip().upper()
        if not code:
            return []
        payload = self._get("flights", {"arrIata": code})
        if isinstance(payload, list):
            return payload
        return []

    def get_flight_by_number(self, flight_number: str) -> List[Dict[str, Any]]:
        number = (flight_number or "").strip().upper()
        if not number:
            return []
        payload = self._get("flights", {"flightIata": number})
        if isinstance(payload, list):
            return payload
        return []
