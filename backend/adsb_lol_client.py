import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import re

import requests


class AdsbLolApiClient:
    """Client for ADSB.lol public API."""

    _ICAO_TO_IATA = {
        "AIC": ("AI", "Air India"),
        "IGO": ("6E", "IndiGo"),
        "SEJ": ("SG", "SpiceJet"),
        "VTI": ("UK", "Vistara"),
        "AXB": ("IX", "Air India Express"),
        "UAE": ("EK", "Emirates"),
        "QTR": ("QR", "Qatar Airways"),
        "THY": ("TK", "Turkish Airlines"),
        "DLH": ("LH", "Lufthansa"),
        "BAW": ("BA", "British Airways"),
        "SIA": ("SQ", "Singapore Airlines"),
        "CPA": ("CX", "Cathay Pacific"),
        "AFR": ("AF", "Air France"),
        "KLM": ("KL", "KLM"),
        "ETD": ("EY", "Etihad Airways"),
        "VIR": ("VS", "Virgin Atlantic"),
        "JAL": ("JL", "Japan Airlines"),
        "ANA": ("NH", "All Nippon Airways"),
    }

    def __init__(self) -> None:
        self.base_url = os.getenv("ADSB_LOL_BASE", "https://api.adsb.lol/v2").strip().rstrip("/")
        self.delhi_lat = float(os.getenv("ADSB_LOL_DELHI_LAT", "28.5562"))
        self.delhi_lon = float(os.getenv("ADSB_LOL_DELHI_LON", "77.1000"))
        self.delhi_radius_nm = int(os.getenv("ADSB_LOL_DELHI_RADIUS_NM", "40"))

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.get(url, timeout=20)
        if response.status_code == 429:
            raise RuntimeError("ADSB.lol rate limit exceeded. Try again later.")
        if response.status_code >= 400:
            raise RuntimeError(f"ADSB.lol API error: {response.status_code}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("ADSB.lol returned an unexpected payload.")
        return payload

    def _extract_airline(self, raw_flight: str) -> Dict[str, str]:
        value = (raw_flight or "").strip().upper().replace(" ", "")
        if not value:
            return {"flight_iata": "", "airline_name": "Unknown"}

        # Common ADSB callsigns use 3-letter ICAO prefix + number, e.g. IGO1234.
        icao_match = re.match(r"^([A-Z]{3})(\d{1,4}[A-Z]?)$", value)
        if icao_match:
            icao, number = icao_match.groups()
            mapped = self._ICAO_TO_IATA.get(icao)
            if mapped:
                iata_code, airline_name = mapped
                return {"flight_iata": f"{iata_code}{number}", "airline_name": airline_name}

        # If already in IATA format like AI302 or 6E5119, keep it.
        iata_match = re.match(r"^([A-Z0-9]{2})(\d{1,4}[A-Z]?)$", value)
        if iata_match:
            return {"flight_iata": value, "airline_name": "Unknown"}

        return {"flight_iata": value, "airline_name": "Unknown"}

    def get_departures(self, airport_iata: str) -> List[Dict[str, Any]]:
        if (airport_iata or "").strip().upper() != "DEL":
            return []

        payload = self._get(f"point/{self.delhi_lat}/{self.delhi_lon}/{self.delhi_radius_nm}")
        aircraft = payload.get("ac") or []
        if not isinstance(aircraft, list):
            return []

        obs_time_unix = payload.get("now")
        if isinstance(obs_time_unix, (int, float)):
            # Some deployments expose milliseconds; normalize to seconds.
            ts = float(obs_time_unix)
            if ts > 10_000_000_000:
                ts = ts / 1000.0
            observed_time = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            observed_time = datetime.now(timezone.utc)

        flights: List[Dict[str, Any]] = []
        for item in aircraft:
            if not isinstance(item, dict):
                continue

            flight_raw = (item.get("flight") or "").strip().upper().replace(" ", "")
            reg = (item.get("r") or "").strip().upper().replace(" ", "")
            hex_code = (item.get("hex") or "").strip().upper()
            parsed = self._extract_airline(flight_raw)
            flight_id = parsed.get("flight_iata") or reg or hex_code
            if not flight_id:
                continue

            alt_baro = item.get("alt_baro")
            on_ground = alt_baro in ("ground", 0)
            status = "scheduled" if on_ground else "active"

            # ADSB provides live position, not airport schedule; we expose this as low-confidence data.
            scheduled = observed_time.isoformat()
            estimated = (observed_time + timedelta(minutes=25)).isoformat()

            flights.append(
                {
                    "flight": flight_id,
                    "airline_name": parsed.get("airline_name") or "Unknown",
                    "aircraft_type": item.get("t") or "",
                    "registration": reg,
                    "hex": hex_code,
                    "departure_iata": "DEL",
                    "arrival_iata": "UNK",
                    "scheduled": scheduled,
                    "estimated": estimated,
                    "status": status,
                }
            )

        return flights
