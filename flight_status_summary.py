#!/usr/bin/env python3
"""Test script to display flight status summary"""
import requests

r = requests.get('http://localhost:3000/api/departures')
data = r.json()

# Count by status
statuses = {}
for flight in data['departures']:
    status = flight.get('status', 'unknown')
    if status not in statuses:
        statuses[status] = 0
    statuses[status] += 1

print('============================================')
print('FLIGHT STATUS SUMMARY')
print('============================================')
for status, count in sorted(statuses.items()):
    print(f'  • {status.upper():<15} {count} flights')

print(f'\nTotal flights in system: {len(data["departures"])}')

print('\n============================================')
print('SAMPLE FLIGHTS (by status)') 
print('============================================')
shown = set()
for flight in data['departures']:
    status = flight.get('status')
    if status not in shown and len(shown) < 7:
        shown.add(status)
        dest = flight.get('destination', 'N/A')
        terminal = flight.get('terminal', 'N/A')
        gate_str = flight.get('gate', 'TBD')
        print(f"{flight['flight_number']:8} {dest:5} {status:12} Terminal-{terminal} {gate_str}")

print('============================================\n')
