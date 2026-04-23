#!/usr/bin/env python3
"""Quick test to check flight count from API."""
import requests
import sys

try:
    resp = requests.get('http://localhost:3000/api/departures', timeout=5)
    data = resp.json()
    
    total = data.get('count', 0)
    departures = data.get('departures', [])
    
    t1_flights = len(data['terminals']['1']['domestic']) + len(data['terminals']['1']['international'])
    t2_flights = len(data['terminals']['2']['domestic']) + len(data['terminals']['2']['international'])
    t3_flights = len(data['terminals']['3']['domestic']) + len(data['terminals']['3']['international'])
    
    print(f"✓ API responding with {total} total flights")
    print(f"  Filtered in window: {len(departures)} flights")
    print(f"  Terminal distribution: T1={t1_flights}, T2={t2_flights}, T3={t3_flights}")
    print(f"  Window: {data['window_start']} to {data['window_end']}")
    
    if len(departures) >= 7:
        print("\n✓ SUCCESS: All or most flights are showing!")
    elif len(departures) >= 5:
        print("\n⚠ WARNING: Partial flights showing")
    else:
        print("\n✗ PROBLEM: Only few flights showing")
        
except requests.exceptions.ConnectionError:
    print("✗ API not responding on localhost:3000")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
