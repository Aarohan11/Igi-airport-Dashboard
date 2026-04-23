"""Reliable multi-provider flight API client.

Provider order is configurable and defaults to trying real-time APIs first,
with local generated data used only as a last-resort fallback.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional

from api_client import AviationApiClient
from adsb_lol_client import AdsbLolApiClient
from aerodatabox_client import AeroDataBoxApiClient
from aviation_edge_client import AviationEdgeApiClient
from opensky_client import OpenSkyApiClient


class ReliableFlightApiClient:
    """Unified client that normalizes data from multiple providers."""

    _KNOWN_PROVIDERS = ("aerodatabox", "aviation_edge", "aviationstack", "adsb_lol", "opensky", "local")

    def __init__(self) -> None:
        self.base_url = "multi://flight-provider"
        self._flights_cache: List[Dict[str, Any]] | None = None
        self._arrivals_cache: List[Dict[str, Any]] | None = None
        self._cache_time: datetime | None = None
        self._arrivals_cache_time: datetime | None = None
        try:
            self.cache_duration_seconds = max(0, int(os.getenv("FLIGHT_CACHE_SECONDS", "60")))
        except ValueError:
            self.cache_duration_seconds = 60

        # auto | aviation_edge | aviationstack | adsb_lol | opensky | local
        self.provider_preference = os.getenv("FLIGHT_DATA_PROVIDER", "auto").strip().lower()
        # By default we enforce real providers and still allow ADSB.lol as
        # emergency fallback when schedule APIs are unavailable.
        # Set ALLOW_LOW_CONFIDENCE_FALLBACK=true to additionally allow OpenSky/local.
        self.allow_low_confidence_fallback = os.getenv("ALLOW_LOW_CONFIDENCE_FALLBACK", "false").strip().lower() == "true"

        self._aerodatabox = AeroDataBoxApiClient()
        self._aviation_edge = AviationEdgeApiClient()
        self._aviationstack = AviationApiClient()
        self._adsb_lol = AdsbLolApiClient()
        self._opensky = OpenSkyApiClient()

    def _dedupe_flights(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: Dict[str, Dict[str, Any]] = {}
        for flight in flights:
            key = f"{flight.get('flight_iata')}|{(flight.get('departure') or {}).get('scheduled')}"
            unique[key] = flight
        return list(unique.values())

    def _get_provider_order(self) -> List[str]:
        trusted_default = ["aerodatabox", "aviation_edge", "aviationstack", "adsb_lol"]
        permissive_default = ["aerodatabox", "aviation_edge", "aviationstack", "adsb_lol", "opensky", "local"]

        # Explicit provider selection should be honored as single-provider mode.
        if self.provider_preference in self._KNOWN_PROVIDERS:
            return [self.provider_preference]

        return permissive_default if self.allow_low_confidence_fallback else trusted_default

    def _normalize_status(self, raw_status: str) -> str:
        status = (raw_status or "scheduled").strip().lower()
        status_map = {
            "active": "active",
            "en-route": "active",
            "enroute": "active",
            "in-air": "active",
            "in flight": "active",
            "in-flight": "active",
            "scheduled": "scheduled",
            "boarding": "boarding",
            "check-in": "check-in",
            "final-call": "final-call",
            "gate-closed": "gate-closed",
            "landed": "landed",
            "arrived": "landed",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "delayed": "scheduled",
        }
        return status_map.get(status, "scheduled")

    def _iso_or_none(self, value: str) -> Optional[str]:
        cleaned = (value or "").strip()
        if not cleaned:
            return None
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return None

    def _normalize_single_flight(
        self,
        item: Dict[str, Any],
        source: str,
        movement: str = "departures",
    ) -> Optional[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()

        if source == "aerodatabox":
            flight_iata = (item.get("flight") or {}).get("iataNumber") or item.get("flightIata") or item.get("flight_iata")
            airline_name = (item.get("airline") or {}).get("name") or item.get("airlineName")
            departure_iata = (item.get("departure") or {}).get("iata") or item.get("departureIata") or "DEL"
            arrival_iata = (item.get("arrival") or {}).get("iata") or item.get("arrivalIata")
            scheduled = (item.get("departure") or {}).get("scheduled") or item.get("departureTime")
            estimated = (item.get("departure") or {}).get("estimated") or item.get("departureTime")
            terminal = (item.get("departure") or {}).get("terminal") or item.get("departureTerminal")
            gate = (item.get("departure") or {}).get("gate") or item.get("departureGate")
            aircraft_iata = (item.get("aircraft") or {}).get("iataCode") or item.get("aircraftIata")
            raw_status = item.get("status") or item.get("flight_status") or "scheduled"
        elif source == "aviation_edge":
            flight_iata = (item.get("flight", {}) or {}).get("iataNumber") or item.get("flightIata")
            airline_name = (item.get("airline", {}) or {}).get("name") or item.get("airlineName")
            departure_iata = (item.get("departure", {}) or {}).get("iataCode") or item.get("departureIata") or "DEL"
            arrival_iata = (item.get("arrival", {}) or {}).get("iataCode") or item.get("arrivalIata")
            scheduled = (item.get("departure", {}) or {}).get("scheduledTime") or item.get("departureTime")
            estimated = (item.get("departure", {}) or {}).get("estimatedTime") or item.get("departureTime")
            terminal = (item.get("departure", {}) or {}).get("terminal") or item.get("departureTerminal")
            gate = (item.get("departure", {}) or {}).get("gate") or item.get("departureGate")
            aircraft_iata = (item.get("aircraft", {}) or {}).get("iataCode") or item.get("aircraftIata")
            raw_status = item.get("status") or item.get("flight_status") or "scheduled"
        elif source == "aviationstack":
            flight_iata = item.get("flight_iata") or (item.get("flight") or {}).get("iata")
            airline_name = (item.get("airline") or {}).get("name")
            departure_iata = (item.get("departure") or {}).get("iata") or "DEL"
            arrival_iata = (item.get("arrival") or {}).get("iata")
            scheduled = (item.get("departure") or {}).get("scheduled")
            estimated = (item.get("departure") or {}).get("estimated")
            terminal = (item.get("departure") or {}).get("terminal")
            gate = (item.get("departure") or {}).get("gate")
            aircraft_iata = (item.get("aircraft") or {}).get("iata")
            raw_status = item.get("flight_status") or item.get("status") or "scheduled"
        elif source == "opensky":
            flight_iata = item.get("flight_iata") or (item.get("flight") or {}).get("iata") or item.get("flight_number")
            airline_name = (item.get("airline") or {}).get("name") or item.get("airline_name")
            departure_iata = (item.get("departure") or {}).get("iata") or "DEL"
            arrival_iata = (item.get("arrival") or {}).get("iata")
            scheduled = (item.get("departure") or {}).get("scheduled")
            estimated = (item.get("departure") or {}).get("estimated")
            terminal = (item.get("departure") or {}).get("terminal")
            gate = (item.get("departure") or {}).get("gate")
            aircraft_iata = (item.get("aircraft") or {}).get("iata")
            raw_status = item.get("flight_status") or item.get("status") or "scheduled"
        elif source == "adsb_lol":
            flight_iata = item.get("flight") or item.get("flight_iata")
            airline_name = item.get("airline_name") or "Unknown"
            departure_iata = item.get("departure_iata") or "DEL"
            arrival_iata = item.get("arrival_iata") or "UNK"
            scheduled = item.get("scheduled")
            estimated = item.get("estimated")
            terminal = item.get("terminal")
            gate = item.get("gate")
            aircraft_iata = item.get("aircraft_type") or item.get("t") or ""
            raw_status = item.get("status") or item.get("flight_status") or "scheduled"
        else:
            flight_iata = item.get("flight_iata")
            airline_name = (item.get("airline") or {}).get("name")
            departure_iata = (item.get("departure") or {}).get("iata") or "DEL"
            arrival_iata = (item.get("arrival") or {}).get("iata")
            scheduled = (item.get("departure") or {}).get("scheduled")
            estimated = (item.get("departure") or {}).get("estimated")
            terminal = (item.get("departure") or {}).get("terminal")
            gate = (item.get("departure") or {}).get("gate")
            aircraft_iata = (item.get("aircraft") or {}).get("iata")
            raw_status = item.get("flight_status") or item.get("status") or "scheduled"

        flight_iata = (flight_iata or "").strip().upper()
        arrival_iata = (arrival_iata or "").strip().upper()
        departure_iata = (departure_iata or "DEL").strip().upper()
        if not flight_iata or not arrival_iata:
            return None

        if movement == "departures" and departure_iata != "DEL":
            return None
        if movement == "arrivals" and arrival_iata != "DEL":
            return None

        # In strict mode we reject records without reliable schedule timestamps.
        if not self.allow_low_confidence_fallback and not scheduled:
            return None

        normalized_status = self._normalize_status(str(raw_status))

        return {
            "flight_iata": flight_iata,
            "flight_status": normalized_status,
            "status": normalized_status,
            "airline": {
                "name": airline_name or "Unknown",
            },
            "departure": {
                "iata": departure_iata,
                "airport": (item.get("departure") or {}).get("airport") or "Indira Gandhi International Airport",
                "terminal": str(terminal) if terminal not in (None, "") else "unknown",
                "gate": gate or "TBD",
                "scheduled": self._iso_or_none(str(scheduled or "")) or now_iso,
                "estimated": self._iso_or_none(str(estimated or "")) or self._iso_or_none(str(scheduled or "")) or now_iso,
            },
            "arrival": {
                "iata": arrival_iata,
                "airport": (item.get("arrival") or {}).get("airport") or "Unknown",
            },
            "aircraft": {
                "iata": aircraft_iata or "",
            },
            "provider": source,
            "confidence": "high" if source in ("aerodatabox", "aviation_edge", "aviationstack") else "low",
        }

    def _normalize_flights(
        self,
        flights: List[Dict[str, Any]],
        source: str,
        movement: str = "departures",
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in flights:
            if not isinstance(item, dict):
                continue
            normalized_item = self._normalize_single_flight(item, source, movement)
            if normalized_item is not None:
                normalized.append(normalized_item)

        return self._dedupe_flights(normalized)

    def _get_flights_from_provider(self, provider: str, airport_iata: str, movement: str = "departures") -> List[Dict[str, Any]]:
        if provider == "aerodatabox":
            raw = self._aerodatabox.get_departures(airport_iata) if movement == "departures" else self._aerodatabox.get_arrivals(airport_iata)
            return self._normalize_flights(raw, "aerodatabox", movement)
        if provider == "aviation_edge":
            raw = self._aviation_edge.get_departures(airport_iata) if movement == "departures" else self._aviation_edge.get_arrivals(airport_iata)
            return self._normalize_flights(raw, "aviation_edge", movement)
        if provider == "aviationstack":
            raw = self._aviationstack.get_departures(airport_iata) if movement == "departures" else self._aviationstack.get_arrivals(airport_iata)
            return self._normalize_flights(raw, "aviationstack", movement)
        if provider == "adsb_lol":
            if movement == "arrivals":
                return []
            raw = self._adsb_lol.get_departures(airport_iata)
            return self._normalize_flights(raw, "adsb_lol", movement)
        if provider == "opensky":
            if movement == "arrivals":
                return []
            raw = self._opensky.get_departures(airport_iata)
            return self._normalize_flights(raw, "opensky", movement)
        return []

    def _ensure_cache(self, airport_iata: str, movement: str = "departures") -> None:
        now = datetime.now(timezone.utc)
        cache = self._flights_cache if movement == "departures" else self._arrivals_cache
        cache_time = self._cache_time if movement == "departures" else self._arrivals_cache_time
        if (
            cache is not None
            and cache_time is not None
            and (now - cache_time).total_seconds() <= self.cache_duration_seconds
        ):
            return

        last_error: Optional[Exception] = None
        had_previous_cache = bool(cache)
        for provider in self._get_provider_order():
            try:
                flights = self._get_flights_from_provider(provider, airport_iata, movement)
                if flights:
                    if movement == "departures":
                        self._flights_cache = flights
                        self._cache_time = now
                    else:
                        self._arrivals_cache = flights
                        self._arrivals_cache_time = now
                    return
            except Exception as exc:
                last_error = exc

        if last_error:
            raise RuntimeError(f"No flight data provider available. Last error: {last_error}")

        if had_previous_cache:
            # Preserve last known non-empty snapshot when provider is temporarily empty.
            return

        if movement == "departures":
            self._flights_cache = []
            self._cache_time = now
        else:
            self._arrivals_cache = []
            self._arrivals_cache_time = now

    def get_departures(self, airport_iata: str) -> List[Dict[str, Any]]:
        code = (airport_iata or "").strip().upper()
        if code != "DEL":
            return []
        self._ensure_cache(code, "departures")
        return self._flights_cache or []

    def get_arrivals(self, airport_iata: str) -> List[Dict[str, Any]]:
        code = (airport_iata or "").strip().upper()
        if code != "DEL":
            return []
        self._ensure_cache(code, "arrivals")
        return self._arrivals_cache or []

    def get_movements(self, airport_iata: str) -> Dict[str, List[Dict[str, Any]]]:
        code = (airport_iata or "").strip().upper()
        if code != "DEL":
            return {"departures": [], "arrivals": []}
        return {
            "departures": self.get_departures(code),
            "arrivals": self.get_arrivals(code),
        }

    def get_flight_by_number(self, flight_number: str) -> List[Dict[str, Any]]:
        self._ensure_cache("DEL", "departures")
        self._ensure_cache("DEL", "arrivals")
        wanted = (flight_number or "").strip().upper()
        if not wanted:
            return []
        for flight in (self._flights_cache or []) + (self._arrivals_cache or []):
            if (flight.get("flight_iata") or "").upper() == wanted:
                return [flight]
        return []

    def get_airport_country(self, airport_iata: str) -> str:
        code = (airport_iata or "").strip().upper()
        if not code:
            return ""

        country_map = {
            "DEL": "India",
            "BOM": "India",
            "BLR": "India",
            "CCU": "India",
            "HYD": "India",
            "MAA": "India",
            "COK": "India",
            "PNQ": "India",
            "IXC": "India",
            "JAI": "India",
            "LKO": "India",
            "GOI": "India",
            "IDR": "India",
            "LHR": "United Kingdom",
            "CDG": "France",
            "DXB": "United Arab Emirates",
            "AUH": "United Arab Emirates",
            "DOH": "Qatar",
            "IST": "Turkey",
            "FRA": "Germany",
            "MUC": "Germany",
            "BKK": "Thailand",
            "SIN": "Singapore",
            "KUL": "Malaysia",
            "HKG": "Hong Kong",
            "HND": "Japan",
            "NRT": "Japan",
            "PEK": "China",
            "PVG": "China",
            "ICN": "South Korea",
            "AMS": "Netherlands",
        }
        return country_map.get(code, "Unknown")


# Export the client
FlightApiClient = ReliableFlightApiClient
