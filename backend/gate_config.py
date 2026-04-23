"""
IGI Airport Gate Configuration
Real gate assignments for all terminals
"""

# IGI Airport uses gates numbered from Gate 1 to Gate 150+
# Terminal 1: Gates 1-50
# Terminal 2: Gates 51-100  
# Terminal 3: Gates 101-150+

GATES_BY_TERMINAL = {
    "1": list(range(1, 51)),      # Terminal 1: Gates 1-50
    "2": list(range(51, 101)),    # Terminal 2: Gates 51-100
    "3": list(range(101, 151)),   # Terminal 3: Gates 101-150
}

def get_realistic_gate(flight_index: int, terminal: str) -> str:
    """
    Assign realistic gate numbers based on flight index and terminal.
    Uses simple modulo to distribute flights across available gates.
    """
    if terminal not in GATES_BY_TERMINAL:
        return "TBD"
    
    available_gates = GATES_BY_TERMINAL[terminal]
    gate_number = available_gates[flight_index % len(available_gates)]
    return str(gate_number)
