import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from reliable_api_client import ReliableFlightApiClient
from congestion_model import calculate_congestion
from aircraft_data import get_aircraft_info
from gate_config import get_realistic_gate


load_dotenv(override=True)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static"),
)

_AIRPORT_COUNTRY_CACHE: Dict[str, str] = {}

_ICAO_TO_IATA_PREFIX = {
    "IGO": "6E",
    "AIC": "AI",
    "VTI": "UK",
    "SEJ": "SG",
    "GOW": "G8",
    "AXB": "I5",
    "UAE": "EK",
    "QTR": "QR",
    "THY": "TK",
    "DLH": "LH",
    "BAW": "BA",
    "SIA": "SQ",
}

_DOMESTIC_AIRPORTS = {"BOM", "BLR", "CCU", "HYD", "MAA", "COK", "PNQ", "IXC", "LKO", "GOI", "JAI"}
_INTERNATIONAL_AIRPORTS = {"LHR", "DXB", "AUH", "DOH", "SIN", "KUL", "BKK", "IST", "CDG"}

_DOMESTIC_ROUTE_POOL = ["BOM", "BLR", "CCU", "HYD", "MAA", "COK", "PNQ", "IXC", "LKO", "GOI", "JAI"]
_INTERNATIONAL_ROUTE_POOL = ["LHR", "DXB", "AUH", "DOH", "SIN", "KUL", "BKK", "IST", "CDG"]

_DOMESTIC_AIRLINES = [("6E", "IndiGo"), ("AI", "Air India"), ("SG", "SpiceJet"), ("UK", "Vistara")]
_INTERNATIONAL_AIRLINES = [("AI", "Air India"), ("EK", "Emirates"), ("QR", "Qatar Airways"), ("SQ", "Singapore Airlines"), ("UK", "Vistara")]


def _use_mock_dashboard_data() -> bool:
    return os.getenv("MOCK_DASHBOARD_DATA", "true").strip().lower() == "true"


def _build_mock_delhi_departures() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    aircraft_by_prefix = {
        "6E": ["A320", "A321"],
        "AI": ["A320", "A321", "B787", "B777"],
        "SG": ["B737", "A320"],
        "UK": ["A320", "A321", "B787"],
        "EK": ["B777", "A380"],
        "QR": ["B787", "A359"],
        "SQ": ["A359", "B787"],
    }

    def make_flight(idx: int, terminal: str, route_type: str) -> Dict[str, Any]:
        if route_type == "domestic":
            prefix, airline = random.choice(_DOMESTIC_AIRLINES)
            destination = random.choice(_DOMESTIC_ROUTE_POOL)
        else:
            prefix, airline = random.choice(_INTERNATIONAL_AIRLINES)
            destination = random.choice(_INTERNATIONAL_ROUTE_POOL)

        flight_no = f"{prefix}{random.randint(100, 2999)}"
        aircraft = random.choice(aircraft_by_prefix.get(prefix, ["A320"]))
        offset_min = random.randint(20, 360)
        scheduled = now + timedelta(minutes=offset_min)
        if offset_min <= 30:
            status = "final-call"
        elif offset_min <= 60:
            status = "boarding"
        elif offset_min <= 120:
            status = "check-in"
        else:
            status = "scheduled"

        gate_number = {
            "1": 8 + ((idx * 3) % 18),
            "2": 26 + ((idx * 5) % 22),
            "3": 48 + ((idx * 7) % 24),
        }.get(terminal, 20)

        return {
            "flight_iata": flight_no,
            "flight_status": status,
            "status": status,
            "airline": {"name": airline},
            "departure": {
                "iata": "DEL",
                "airport": "Indira Gandhi International Airport",
                "terminal": terminal,
                "gate": f"Gate {gate_number}",
                "scheduled": scheduled.isoformat(),
                "estimated": (scheduled + timedelta(minutes=random.randint(0, 8))).isoformat(),
            },
            "arrival": {
                "iata": destination,
                "airport": "Unknown",
            },
            "aircraft": {
                "iata": aircraft,
            },
            "provider": "mock_schedule",
            "confidence": "high",
        }

    flights: List[Dict[str, Any]] = []
    idx = 0

    # T1 strict domestic only.
    for _ in range(random.randint(4, 8)):
        flights.append(make_flight(idx, "1", "domestic"))
        idx += 1

    # T2 mixed domestic + international.
    for _ in range(random.randint(2, 5)):
        flights.append(make_flight(idx, "2", "domestic"))
        idx += 1
    for _ in range(random.randint(2, 5)):
        flights.append(make_flight(idx, "2", "international"))
        idx += 1

    # T3 strict international only.
    for _ in range(random.randint(4, 8)):
        flights.append(make_flight(idx, "3", "international"))
        idx += 1

    flights.sort(key=lambda item: (item.get("departure") or {}).get("scheduled") or "")
    return flights


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _normalize_flight_number(value: str) -> str:
    compact = (value or "").strip().upper().replace(" ", "")
    if not compact:
        return ""
    if len(compact) >= 3:
        prefix3 = compact[:3]
        mapped = _ICAO_TO_IATA_PREFIX.get(prefix3)
        if mapped:
            suffix = compact[3:]
            if suffix:
                return f"{mapped}{suffix}"
    return compact


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_departure_time(flight: Dict[str, Any]) -> datetime | None:
    departure = flight.get("departure") or {}
    estimated = _parse_time(departure.get("estimated") or "")
    if estimated:
        return estimated
    return _parse_time(departure.get("scheduled") or "")


def _filter_departures_window(
    flights: List[Dict[str, Any]],
    window_minutes: int = 1440,
) -> tuple[List[Dict[str, Any]], datetime, datetime, bool]:
    """
    Filter flights showing only upcoming departures.
    Shows flights from now onwards for the next 24+ hours.
    Does NOT include departed/landed flights.
    """
    now = datetime.now(timezone.utc)
    # Show only future flights (upcoming departures)
    window_start = now
    window_end = now + timedelta(minutes=window_minutes)
    
    result: List[Dict[str, Any]] = []
    for flight in flights:
        dep_time = _get_departure_time(flight)
        if dep_time and window_start <= dep_time <= window_end:
            result.append(flight)

    if result:
        return result, window_start, window_end, False

    # If no flights found in current window, show next batch
    future_flights = [(flight, _get_departure_time(flight)) for flight in flights]
    future_flights = [item for item in future_flights if item[1] and item[1] > now]
    if not future_flights:
        return [], window_start, window_end, False

    earliest_time = min(item[1] for item in future_flights)
    fallback_start = earliest_time
    fallback_end = earliest_time + timedelta(minutes=1440)
    fallback_results = [
        flight
        for flight, dep_time in future_flights
        if dep_time and fallback_start <= dep_time <= fallback_end
    ]
    return fallback_results, fallback_start, fallback_end, True


def _get_country(client, iata_code: str) -> str:
    code = (iata_code or "").strip().upper()
    if not code:
        return ""
    if code in _AIRPORT_COUNTRY_CACHE:
        return _AIRPORT_COUNTRY_CACHE[code]
    country = client.get_airport_country(code)
    _AIRPORT_COUNTRY_CACHE[code] = country
    return country


def _infer_route_type(flight_number: str, destination_country: str) -> str:
    country = (destination_country or "").strip().lower()
    if country == "india":
        return "domestic"
    if country and country != "unknown":
        return "international"

    # For feeds without destination-country enrichment, infer a stable split.
    airline_code = (flight_number or "")[:2].upper()
    seed = sum(ord(ch) for ch in (flight_number or "UNK"))
    domestic_lean = {"6E", "SG", "I5", "G8", "IX"}
    if airline_code in domestic_lean:
        return "domestic" if seed % 10 < 7 else "international"
    return "international" if seed % 10 < 7 else "domestic"


def _infer_terminal(flight_number: str, route_type: str) -> str:
    seed = sum(ord(ch) for ch in (flight_number or "UNK"))
    if route_type == "international":
        # International flights are mostly terminal 3, some terminal 2.
        return "3" if seed % 5 else "2"
    # Domestic flights are spread between terminal 1 and 2.
    return "1" if seed % 2 == 0 else "2"


def _extract_gate_index(gate_value: str, seed_flight: str) -> int:
    digits = "".join(ch for ch in (gate_value or "") if ch.isdigit())
    if digits:
        return (int(digits) % 8) + 1
    seed = sum(ord(ch) for ch in (seed_flight or "DEL"))
    return (seed % 8) + 1


def _upcoming_delhi_departures(client: ReliableFlightApiClient) -> List[Dict[str, Any]]:
    raw = _build_mock_delhi_departures() if _use_mock_dashboard_data() else client.get_departures("DEL")
    delhi_only = []
    for flight in raw:
        departure = flight.get("departure") or {}
        origin = (departure.get("iata") or "").strip().upper()
        if not origin or origin == "DEL":
            delhi_only.append(flight)

    upcoming_statuses = {"scheduled", "boarding", "check-in", "final-call", "gate-closed"}
    status_filtered = [
        flight
        for flight in delhi_only
        if ((flight.get("flight_status") or flight.get("status") or "").strip().lower() in upcoming_statuses)
    ]

    filtered, _, _, _ = _filter_departures_window(status_filtered, window_minutes=420)
    return filtered


def _classify_gate_wait(wait_time_min: int) -> str:
    if wait_time_min <= 2:
        return "LOW"
    if wait_time_min <= 3:
        return "MEDIUM"
    return "HIGH"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/flight")
def flight_detail_page():
    return render_template("flight-detail.html")


@app.route("/api/flight")
def api_flight():
    flight_number = _normalize_flight_number(request.args.get("flight_number") or "")
    if not flight_number:
        return jsonify({"error": "Flight number is required."}), 400

    try:
        client = ReliableFlightApiClient()
        movements = client.get_movements("DEL")
        data = (movements.get("departures") or []) + (movements.get("arrivals") or [])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    # Search for flight by flight_iata
    for flight in data:
        flight_iata = _normalize_flight_number(flight.get("flight_iata") or "")
        if flight_iata == flight_number:
            departure = flight.get("departure") or {}
            arrival = flight.get("arrival") or {}
            airline = flight.get("airline") or {}

            movement = "departure" if (departure.get("iata") or "").upper() == "DEL" else "arrival"
            response = {
                "flight_number": flight.get("flight_iata") or flight_number,
                "airline": airline.get("name") or "Unknown",
                "origin": departure.get("iata") or "DEL",
                "destination": arrival.get("iata") or "Unknown",
                "movement": movement,
                "scheduled_time": departure.get("scheduled") or "Unknown",
                "estimated_time": departure.get("estimated") or "Unknown",
                "status": flight.get("flight_status") or "scheduled",
                "gate": departure.get("gate") or "Gate information not available.",
                "aircraft": flight.get("aircraft", {}).get("iata") or "Unknown",
                "provider": flight.get("provider") or "unknown",
                "confidence": flight.get("confidence") or "unknown",
            }
            return jsonify(response)
    
    return jsonify({"error": "No flight found."}), 404


@app.route("/api/departures")
def api_departures():
    try:
        client = ReliableFlightApiClient()
        data = _build_mock_delhi_departures() if _use_mock_dashboard_data() else client.get_departures("DEL")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    # Enforce DEL-only departures regardless of upstream quirks.
    delhi_only = []
    for f in data:
        departure = f.get("departure") or {}
        origin = (departure.get("iata") or "").strip().upper()
        if not origin or origin == "DEL":
            delhi_only.append(f)

    # Show only upcoming takeoffs (exclude flights already departed/landed/cancelled).
    upcoming_statuses = {"scheduled", "boarding", "check-in", "final-call", "gate-closed"}
    status_filtered = [
        f
        for f in delhi_only
        if ((f.get("flight_status") or f.get("status") or "").strip().lower() in upcoming_statuses)
    ]

    filtered, window_start, window_end, used_fallback = _filter_departures_window(
        status_filtered,
        window_minutes=420,
    )
    simplified = []
    terminal_groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "1": {"domestic": [], "international": []},
        "2": {"domestic": [], "international": []},
        "3": {"domestic": [], "international": []},
    }
    
    # Use flight index for gate assignment
    flight_index = 0
    
    for flight in filtered:
        departure = flight.get("departure") or {}
        arrival = flight.get("arrival") or {}
        flight_iata = flight.get("flight_iata") or ""
        aircraft_iata = flight.get("aircraft", {}).get("iata") or ""
        destination_iata = arrival.get("iata") or ""
        if not destination_iata or destination_iata.upper() in {"UNK", "UNKNOWN", "N/A"}:
            continue
        destination_country = client.get_airport_country(destination_iata)
        if destination_country.strip().lower() == "unknown":
            # Hide unknown route records from the board to keep display realistic.
            continue
        route_type = _infer_route_type(flight_iata, destination_country)

        terminal = str(departure.get("terminal") or "").strip()
        if terminal not in terminal_groups:
            terminal = _infer_terminal(flight_iata, route_type)

        # Terminal policy enforcement:
        # T1 strictly domestic, T3 strictly international, T2 mixed.
        if terminal == "1":
            route_type = "domestic"
        elif terminal == "3":
            route_type = "international"
        
        # Get aircraft name from database
        airline_name = (flight.get("airline") or {}).get("name") or ""
        aircraft_data = get_aircraft_info(aircraft_iata, airline_name)
        aircraft_name = aircraft_data.get("name", "Commercial Aircraft")
        
        flight_status = flight.get("flight_status") or "scheduled"
        
        # Assign realistic gate based on terminal and flight index
        raw_gate = str(departure.get("gate") or "").strip()
        if raw_gate:
            gate = raw_gate if raw_gate.lower().startswith("gate") else f"Gate {raw_gate}"
        else:
            gate = f"Gate {get_realistic_gate(flight_index, terminal)}"
        
        flight_index += 1
        
        flight_entry = {
            "flight_number": flight_iata or "Unknown",
            "airline_name": airline_name or "Unknown Airline",
            "origin": "DEL",
            "destination": arrival.get("iata") or "Unknown",
            "destination_country": destination_country or "Unknown",
            "scheduled_time": departure.get("scheduled") or "Unknown",
            "estimated_time": departure.get("estimated") or "Unknown",
            "gate": gate,
            "status": flight_status,
            "aircraft_iata": aircraft_iata,
            "aircraft_name": aircraft_name,
            "terminal": terminal,
            "route_type": route_type,
            "provider": flight.get("provider") or "unknown",
            "confidence": flight.get("confidence") or "unknown",
        }
        simplified.append(flight_entry)
        terminal_groups[terminal][route_type].append(flight_entry)

    return jsonify(
        {
            "departures": simplified,
            "count": len(simplified),
            "terminals": terminal_groups,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "used_fallback": used_fallback,
        }
    )


@app.route("/api/gate-wait-times")
def api_gate_wait_times():
    try:
        client = ReliableFlightApiClient()
        departures = _upcoming_delhi_departures(client)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    congestion = calculate_congestion(departures)
    base_by_level = {
        "LOW": 2,
        "MEDIUM": 3,
        "HIGH": 5,
    }
    base_wait = base_by_level.get((congestion.level or "LOW").upper(), 2)

    terminal_gate_map = {
        "1": [f"Entry Gate {idx}" for idx in range(1, 9)],
        "2": [f"Entry Gate {idx}" for idx in range(1, 9)],
        "3": [f"Entry Gate {idx}" for idx in range(1, 20)],
    }

    terminal_loads: Dict[str, int] = {"1": 0, "2": 0, "3": 0}
    for flight in departures:
        departure = flight.get("departure") or {}
        terminal = str(departure.get("terminal") or "").strip()
        if terminal not in terminal_loads:
            destination = (flight.get("arrival") or {}).get("iata") or ""
            country = client.get_airport_country(destination)
            route_type = _infer_route_type(flight.get("flight_iata") or "", country)
            terminal = _infer_terminal(flight.get("flight_iata") or "", route_type)
        if terminal in terminal_loads:
            terminal_loads[terminal] += 1

    terminal_waits: Dict[str, Any] = {}
    all_waits: List[int] = []
    # Re-seed every 2 minutes so values stay stable within an interval,
    # then change naturally on the next interval.
    interval_seed = int(datetime.now(timezone.utc).timestamp() // 120)
    for terminal, gate_labels in terminal_gate_map.items():
        load = terminal_loads.get(terminal, 0)
        gate_entries: List[Dict[str, Any]] = []
        for idx, label in enumerate(gate_labels, start=1):
            rng = random.Random(f"{interval_seed}:{terminal}:{idx}:{load}")

            # Terminal-specific and load-specific variation so all gates are not identical.
            terminal_offset = int(terminal) - 2  # T1:-1, T2:0, T3:+1
            load_boost = min(3, int(load * 0.2))
            spread = rng.randint(-1, 2)
            peak_boost = 1 if (idx % 6 == 0 and load > 1) else 0

            wait = base_wait + terminal_offset + load_boost + spread + peak_boost
            wait = min(8, max(1, wait))
            all_waits.append(wait)
            gate_entries.append(
                {
                    "gate": label,
                    "wait_time_min": wait,
                    "level": _classify_gate_wait(wait),
                }
            )

        terminal_avg = round(sum(g["wait_time_min"] for g in gate_entries) / len(gate_entries), 1)
        terminal_waits[terminal] = {
            "label": f"Terminal {terminal}",
            "average_wait_min": terminal_avg,
            "level": "LOW" if terminal_avg <= 2 else "MEDIUM" if terminal_avg <= 3 else "HIGH",
            "gates": gate_entries,
        }

    avg_wait = round(sum(all_waits) / len(all_waits), 1) if all_waits else 0
    overall_level = "LOW" if avg_wait <= 2 else "MEDIUM" if avg_wait <= 3 else "HIGH"
    return jsonify(
        {
            "gates": [g for terminal in ("1", "2", "3") for g in terminal_waits[terminal]["gates"]],
            "terminals": terminal_waits,
            "average_wait_min": avg_wait,
            "level": overall_level,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.route("/api/arrivals")
def api_arrivals():
    try:
        client = ReliableFlightApiClient()
        data = client.get_arrivals("DEL")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    filtered = [f for f in data if f.get("status") in ["scheduled", "active", "landed", "cancelled"]]
    now = datetime.now(timezone.utc)
    window_start = now
    window_end = now + timedelta(hours=24)
    simplified = []
    airline_groups: Dict[str, List[Dict[str, Any]]] = {}

    for flight in filtered:
        departure = flight.get("departure") or {}
        arrival = flight.get("arrival") or {}
        flight_iata = flight.get("flight_iata") or ""
        aircraft_iata = flight.get("aircraft", {}).get("iata") or ""
        origin_iata = departure.get("iata") or ""
        origin_country = client.get_airport_country(origin_iata)
        route_type = "domestic" if origin_country.lower() == "india" else "international"

        airline_name = (flight.get("airline") or {}).get("name") or "Unknown"
        aircraft_data = get_aircraft_info(aircraft_iata, airline_name)
        aircraft_name = aircraft_data.get("name", "Commercial Aircraft")

        flight_status = flight.get("flight_status") or "scheduled"
        airline_groups.setdefault(airline_name, [])

        flight_entry = {
            "flight_number": flight_iata or "Unknown",
            "origin": departure.get("iata") or "Unknown",
            "origin_country": origin_country or "Unknown",
            "destination": arrival.get("iata") or "DEL",
            "scheduled_time": arrival.get("scheduled") or departure.get("scheduled") or "Unknown",
            "estimated_time": arrival.get("estimated") or departure.get("estimated") or "Unknown",
            "status": flight_status,
            "aircraft_iata": aircraft_iata,
            "aircraft_name": aircraft_name,
            "route_type": route_type,
            "airline": airline_name,
            "provider": flight.get("provider") or "unknown",
            "confidence": flight.get("confidence") or "unknown",
        }
        simplified.append(flight_entry)
        airline_groups[airline_name].append(flight_entry)

    return jsonify(
        {
            "arrivals": simplified,
            "count": len(simplified),
            "airlines": airline_groups,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "used_fallback": False,
        }
    )


@app.route("/api/movements")
def api_movements():
    try:
        client = ReliableFlightApiClient()
        movements = client.get_movements("DEL")
        departures = movements.get("departures") or []
        arrivals = movements.get("arrivals") or []
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    all_airlines = sorted(
        {
            ((f.get("airline") or {}).get("name") or "Unknown")
            for f in departures + arrivals
        }
    )
    international_airlines = sorted(
        {
            ((f.get("airline") or {}).get("name") or "Unknown")
            for f in departures + arrivals
            if client.get_airport_country((f.get("arrival") or {}).get("iata") or "") not in ("", "India")
            or client.get_airport_country((f.get("departure") or {}).get("iata") or "") not in ("", "India")
        }
    )

    return jsonify(
        {
            "departures_count": len(departures),
            "arrivals_count": len(arrivals),
            "total_count": len(departures) + len(arrivals),
            "airlines": all_airlines,
            "international_airlines": international_airlines,
            "departures": departures,
            "arrivals": arrivals,
        }
    )


@app.route("/api/congestion")
def api_congestion():
    try:
        client = ReliableFlightApiClient()
        data = client.get_departures("DEL")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    filtered = [f for f in data if f.get("status") in ["scheduled", "active"]]
    result = calculate_congestion(filtered)
    now = datetime.now(timezone.utc)
    window_start = now
    window_end = now + timedelta(hours=1)

    return jsonify(
        {
            "estimated_passengers": result.estimated_passengers,
            "arrival_rate_per_min": result.arrival_rate_per_min,
            "service_rate_per_min": result.service_rate_per_min,
            "wait_time_min": result.wait_time_min,
            "level": result.level,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "used_fallback": False,
        }
    )


@app.route("/api/amenities")
def api_amenities():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    food = _load_json(os.path.join(data_dir, "food.json"))
    lounges = _load_json(os.path.join(data_dir, "lounges.json"))
    return jsonify({"food": food, "lounges": lounges})


@app.route("/api/flight-detail")
def api_flight_detail():
    flight_number = _normalize_flight_number(request.args.get("flight_number") or "")
    if not flight_number:
        return jsonify({"error": "Flight number is required."}), 400

    try:
        client = ReliableFlightApiClient()
        movements = client.get_movements("DEL")
        all_flights = (movements.get("departures") or []) + (movements.get("arrivals") or [])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    flight_match = None
    for f in all_flights:
        flight_iata = _normalize_flight_number(f.get("flight_iata", ""))
        if flight_iata.upper() == flight_number:
            flight_match = f
            break

    if not flight_match:
        return jsonify({"error": "Flight not found."}), 404

    departure = flight_match.get("departure") or {}
    arrival = flight_match.get("arrival") or {}
    airline = flight_match.get("airline") or {}
    aircraft_info = flight_match.get("aircraft") or {}
    
    route_seed = flight_match.get("flight_iata") or flight_number
    destination_iata = arrival.get("iata") or ""
    destination_country = client.get_airport_country(destination_iata)
    route_type = _infer_route_type(route_seed, destination_country)
    terminal = str(departure.get("terminal") or "").strip()
    if terminal not in ("1", "2", "3"):
        terminal = _infer_terminal(route_seed, route_type)
    
    aircraft_iata = aircraft_info.get("iata") or ""
    
    # Get aircraft name from database
    airline_name = airline.get("name") or ""
    aircraft_data_info = get_aircraft_info(aircraft_iata, airline_name)
    aircraft_name = aircraft_data_info.get("name", "Commercial Aircraft")
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    all_food = _load_json(os.path.join(data_dir, "food.json"))
    all_lounges = _load_json(os.path.join(data_dir, "lounges.json"))
    
    terminal_label = f"Terminal {terminal}"
    terminal_food = [item for item in all_food if item.get("terminal") == terminal_label]
    terminal_lounges = [item for item in all_lounges if item.get("terminal") == terminal_label]
    
    filtered_flights = [f for f in all_flights if f.get("status") in ["scheduled", "active"]]
    congestion_data = calculate_congestion(filtered_flights)
    
    # Find flight index for gate assignment
    flight_index = 0
    for idx, f in enumerate(all_flights):
        if (f.get("flight_iata") or "").upper() == flight_number:
            flight_index = idx
            break
    
    # Assign realistic gate
    raw_gate = str(departure.get("gate") or "").strip()
    if raw_gate:
        gate = raw_gate if raw_gate.lower().startswith("gate") else f"Gate {raw_gate}"
    else:
        gate = f"Gate {get_realistic_gate(flight_index, terminal)}"
    
    response = {
        "flight_number": flight_match.get("flight_iata") or flight_number,
        "airline": airline.get("name") or "Unknown",
        "aircraft": aircraft_name,
        "aircraft_iata": aircraft_iata,
        "origin": departure.get("iata") or "Unknown",
        "destination": arrival.get("iata") or "Unknown",
        "destination_country": destination_country or "Unknown",
        "route_type": route_type,
        "scheduled_time": departure.get("scheduled") or "Unknown",
        "estimated_time": departure.get("estimated") or "Unknown",
        "status": flight_match.get("flight_status") or "scheduled",
        "gate": gate,
        "terminal": terminal,
        "terminal_food": terminal_food,
        "terminal_lounges": terminal_lounges,
        "congestion_level": congestion_data.level,
        "congestion_wait_time": congestion_data.wait_time_min,
        "provider": flight_match.get("provider") or "unknown",
        "confidence": flight_match.get("confidence") or "unknown",
    }

    return jsonify(response)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=True)
