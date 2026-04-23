#!/usr/bin/env python3
"""Analyze API response for flight coverage."""
import requests
from datetime import datetime

r = requests.get('http://localhost:3000/api/departures')
data = r.json()

print('API RESPONSE SUMMARY')
print('='*60)
print(f'Total flights: {len(data["departures"])}')
print(f'Window start: {data["window_start"]}')
print(f'Window end: {data["window_end"]}')
print()

# Parse window times
window_start = datetime.fromisoformat(data['window_start'].replace('Z', '+00:00'))
window_end = datetime.fromisoformat(data['window_end'].replace('Z', '+00:00'))
window_duration = (window_end - window_start).total_seconds() / 3600
print(f'Window duration: {window_duration:.1f} hours')
print()

# Check flight time distribution
statuses = {}
earliest = None
latest = None

for f in data['departures']:
    status = f.get('status', 'unknown')
    statuses[status] = statuses.get(status, 0) + 1
    
    sched_time = datetime.fromisoformat(f['scheduled_time'].replace('Z', '+00:00'))
    if not earliest or sched_time < earliest:
        earliest = sched_time
    if not latest or sched_time > latest:
        latest = sched_time

print('Flights by Status:')
for status in sorted(statuses.keys()):
    print(f'  {status}: {statuses[status]}')

if earliest and latest:
    print()
    print(f'Earliest flight: {earliest.strftime("%H:%M")}')
    print(f'Latest flight: {latest.strftime("%H:%M")}')
    span = (latest - earliest).total_seconds() / 3600
    print(f'Flight span: {span:.1f} hours')

print()
print('SAMPLE FLIGHTS:')
print('-'*60)
for i, f in enumerate(data['departures'][:8]):
    sched = datetime.fromisoformat(f['scheduled_time'].replace('Z', '+00:00'))
    print(f"{f['flight_number']:8} {f['destination']:5} {f['status']:12} {sched.strftime('%H:%M UTC')}")
