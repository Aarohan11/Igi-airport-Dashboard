// Homepage Script - Fetches data and displays stats and search functionality

let allFlights = [];
let searchableFlights = [];

function normalizeFlightNumber(value) {
    return String(value || '').trim().toUpperCase().replace(/\s+/g, '');
}

function simplifyMovementFlight(flight) {
    const departure = flight.departure || {};
    const arrival = flight.arrival || {};
    const airlineObj = flight.airline || {};
    const aircraftObj = flight.aircraft || {};

    const origin = departure.iata || 'DEL';
    const destination = arrival.iata || 'Unknown';

    const domesticAirports = new Set(['DEL', 'BOM', 'BLR', 'CCU', 'HYD', 'MAA', 'COK', 'PNQ', 'IXC', 'LKO', 'GOI', 'JAI']);
    const route_type = domesticAirports.has(origin) && domesticAirports.has(destination) ? 'domestic' : 'international';

    const rawGate = String(departure.gate || '').trim();
    const gate = rawGate ? (rawGate.toLowerCase().startsWith('gate') ? rawGate : `Gate ${rawGate}`) : 'TBD';

    return {
        flight_number: flight.flight_iata || flight.flight_number || 'Unknown',
        airline_name: airlineObj.name || 'Unknown Airline',
        airline: airlineObj.name || 'Unknown Airline',
        aircraft_iata: aircraftObj.iata || 'Unknown',
        aircraft_name: aircraftObj.iata || 'Unknown',
        origin,
        destination,
        route_type,
        terminal: String(departure.terminal || 'unknown'),
        gate,
        status: flight.flight_status || flight.status || 'scheduled',
        scheduled_time: departure.scheduled || arrival.scheduled || null,
        estimated_time: departure.estimated || arrival.estimated || departure.scheduled || arrival.scheduled || null,
    };
}

// Fetch and display initial data
async function initializeHomepage() {
    try {
        await fetchFlightData();
        updateHomeStats();
        setupFlightSearch();
        updateClock();
        setInterval(updateClock, 1000);
        updateFooterTime();
        setInterval(updateFooterTime, 60000); // Update footer time every minute
    } catch (error) {
        console.error('Error initializing homepage:', error);
    }
}

function updateClock() {
    const now = new Date();
    const timeEl = document.getElementById('current-time');
    const dateEl = document.getElementById('current-date');

    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
            timeZone: 'Asia/Kolkata'
        });
    }

    if (dateEl) {
        dateEl.textContent = now.toLocaleDateString('en-IN', {
            weekday: 'short',
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            timeZone: 'Asia/Kolkata'
        });
    }
}

// Fetch flight data from API
async function fetchFlightData() {
    try {
        const [departuresResponse, movementsResponse] = await Promise.all([
            fetch('/api/departures'),
            fetch('/api/movements'),
        ]);

        const departuresData = departuresResponse.ok ? await departuresResponse.json() : { departures: [] };
        const movementsData = movementsResponse.ok ? await movementsResponse.json() : { departures: [], arrivals: [] };

        allFlights = departuresData.departures || [];

        const movementFlights = [
            ...(movementsData.departures || []),
            ...(movementsData.arrivals || []),
        ].map(simplifyMovementFlight);

        const dedup = new Map();
        [...allFlights, ...movementFlights].forEach((flight) => {
            const key = normalizeFlightNumber(flight.flight_number);
            if (key) {
                dedup.set(key, flight);
            }
        });
        searchableFlights = Array.from(dedup.values());
    } catch (error) {
        console.error('Error fetching flight data:', error);
        searchableFlights = allFlights;
    }
}

// Update homepage statistics
function updateHomeStats() {
    if (!allFlights || allFlights.length === 0) {
        document.getElementById('hero-flights').textContent = '0';
        document.getElementById('hero-passengers').textContent = '0';
        document.getElementById('hero-congestion').textContent = 'N/A';
        document.getElementById('t1-count').textContent = '0 flights';
        document.getElementById('t2-count').textContent = '0 flights';
        document.getElementById('t3-count').textContent = '0 flights';
        return;
    }

    // Count total flights
    const totalFlights = allFlights.length;
    document.getElementById('hero-flights').textContent = totalFlights;

    // Calculate estimated passengers (use a reasonable default per aircraft)
    const aircraftCapacities = {
        'A320': 180,
        'A321': 220,
        'B737': 189,
        'B777': 350,
        'B787': 242,
        'A380': 555
    };
    
    const totalPassengers = allFlights.reduce((sum, flight) => {
        // Extract aircraft type from aircraft_iata (e.g., "A320", "B777")
        const aircraftType = flight.aircraft_iata || 'A320';
        const capacity = aircraftCapacities[aircraftType] || 200;
        return sum + (Math.round(capacity * (0.75 + Math.random() * 0.2))); // 75-95% occupancy
    }, 0);
    document.getElementById('hero-passengers').textContent = String(Math.round(totalPassengers / 1000)) + 'K';

    // Calculate congestion level (simple: flights per hour / capacity)
    const congestionLevel = totalFlights / 30; // 30 flights per hour is normal capacity
    const congestionText = congestionLevel > 0.8 ? 'High ⚠️' : congestionLevel > 0.5 ? 'Medium ⚡' : 'Low ✓';
    document.getElementById('hero-congestion').textContent = congestionText;

    // Count flights by terminal
    const t1Flights = allFlights.filter(f => String(f.terminal) === '1').length;
    const t2Flights = allFlights.filter(f => String(f.terminal) === '2').length;
    const t3Flights = allFlights.filter(f => String(f.terminal) === '3').length;
    const unknownFlights = allFlights.filter(f => !['1', '2', '3'].includes(String(f.terminal))).length;

    document.getElementById('t1-count').textContent = t1Flights + ' flights';
    document.getElementById('t2-count').textContent = t2Flights + ' flights';
    document.getElementById('t3-count').textContent = unknownFlights > 0
        ? `${t3Flights} flights (+${unknownFlights} TBD)`
        : `${t3Flights} flights`;
    
    // Display available flights for quick search
    updateAvailableFlights();
}

// Display available flights for quick search
function updateAvailableFlights() {
    const flightsList = document.getElementById('flights-list');
    const availableFlightsDiv = document.getElementById('available-flights');
    
    if (!searchableFlights || searchableFlights.length === 0) {
        availableFlightsDiv.style.display = 'none';
        return;
    }
    
    // Show a broad searchable set while keeping UI manageable.
    const uniqueFlights = [...new Set(searchableFlights.map(f => f.flight_number).filter(Boolean))].sort();
    const visibleFlights = uniqueFlights.slice(0, 80);
    const remaining = Math.max(0, uniqueFlights.length - visibleFlights.length);
    
    flightsList.innerHTML = visibleFlights.map(flight => `
        <button
            type="button"
            class="flight-chip"
            onclick="quickSearchFlight('${flight}')"
        >${flight}</button>
    `).join('') + (remaining > 0 ? `<span class="flight-chip" style="cursor:default;opacity:.8;">+${remaining} more searchable</span>` : '');
    
    availableFlightsDiv.style.display = 'block';
}

// Quick search by clicking on available flights
function quickSearchFlight(flightNumber) {
    document.getElementById('flight-number').value = flightNumber;
    document.getElementById('flight-form').dispatchEvent(new Event('submit'));
    // Scroll to results
    setTimeout(() => {
        document.getElementById('flight-result').scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

// Setup flight search functionality
function setupFlightSearch() {
    const form = document.getElementById('flight-form');
    form.addEventListener('submit', handleFlightSearch);
}

// Handle flight search
async function handleFlightSearch(e) {
    e.preventDefault();
    
    const flightNumber = normalizeFlightNumber(document.getElementById('flight-number').value);
    const resultDiv = document.getElementById('flight-result');
    const errorDiv = document.getElementById('flight-error');
    
    errorDiv.textContent = '';
    resultDiv.innerHTML = '';
    
    if (!flightNumber) {
        errorDiv.textContent = 'Please enter a flight number';
        return;
    }

    try {
        // Search for flight in the broader local index first.
        const flight = searchableFlights.find(
            f => normalizeFlightNumber(f.flight_number) === flightNumber
        );
        
        if (flight) {
            displayFlightResult(flight, resultDiv);
            return;
        }

        // Try detailed endpoint first.
        let response = await fetch(`/api/flight-detail?flight_number=${encodeURIComponent(flightNumber)}`);
        if (response.ok) {
            const data = await response.json();
            displayFlightResult(data, resultDiv);
            return;
        }

        // Fallback endpoint for broader provider responses.
        response = await fetch(`/api/flight?flight_number=${encodeURIComponent(flightNumber)}`);
        if (response.ok) {
            const data = await response.json();
            displayFlightResult(data, resultDiv);
            return;
        }

        const suggestions = searchableFlights
            .map(f => f.flight_number)
            .filter(Boolean)
            .slice(0, 40)
            .join(', ');
        errorDiv.innerHTML = `
            <div class="search-empty">
                <strong>Flight "${flightNumber}" not found.</strong><br/>
                <small>Try one of these: ${suggestions || 'No flights available right now'}</small>
            </div>
        `;
    } catch (error) {
        errorDiv.textContent = 'Error searching for flight: ' + error.message;
    }
}

// Display flight search result
function displayFlightResult(flight, resultDiv) {
    if (!flight) {
        resultDiv.innerHTML = '<p class="search-empty">No flight data available</p>';
        return;
    }

    const status = flight.status || 'Scheduled';
    const statusClass = status.toLowerCase().replaceAll(' ', '').replaceAll('-', '');
    const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
    
    const html = `
        <div class="search-grid">
            <div>
                <h3 class="search-title">Flight Information</h3>
                <div class="amenity-list">
                    <div>
                        <div class="search-label">Flight Number</div>
                        <div class="search-value big">${flight.flight_number || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="search-label">Aircraft Type</div>
                        <div class="search-value">${flight.aircraft_name || flight.aircraft || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="search-label">Route Type</div>
                        <div class="search-value">${flight.route_type ? (flight.route_type === 'domestic' ? 'Domestic' : 'International') : 'N/A'}</div>
                    </div>
                    <div>
                        <div class="search-label">Status</div>
                        <div class="flight-status-badge status-${statusClass}">${statusLabel}</div>
                    </div>
                </div>
            </div>
            <div>
                <h3 class="search-title">Terminal and Gate</h3>
                <div class="amenity-list">
                    <div>
                        <div class="search-label">Terminal</div>
                        <div class="search-value big">${flight.terminal === 'unknown' ? 'TBD' : ('Terminal ' + flight.terminal) || 'TBD'}</div>
                    </div>
                    <div>
                        <div class="search-label">Gate</div>
                        <div class="search-value">${flight.gate || 'TBD'}</div>
                    </div>
                    <div>
                        <div class="search-label">Route</div>
                        <div class="search-value">${flight.origin || 'DEL'} → ${flight.destination || 'Unknown'}</div>
                    </div>
                    <div>
                        <div class="search-label">Departure Time</div>
                        <div class="search-value">${formatTime(flight.estimated_time || flight.scheduled_time)}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    resultDiv.innerHTML = html;
}

// Format time to readable format
function formatTime(isoTime) {
    if (!isoTime) return 'N/A';
    try {
        const date = new Date(isoTime);
        return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' });
    } catch {
        return isoTime;
    }
}

// Update footer time
function updateFooterTime() {
    const now = new Date();
    const istTime = now.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' });
    const topFooterTime = document.getElementById('footer-time');
    const bottomFooterTime = document.getElementById('footer-time-copy');
    if (topFooterTime) {
        topFooterTime.textContent = istTime;
    }
    if (bottomFooterTime) {
        bottomFooterTime.textContent = istTime;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeHomepage);

// Refresh data every 30 seconds
setInterval(async () => {
    await fetchFlightData();
    updateHomeStats();
}, 30000);
