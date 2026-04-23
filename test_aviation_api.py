#!/usr/bin/env python
"""Test the AviationStack API client."""
import os
from dotenv import load_dotenv

load_dotenv()

from backend.api_client import AviationApiClient

try:
    print("Creating AviationApiClient...")
    client = AviationApiClient()
    print(f"API Key loaded: {'***' if client.api_key else 'MISSING'}")
    
    print("Getting departures from DEL...")
    data = client.get_departures("DEL")
    print(f"Got {len(data)} flights")
    
    if data:
        for i, f in enumerate(data[:3]):
            flight_iata = f.get("flight_iata")
            airline = f.get("airline", {}).get("name", "Unknown")
            arrival = f.get("arrival", {})
            dest_iata = arrival.get("iata", "Unknown")
            print(f"  {i+1}. {flight_iata} ({airline}) → {dest_iata}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
