from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class CongestionResult:
    estimated_passengers: int
    arrival_rate_per_min: float
    service_rate_per_min: float
    wait_time_min: float
    level: str


def _is_wide_body(aircraft_iata: str) -> bool:
    if not aircraft_iata:
        return False
    wide_prefixes = ("33", "34", "35", "38", "74", "75", "76", "77", "78", "87", "88", "90")
    return aircraft_iata.startswith(wide_prefixes)


def estimate_passengers(departures: List[Dict]) -> int:
    total = 0
    for flight in departures:
        aircraft = flight.get("aircraft") or {}
        aircraft_iata = (aircraft.get("iata") or "").strip()
        total += 300 if _is_wide_body(aircraft_iata) else 180
    return total


def _erlang_c_probability(arrival_rate: float, service_rate: float, servers: int) -> float:
    if arrival_rate <= 0 or service_rate <= 0 or servers <= 0:
        return 0.0
    utilization = arrival_rate / (servers * service_rate)
    if utilization >= 1:
        return 1.0

    sum_terms = 0.0
    for k in range(servers):
        sum_terms += (servers * utilization) ** k / _factorial(k)
    numerator = (servers * utilization) ** servers / (_factorial(servers) * (1 - utilization))
    return numerator / (sum_terms + numerator)


def _factorial(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def estimate_wait_time(arrival_rate: float, service_rate: float, servers: int) -> float:
    utilization = arrival_rate / (servers * service_rate)
    if utilization >= 1:
        return 60.0
    erlang_c = _erlang_c_probability(arrival_rate, service_rate, servers)
    wait_q = erlang_c / (servers * service_rate - arrival_rate)
    return wait_q


def classify_congestion(wait_time_min: float) -> str:
    if wait_time_min < 10:
        return "LOW"
    if wait_time_min <= 25:
        return "MEDIUM"
    return "HIGH"


def calculate_congestion(departures: List[Dict]) -> CongestionResult:
    passengers = estimate_passengers(departures)
    arrival_rate = passengers / 60.0
    service_rate = 3.0
    servers = 4
    service_rate_total = service_rate * servers
    wait_time = estimate_wait_time(arrival_rate, service_rate, servers)
    return CongestionResult(
        estimated_passengers=passengers,
        arrival_rate_per_min=round(arrival_rate, 2),
        service_rate_per_min=round(service_rate_total, 2),
        wait_time_min=round(wait_time, 2),
        level=classify_congestion(wait_time),
    )
