#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from opensky_client import OpenSkyApiClient
from datetime import datetime, timezone, timedelta

print("Testing OpenSky Client...")
client = OpenSkyApiClient()
flights = client.get_departures('DEL')
print(f"✓ Total flights from API: {len(flights)}")

if flights:
    f = flights[0]
    print(f"\nSample flight:")
    print(f"  Flight: {f.get('flight_number')}")
    print(f"  Gate: {f.get('departure', {}).get('gate')}")
    print(f"  Status: {f.get('flight_status')}")
    print(f"  Terminal: {f.get('departure', {}).get('terminal')}")
    print(f"  Scheduled: {f.get('departure', {}).get('scheduled')}")

print("\nTesting time window filter (7 hours)...")
now = datetime.now(timezone.utc)
window_start = now
window_end = now + timedelta(minutes=420)
filtered = [f for f in flights if (
    f.get('departure', {}).get('scheduled') and 
    window_start <= datetime.fromisoformat(f.get('departure', {}).get('scheduled').replace('Z', '+00:00')) <= window_end
)]
print(f"Flights in 7-hour window: {len(filtered)}")
print(f"Window: {window_start.strftime('%H:%M')} to {window_end.strftime('%H:%M')}")

if filtered:
    print(f"\nSample filtered flights:")
    for f in filtered[:3]:
        print(f"  {f.get('flight_number')} | Gate: {f.get('departure', {}).get('gate')} | Status: {f.get('flight_status')} | Terminal: {f.get('departure', {}).get('terminal')}")
