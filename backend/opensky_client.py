"""
OpenSky Network API Client - Free flight tracking API with no usage limits
https://opensky-network.org/api/documentation
"""
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import time

class OpenSkyApiClient:
    """Client for OpenSky Network REST API - Free flight data"""
    
    BASE_URL = "https://opensky-network.org/api"
    
    # IGI Airport Delhi coordinates with bounding box
    # Latitude: 28.5662, Longitude: 77.1197
    DELHI_LAT_MIN = 28.4
    DELHI_LAT_MAX = 28.7
    DELHI_LON_MIN = 76.9
    DELHI_LON_MAX = 77.3
    
    # Rate limiting and caching
    _last_request_time = 0
    _request_interval = 5  # Minimum 5 seconds between OpenSky requests
    _cache: Dict[str, tuple] = {}  # Cache with (data, timestamp)
    _cache_ttl = 300  # Cache for 5 minutes
    
    # Mapping of airlines to common aircraft
    AIRLINE_MAPPING = {
        "AI": "Air India",
        "6E": "IndiGo",
        "SG": "SpiceJet",
        "G8": "GoAir",
        "UK": "Vistara",
        "I5": "AirAsia India",
        "BA": "British Airways",
        "EK": "Emirates",
        "QR": "Qatar Airways",
        "TK": "Turkish Airlines",
        "LH": "Lufthansa",
        "VS": "Virgin Atlantic",
        "SQ": "Singapore Airlines",
        "TG": "Thai Airways",
        "MH": "Malaysia Airlines",
        "CX": "Cathay Pacific",
        "JL": "Japan Airlines",
        "NH": "All Nippon Airways",
        "UA": "United Airlines",
        "AA": "American Airlines",
        "DL": "Delta Air Lines",
        "LX": "Swiss International",
    }

    # ICAO airline code to IATA prefix used in customer-facing flight numbers.
    ICAO_TO_IATA = {
        "IGO": "6E",   # IndiGo
        "AIC": "AI",   # Air India
        "VTI": "UK",   # Vistara
        "SEJ": "SG",   # SpiceJet
        "GOW": "G8",   # Go First
        "AXB": "I5",   # AirAsia India
        "UAE": "EK",   # Emirates
        "QTR": "QR",   # Qatar Airways
        "THY": "TK",   # Turkish Airlines
        "DLH": "LH",   # Lufthansa
        "BAW": "BA",   # British Airways
        "SIA": "SQ",   # Singapore Airlines
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
    
    def get_departures(self, airport_code: str = "DEL") -> List[Dict[str, Any]]:
        """
        Get flight data for Delhi airport.

        This is strict OpenSky mode: returns only real-time OpenSky data.
        If OpenSky is unavailable or returns no states, an empty list is returned.
        """
        flights = []
        cache_key = f"departures:{airport_code.upper()}"
        now_ts = time.time()

        # Reuse recent cache to avoid hitting OpenSky rate limits too often.
        cached = self._cache.get(cache_key)
        if cached and (now_ts - cached[1]) <= self._cache_ttl:
            return cached[0]

        # Honor minimum interval between OpenSky requests.
        if now_ts - self._last_request_time < self._request_interval and cached:
            return cached[0]
        
        # Try to get real-time aircraft in Delhi airspace
        try:
            print("Attempting to fetch from OpenSky real-time API...")
            url = f"{self.BASE_URL}/states/all"
            params = {
                "lamin": self.DELHI_LAT_MIN,
                "lamax": self.DELHI_LAT_MAX,
                "lomin": self.DELHI_LON_MIN,
                "lomax": self.DELHI_LON_MAX,
            }
            
            self._last_request_time = now_ts
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                print("OpenSky rate limited (429). Returning cached dataset when available.")
                if cached:
                    return cached[0]
            elif response.status_code == 200:
                data = response.json()
                if data and "states" in data and data["states"]:
                    for state in data["states"]:
                        flight = self._transform_opensky_flight(state)
                        if flight:
                            flights.append(flight)
                
                if flights:
                    print(f"Successfully fetched {len(flights)} real flights from OpenSky")
                    self._cache[cache_key] = (flights, now_ts)
                    return flights
        
        except requests.exceptions.Timeout:
            print("OpenSky request timed out. Returning empty dataset.")
            if cached:
                return cached[0]
        except Exception as e:
            print(f"OpenSky API unavailable: {e}. Returning empty dataset.")
            if cached:
                return cached[0]

        return []
    
    def _generate_simulated_flights(self) -> List[Dict[str, Any]]:
        """
        Generate realistic simulated flights with ACCURATE real-world routes.
        
        Uses actual Indian airline flight patterns for Delhi (DEL) airport.
        All flights are created with real destination airports.
        """
        import random
        
        flights = []
        now = datetime.now(timezone.utc)
        
        # REAL airline codes used in India
        domestic_airlines = ["AI", "6E", "SG", "G8", "UK", "I5"]
        international_airlines = ["BA", "EK", "QR", "TK", "LH", "VS", "SQ", "CX"]
        
        # REAL Indian domestic destinations from Delhi
        domestic_airports = [
            ("BOM", "Mumbai"),
            ("CCU", "Kolkata"),
            ("BLR", "Bangalore"),
            ("HYD", "Hyderabad"),
            ("MAA", "Chennai"),
            ("COK", "Kochi"),
            ("PNQ", "Pune"),
            ("IXC", "Chandigarh"),
            ("JAI", "Jaipur"),
            ("LKO", "Lucknow"),
            ("GOI", "Goa"),
            ("IDR", "Indore"),
        ]
        
        # REAL international destinations from Delhi
        international_airports = [
            ("LHR", "London"),
            ("CDG", "Paris"),
            ("DXB", "Dubai"),
            ("IST", "Istanbul"),
            ("BKK", "Bangkok"),
            ("SIN", "Singapore"),
            ("KUL", "Kuala Lumpur"),
            ("HND", "Tokyo"),
            ("HKG", "Hong Kong"),
            ("ICN", "Seoul"),
            ("PEK", "Beijing"),
        ]
        
        # Real airline + flight number combinations (realistic format)
        # Each airline has specific flight number ranges
        airline_flight_ranges = {
            "AI": (100, 2500),   # Air India
            "6E": (1, 2000),     # IndiGo
            "SG": (1, 600),      # SpiceJet
            "G8": (1, 500),      # GoAir
            "UK": (1, 2500),     # Vistara
            "I5": (1, 1500),     # AirAsia India
            "BA": (100, 1000),   # British Airways
            "EK": (1, 500),      # Emirates
            "QR": (600, 700),    # Qatar Airways
            "TK": (200, 500),    # Turkish
            "LH": (700, 800),    # Lufthansa
            "VS": (1, 400),      # Virgin Atlantic
            "SQ": (1, 50),       # Singapore Airlines
            "CX": (700, 800),    # Cathay Pacific
        }
        
        # Generate flights across 36 hours
        for hour_offset in range(-12, 24):
            flights_this_hour = random.randint(2, 3)
            
            for _ in range(flights_this_hour):
                minute_offset = random.randint(0, 59)
                flight_time = now + timedelta(hours=hour_offset, minutes=minute_offset)
                
                # Determine status based on time
                if hour_offset < -1:
                    status = "landed"
                elif hour_offset < 0:
                    status = random.choice(["in-flight", "landed"])
                elif hour_offset == 0 and minute_offset < 30:
                    status = random.choice(["gate-closed", "final-call"])
                elif hour_offset == 0 or hour_offset == 1:
                    status = random.choice(["check-in", "boarding", "final-call", "gate-closed"])
                else:
                    status = "scheduled"
                
                # Randomly choose domestic or international (70% domestic, 30% international)
                is_international = random.random() < 0.3
                
                if is_international:
                    airline_code = random.choice(international_airlines)
                    destination, dest_name = random.choice(international_airports)
                else:
                    airline_code = random.choice(domestic_airlines)
                    destination, dest_name = random.choice(domestic_airports)
                
                # Generate realistic flight number
                min_num, max_num = airline_flight_ranges.get(airline_code, (1, 9999))
                flight_num = random.randint(min_num, max_num)
                flight_number = f"{airline_code}{flight_num}"
                
                estimated_time = flight_time if status in ["in-flight", "landed"] else flight_time + timedelta(minutes=random.randint(-5, 15))
                
                airline_name = self.AIRLINE_MAPPING.get(airline_code, f"Airline {airline_code}")
                
                flight = {
                    "flight_number": flight_number,
                    "airline_name": airline_name,
                    "callsign": f"{airline_code}{random.randint(1000, 9999)}",
                    "icao24": f"{random.randint(0x400000, 0xFFFFFF):06X}".lower(),
                    "origin_country": "India",
                    "latitude": 28.5 + random.uniform(-0.3, 0.3),
                    "longitude": 77.1 + random.uniform(-0.3, 0.3),
                    "altitude": random.randint(0, 35000) if status in ["in-flight"] else random.randint(0, 500),
                    "velocity": random.randint(0, 900) if status in ["in-flight"] else random.randint(0, 50),
                    "on_ground": status not in ["in-flight"],
                    "category": None,
                    "timestamp": now.isoformat(),
                    "is_international": is_international,
                    
                    # Structured format for our app
                    "flight": {"iata": flight_number, "number": flight_number},
                    "airline": {"name": airline_name},
                    "departure": {
                        "iata": "DEL",
                        "airport": "Indira Gandhi International Airport",
                        "terminal": self._estimate_terminal(is_international),
                        "gate": self._estimate_gate(),
                        "scheduled": flight_time.isoformat(),
                        "estimated": estimated_time.isoformat(),
                    },
                    "arrival": {
                        "iata": destination,
                        "airport": dest_name,
                    },
                    "aircraft": {
                        "iata": self._estimate_aircraft_type(flight_number, airline_code),
                        "icao": None,
                    },
                    "flight_status": status,
                }
                
                flights.append(flight)
        
        print(f"Generated {len(flights)} realistic flights with accurate Indian airport routes")
        return flights

    
    def _transform_opensky_flight(self, state: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Transform OpenSky state vector to our flight format.
        
        OpenSky state format:
        [icao24, callsign, origin_country, time_position, last_contact,
         longitude, latitude, baro_altitude, on_ground, velocity, true_track,
         vertical_rate, sensors, geo_altitude, squawk, spi, source_type, category]
        """
        try:
            if not state or len(state) < 8:
                return None
            
            icao24 = state[0]
            callsign = (state[1] or "").strip()
            origin_country = state[2]
            latitude = state[6]
            longitude = state[5]
            altitude = state[7]
            on_ground = state[8]
            velocity = state[9]
            category = state[16] if len(state) > 16 else None
            
            # Keep only candidates plausibly near departure phase.
            if altitude and altitude > 12000:
                return None
            
            if not callsign:
                return None
            
            # Normalize callsign into a customer-facing flight number when possible.
            compact_callsign = callsign.replace(" ", "")
            icao_prefix = compact_callsign[:3].upper()
            iata_prefix = self.ICAO_TO_IATA.get(icao_prefix, compact_callsign[:2].upper())
            flight_digits = "".join(ch for ch in compact_callsign if ch.isdigit())
            flight_number = f"{iata_prefix}{flight_digits}" if flight_digits else compact_callsign[:6].upper()
            airline_name = self.AIRLINE_MAPPING.get(iata_prefix, "Unknown Airline")

            # OpenSky states do not provide route airports for this endpoint.
            destination = "UNK"
            is_international = False
            
            # Use current UTC as scheduling baseline; state timestamps can be stale.
            contact_ts = state[4] or state[3]
            current_time = datetime.now(timezone.utc)
            source_time = datetime.fromtimestamp(contact_ts, tz=timezone.utc) if contact_ts else current_time

            speed = float(velocity or 0)
            if on_ground:
                if speed >= 8:
                    flight_status = "boarding"
                    eta_minutes = 20
                else:
                    flight_status = "check-in"
                    eta_minutes = 45
            else:
                # Initial climb/departure roll in airport vicinity.
                flight_status = "final-call"
                eta_minutes = 5

            scheduled_time = current_time + timedelta(minutes=eta_minutes)
            estimated_time = scheduled_time
            
            # Guess if it's a departure or arrival based on altitude/movement
            flight = {
                "flight_number": flight_number,
                "airline_name": airline_name,
                "callsign": callsign,
                "icao24": icao24,
                "origin_country": origin_country,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "velocity": velocity,
                "on_ground": on_ground,
                "category": category,
                "timestamp": source_time.isoformat(),
                "is_international": is_international,
                
                # Structured format for our app
                "flight": {"iata": flight_number, "number": flight_number},
                "airline": {"name": airline_name},
                "departure": {
                    "iata": "DEL",
                    "airport": "Indira Gandhi International Airport",
                    "terminal": self._estimate_terminal(is_international, flight_number),
                    "gate": self._estimate_gate(flight_number),
                    "scheduled": scheduled_time.isoformat(),
                    "estimated": estimated_time.isoformat(),
                },
                "arrival": {
                    "iata": destination,
                    "airport": "Unknown",
                },
                "aircraft": {
                    "iata": self._estimate_aircraft_type(callsign, iata_prefix),
                    "icao": None,
                },
                "flight_status": flight_status,
            }
            
            return flight
        
        except Exception as e:
            print(f"Error transforming flight: {e}")
            return None
    
    def _estimate_gate(self, seed_key: str = "") -> str:
        """Deterministically estimate a gate for display stability."""
        seed = sum(ord(ch) for ch in (seed_key or "DEL"))
        terminal = (seed % 3) + 1
        gate_num = (seed % 50) + 1
        return f"{terminal}{gate_num:02d}"
    
    def _transform_route_to_flight(self, route: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform OpenSky route data to our flight format.
        Used for scheduled flights that may not currently be in airspace.
        """
        try:
            if not route or not isinstance(route, dict):
                return None
            
            callsign = route.get("callsign", "").strip()
            aircraft_type = route.get("aircraft", "")
            departure_airport = route.get("estDepartureAirport", "")
            arrival_airport = route.get("estArrivalAirport", "")
            
            if not callsign or departure_airport != "VIDP":  # Only departures from Delhi
                return None
            
            # Extract flight number
            flight_number = callsign[:6].strip()
            airline_code = flight_number[:2]
            airline_name = self.AIRLINE_MAPPING.get(airline_code, "Unknown Airline")
            
            # Determine if international
            dest_iata = arrival_airport[-3:] if len(arrival_airport) >= 3 else "XXX"
            is_international = dest_iata != "DEL"
            
            # Use real scheduled time if available
            now = datetime.now(timezone.utc)
            scheduled_time = now + timedelta(hours=random.randint(1, 24))
            estimated_time = scheduled_time + timedelta(minutes=random.randint(-15, 30))
            
            flight = {
                "flight_number": flight_number,
                "airline_name": airline_name,
                "callsign": callsign,
                "icao24": route.get("icao24", ""),
                "origin_country": "India",
                "is_international": is_international,
                "latitude": None,
                "longitude": None,
                "altitude": None,
                "velocity": None,
                "on_ground": True,
                
                # Structured format
                "flight": {"iata": flight_number, "number": flight_number},
                "airline": {"name": airline_name},
                "departure": {
                    "iata": "DEL",
                    "airport": "Indira Gandhi International Airport",
                    "terminal": self._estimate_terminal(is_international),
                    "gate": self._estimate_gate(),
                    "scheduled": scheduled_time.isoformat(),
                    "estimated": estimated_time.isoformat(),
                },
                "arrival": {
                    "iata": dest_iata,
                    "airport": "Unknown",
                },
                "aircraft": {
                    "iata": aircraft_type or self._estimate_aircraft_type(callsign, airline_code),
                    "icao": None,
                },
                "flight_status": "scheduled",
            }
            
            return flight
        except Exception as e:
            print(f"Error transforming route: {e}")
            return None
    
    def _estimate_terminal(self, is_international: bool = False, seed_key: str = "") -> Optional[str]:
        """
        Assign terminals based on flight type.
        Terminal 1: Domestic flights
        Terminal 2: Domestic and some International
        Terminal 3: International flights and wide-body aircraft
        """
        seed = sum(ord(ch) for ch in (seed_key or "DEL"))
        if is_international:
            # International flights go to terminals 2 and 3.
            return "3" if seed % 4 else "2"
        else:
            # Domestic flights go to terminals 1 and 2.
            return "1" if seed % 2 == 0 else "2"
    
    def _estimate_aircraft_type(self, callsign: str, airline_code: str) -> str:
        """Estimate aircraft type based on airline"""
        airline_fleet = {
            "AI": ["A320", "A321", "B787", "B777"],  # Air India
            "6E": ["A320", "A321"],  # IndiGo
            "SG": ["B737"],  # SpiceJet
            "G8": ["A320"],  # GoAir
            "UK": ["A320", "B787"],  # Vistara
            "BA": ["B777", "B787"],  # British Airways
            "EK": ["B777", "A380"],  # Emirates
            "QR": ["B777", "B787"],  # Qatar
            "TK": ["B777", "A350"],  # Turkish
            "LH": ["A320", "B787"],  # Lufthansa
        }
        
        aircraft_list = airline_fleet.get(airline_code, ["A320", "B737"])
        seed = sum(ord(ch) for ch in (callsign or airline_code or "A320"))
        return aircraft_list[seed % len(aircraft_list)]
    
    def get_airport_country(self, iata_code: str) -> str:
        """Get country for airport IATA code"""
        airport_countries = {
            # India - Domestic
            "BOM": "India",    # Mumbai (Bombay)
            "CCU": "India",    # Calcutta (Kolkata)
            "BLR": "India",    # Bangalore
            "HYD": "India",    # Hyderabad
            "MAA": "India",    # Chennai (Madras)
            "COK": "India",    # Kochi (Cochin)
            "DEL": "India",    # Delhi
            "PNQ": "India",    # Pune
            "IXC": "India",    # Chandigarh
            "JAI": "India",    # Jaipur
            "LKO": "India",    # Lucknow
            "VGA": "India",    # Vijaywada
            "IXM": "India",    # Madurai
            "TRV": "India",    # Trivandrum
            "CCJ": "India",    # Kozhikode
            "ISK": "India",    # Srinagar
            "IDR": "India",    # Indore
            "AGX": "India",    # Agra
            "VNS": "India",    # Varanasi
            "IXU": "India",    # Varanasi (alternate)
            # Europe
            "LHR": "United Kingdom",
            "CDG": "France",
            "AMS": "Netherlands",
            "FRA": "Germany",
            "MUC": "Germany",
            "FCO": "Italy",
            "MAD": "Spain",
            "BCN": "Spain",
            # Middle East
            "DXB": "United Arab Emirates",
            "AUH": "United Arab Emirates",
            "DXB": "United Arab Emirates",
            "IST": "Turkey",
            "JFK": "United States",
            # Asia-Pacific
            "BKK": "Thailand",
            "SIN": "Singapore",
            "KUL": "Malaysia",
            "HND": "Japan",      # Tokyo Haneda
            "NRT": "Japan",      # Tokyo Narita
            "HKG": "Hong Kong",
            "PVG": "China",      # Shanghai Pudong
            "PEK": "China",      # Beijing
            "ICN": "South Korea",
            "SEL": "South Korea",
        }
        return airport_countries.get(iata_code.upper(), "Unknown")
