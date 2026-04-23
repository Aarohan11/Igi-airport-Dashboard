"""AeroDataBox API client for real-time flight data."""

import os
from typing import Any, Dict, List, Optional
import requests


class AeroDataBoxApiClient:
    """Client for AeroDataBox real-time flight API via RapidAPI."""

    def __init__(self) -> None:
        self.api_key = os.getenv("AERODATABOX_API_KEY", "").strip()
        self.base_url = "https://aerodatabox.p.rapidapi.com"
        self.rapidapi_host = "aerodatabox.p.rapidapi.com"

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Make a request to AeroDataBox API."""
        if not self.api_key:
            raise ValueError("AERODATABOX_API_KEY environment variable not set")

        url = f"{self.base_url}{endpoint}"
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.rapidapi_host,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"AeroDataBox API error: {str(e)}")

    def get_departures(self, airport_iata: str) -> List[Dict[str, Any]]:
        """
        Fetch departures for a given airport.
        
        Args:
            airport_iata: IATA code (e.g., "DEL" for Delhi)
            
        Returns:
            List of flight dictionaries in standard format.
        """
        if airport_iata.upper() != "DEL":
            return []

        try:
            # AeroDataBox endpoint: /flights/airports/iata/{IATA CODE}/departures
            endpoint = f"/flights/airports/iata/{airport_iata.upper()}/departures"
            data = self._make_request(endpoint)

            # Parse response - AeroDataBox returns {"departures": [...]}
            departures = data.get("departures", [])
            
            # Normalize to standard format
            normalized = []
            for flight in departures:
                try:
                    normalized_flight = self._normalize_flight(flight)
                    if normalized_flight:
                        normalized.append(normalized_flight)
                except Exception:
                    continue

            return normalized

        except Exception as e:
            raise RuntimeError(f"Failed to fetch departures from AeroDataBox: {str(e)}")

    def get_arrivals(self, airport_iata: str) -> List[Dict[str, Any]]:
        """Fetch arrivals for a given airport."""
        if airport_iata.upper() != "DEL":
            return []

        try:
            endpoint = f"/flights/airports/iata/{airport_iata.upper()}/arrivals"
            data = self._make_request(endpoint)
            arrivals = data.get("arrivals", [])

            normalized = []
            for flight in arrivals:
                try:
                    normalized_flight = self._normalize_flight(flight)
                    if normalized_flight:
                        normalized.append(normalized_flight)
                except Exception:
                    continue

            return normalized

        except Exception as e:
            raise RuntimeError(f"Failed to fetch arrivals from AeroDataBox: {str(e)}")

    def _normalize_flight(self, flight: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize AeroDataBox flight data to standard format.
        
        Expected AeroDataBox structure:
        {
            "number": "AI101",
            "callsign": "...",
            "icao24": "...",
            "aircraft": {"icaoCode": "A320", "iataCode": "A20"},
            "airline": {"icaoCode": "AIC", "iataCode": "AI", "name": "Air India"},
            "origin": {"icao": "VIDP", "iata": "DEL", "name": "..."},
            "destination": {"icao": "VABB", "iata": "BOM", "name": "..."},
            "scheduledDeparture": "2026-03-30T10:30:00+00:00",
            "estimatedDeparture": "2026-03-30T10:35:00+00:00",
            "status": "SCHEDULED",
            "gate": "123",
            "terminal": "3"
        }
        """
        flight_number = flight.get("number", "").strip().upper()
        destination_iata = (flight.get("destination") or {}).get("iata", "").strip().upper()

        if not flight_number or not destination_iata:
            return None

        aircraft = flight.get("aircraft") or {}
        airline = flight.get("airline") or {}
        departure_info = flight.get("departure") or {}

        # Map status to standard format
        raw_status = flight.get("status", "SCHEDULED").strip().upper()
        status_map = {
            "SCHEDULED": "scheduled",
            "ACTIVE": "active",
            "EN_ROUTE": "active",
            "LANDED": "landed",
            "CANCELLED": "cancelled",
            "BOARDING": "boarding",
            "GATE_CLOSED": "gate-closed",
        }
        normalized_status = status_map.get(raw_status, "scheduled")

        return {
            "flight_iata": flight_number,
            "flight_status": normalized_status,
            "status": normalized_status,
            "airline": {
                "name": airline.get("name") or "Unknown",
            },
            "departure": {
                "iata": "DEL",
                "airport": "Indira Gandhi International Airport",
                "terminal": str(flight.get("terminal") or "unknown"),
                "gate": flight.get("gate") or "TBD",
                "scheduled": flight.get("scheduledDeparture") or "",
                "estimated": flight.get("estimatedDeparture") or flight.get("scheduledDeparture") or "",
            },
            "arrival": {
                "iata": destination_iata,
                "airport": (flight.get("destination") or {}).get("name") or "Unknown",
            },
            "aircraft": {
                "iata": aircraft.get("iataCode") or "",
            },
            "provider": "aerodatabox",
            "confidence": "high",
        }
