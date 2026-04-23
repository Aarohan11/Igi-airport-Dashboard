"""
Aircraft type mapping based on airline fleets and ICAO codes.
This provides common aircraft type information for Indian carriers and international airlines.
"""

# Comprehensive aircraft mapping
AIRCRAFT_DATABASE = {
    # Airbus Commercial Aircraft
    "A319": {"name": "Airbus A319", "passenger_capacity": 150, "wide_body": False},
    "A320": {"name": "Airbus A320", "passenger_capacity": 180, "wide_body": False},
    "A321": {"name": "Airbus A321", "passenger_capacity": 220, "wide_body": False},
    "A330": {"name": "Airbus A330", "passenger_capacity": 300, "wide_body": True},
    "A350": {"name": "Airbus A350", "passenger_capacity": 325, "wide_body": True},
    "A380": {"name": "Airbus A380", "passenger_capacity": 555, "wide_body": True},
    
    # Boeing Commercial Aircraft
    "B737": {"name": "Boeing 737", "passenger_capacity": 180, "wide_body": False},
    "B787": {"name": "Boeing 787 Dreamliner", "passenger_capacity": 330, "wide_body": True},
    "B777": {"name": "Boeing 777", "passenger_capacity": 350, "wide_body": True},
    "B747": {"name": "Boeing 747", "passenger_capacity": 400, "wide_body": True},
    "B767": {"name": "Boeing 767", "passenger_capacity": 285, "wide_body": True},
    
    # Other manufacturers
    "DH4": {"name": "Dash 8-400", "passenger_capacity": 78, "wide_body": False},
    "E190": {"name": "Embraer E190", "passenger_capacity": 196, "wide_body": False},
    "CRJ": {"name": "Bombardier CRJ", "passenger_capacity": 70, "wide_body": False},
}

# Airline fleet mapping - common aircraft used by carriers at IGI
AIRLINE_FLEETS = {
    "Air India": ["A320", "A321", "A330", "A350", "B787", "B777"],
    "IndiGo": ["A320", "A321"],
    "SpiceJet": ["B737", "DH4"],
    "GoAir": ["A320"],
    "Vistara": ["A320", "B787"],
    "AirAsia India": ["A320"],
    "Virgin Atlantic": ["A330", "B787", "B767"],
    "Emirates": ["B777", "A380"],
    "Qatar Airways": ["B777", "B787", "A350"],
    "Turkish Airlines": ["B777", "B787", "A350"],
    "Lufthansa": ["A320", "A330", "B787", "B747"],
    "British Airways": ["B777", "B787", "A380"],
    "Singapore Airlines": ["A380", "B777", "A350"],
    "Thai Airways": ["A380", "B777", "B787"],
    "Malaysia Airlines": ["A330", "B787", "B737"],
    "Cathay Pacific": ["A330", "A350", "B777"],
    "Japan Airlines": ["B787", "A350"],
    "ANA": ["B787", "B777"],
    "United Airlines": ["B787", "B777"],
    "American Airlines": ["B777", "A330"],
    "Delta Air Lines": ["B777", "B767"],
    "Swiss International": ["A220", "A330"],
}

def get_aircraft_info(aircraft_code: str = None, airline_name: str = None) -> dict:
    """
    Get aircraft information based on code or airline.
    
    Args:
        aircraft_code: IATA or ICAO aircraft code
        airline_name: Airline name for fleet-based lookup
    
    Returns:
        Dictionary with aircraft information
    """
    if aircraft_code and aircraft_code in AIRCRAFT_DATABASE:
        return AIRCRAFT_DATABASE[aircraft_code]
    
    # If no direct match but we have airline, suggest likely aircraft
    if airline_name and airline_name in AIRLINE_FLEETS:
        # Return a common aircraft from the airline's fleet
        common_aircraft = AIRLINE_FLEETS[airline_name][0]
        if common_aircraft in AIRCRAFT_DATABASE:
            return AIRCRAFT_DATABASE[common_aircraft]
    
    # Default return
    return {
        "name": aircraft_code or "Commercial Aircraft",
        "passenger_capacity": 180,
        "wide_body": False
    }
