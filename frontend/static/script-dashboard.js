function updateClock() {
    const now = new Date();
    const timeEl = document.getElementById("current-time");
    const dateEl = document.getElementById("current-date");
    const updateEl = document.getElementById("last-update");

    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
            timeZone: "Asia/Kolkata"
        }) + " IST";
    }

    if (dateEl) {
        dateEl.textContent = now.toLocaleDateString("en-IN", {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric",
            timeZone: "Asia/Kolkata"
        });
    }

    if (updateEl) {
        updateEl.textContent = now.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
            timeZone: "Asia/Kolkata"
        });
    }
}

function parseDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return null;
    }
    return date;
}

function normalizeFlightNumber(value) {
    return String(value || "").trim().toUpperCase().replace(/\s+/g, "");
}

function toShortTime(value) {
    const date = parseDate(value);
    if (!date) {
        return "--:--";
    }
    return date.toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Kolkata"
    });
}

function normalizeStatus(flight) {
    const raw = String(flight.status || "scheduled").toLowerCase();
    if (raw.includes("final")) return "FINAL CALL";
    if (raw.includes("board")) return "BOARDING";
    if (raw.includes("check")) return "CHECK-IN";
    if (raw.includes("gate")) return "GATE CLOSING";
    if (raw.includes("delay")) return "DELAYED";
    if (raw.includes("cancel")) return "CANCELLED";
    if (raw.includes("land")) return "LANDED";
    if (raw.includes("active")) return "ON TIME";
    return "SCHEDULED";
}

function statusClass(status) {
    if (status === "CANCELLED") return "is-cancelled";
    if (status === "DELAYED") return "is-delayed";
    if (status === "BOARDING" || status === "FINAL CALL" || status === "GATE CLOSING") return "is-boarding";
    if (status === "ON TIME" || status === "SCHEDULED" || status === "CHECK-IN") return "is-ontime";
    return "is-neutral";
}

function airlineLabel(flight) {
    if (flight.airline_name && flight.airline_name !== "Unknown" && flight.airline_name !== "Unknown Airline") {
        return flight.airline_name;
    }
    if (flight.airline && flight.airline !== "Unknown" && flight.airline !== "Unknown Airline") {
        return flight.airline;
    }
    const code = String(flight.flight_number || "").slice(0, 2).toUpperCase();
    const map = {
        "6E": "IndiGo",
        "AI": "Air India",
        "UK": "Vistara",
        "SG": "SpiceJet",
        "I5": "AirAsia",
        "EK": "Emirates",
        "QR": "Qatar Airways",
        "SQ": "Singapore Airlines",
        "LH": "Lufthansa",
        "BA": "British Airways"
    };
    return map[code] || "Unknown";
}

// Store all flights for modal access
let allDepartures = [];

function flightRow(flight) {
    const status = normalizeStatus(flight);
    const fromVia = `${flight.origin || "DEL"}/${flight.destination || "UNK"}`;
    const flightNumber = flight.flight_number || "---";
    return `
        <tr class="flight-row-clickable" onclick="openFlightModal('${flightNumber}')" style="cursor: pointer;">
            <td>${toShortTime(flight.scheduled_time)}</td>
            <td>${toShortTime(flight.estimated_time || flight.scheduled_time)}</td>
            <td class="cell-airline">${airlineLabel(flight)}</td>
            <td>
                <span class="flight-link">${flightNumber}</span>
            </td>
            <td>${fromVia}</td>
            <td>${flight.gate || "TBD"}</td>
            <td><span class="status-pill ${statusClass(status)}">${status}</span></td>
        </tr>
    `;
}

function renderBoardRows(targetId, flights) {
    const body = document.getElementById(targetId);
    if (!body) {
        return;
    }

    if (!flights.length) {
        body.innerHTML = `
            <tr>
                <td colspan="7" class="empty-row">No live departures in this display window</td>
            </tr>
        `;
        return;
    }

    body.innerHTML = flights.map(flightRow).join("");
}

function updateTerminalCounts(terminals) {
    const t1 = ((terminals["1"] || {}).domestic || []).length + ((terminals["1"] || {}).international || []).length;
    const t2 = ((terminals["2"] || {}).domestic || []).length + ((terminals["2"] || {}).international || []).length;
    const t3 = ((terminals["3"] || {}).domestic || []).length + ((terminals["3"] || {}).international || []).length;

    const t1El = document.getElementById("t1-count");
    const t2El = document.getElementById("t2-count");
    const t3El = document.getElementById("t3-count");

    if (t1El) t1El.textContent = String(t1);
    if (t2El) t2El.textContent = String(t2);
    if (t3El) t3El.textContent = String(t3);
}

function gateLevelClass(level) {
    const normalized = String(level || "").toUpperCase();
    if (normalized === "HIGH") return "is-high";
    if (normalized === "MEDIUM") return "is-medium";
    if (normalized === "LOW") return "is-low";
    return "is-neutral";
}

let activeGateTerminal = "1";

async function loadGateWaitTimes() {
    const grid = document.getElementById("gate-wait-grid");
    const levelEl = document.getElementById("gate-congestion-level");
    if (!grid || !levelEl) {
        return;
    }

    try {
        const response = await fetch("/api/gate-wait-times");
        if (!response.ok) {
            grid.innerHTML = "<div class='gate-empty'>Gate timing data unavailable</div>";
            levelEl.textContent = "--";
            levelEl.className = "gate-level-pill";
            return;
        }

        const data = await response.json();
        const terminals = data.terminals || {};
        const terminalIds = ["1", "2", "3"];
        const hasTerminalData = terminalIds.some((id) => (terminals[id] && (terminals[id].gates || []).length));

        if (!hasTerminalData) {
            grid.innerHTML = "<div class='gate-empty'>No gate timing data in this window</div>";
            levelEl.textContent = "LOW";
            levelEl.className = "gate-level-pill is-low";
            return;
        }

        if (!terminals[activeGateTerminal]) {
            activeGateTerminal = terminalIds.find((id) => terminals[id]) || "1";
        }

        const activeData = terminals[activeGateTerminal] || { label: `Terminal ${activeGateTerminal}`, level: "LOW", average_wait_min: 0, gates: [] };
        const activeGates = activeData.gates || [];
        const gateHtml = activeGates.map((item) => `
            <div class="gate-box ${gateLevelClass(item.level)}">
                <div class="gate-name">${item.gate}</div>
                <div class="gate-wait">${item.wait_time_min} min</div>
            </div>
        `).join("");

        const tabsHtml = terminalIds.map((id) => {
            const terminalData = terminals[id] || { label: `Terminal ${id}`, level: "LOW", average_wait_min: 0 };
            const selected = id === activeGateTerminal ? "is-selected" : "";
            return `
                <button class="terminal-tab ${selected}" data-terminal-id="${id}" type="button">
                    ${terminalData.label}
                    <span class="terminal-tab-meta ${gateLevelClass(terminalData.level)}">${terminalData.level} (${terminalData.average_wait_min}m)</span>
                </button>
            `;
        }).join("");

        grid.innerHTML = `
            <div class="terminal-tabs">${tabsHtml}</div>
            <div class="terminal-gate-group">
                <div class="terminal-gate-head">
                    <span class="terminal-gate-title">${activeData.label} Security Entry Gates</span>
                    <span class="terminal-gate-level ${gateLevelClass(activeData.level)}">${activeData.level} (${activeData.average_wait_min}m)</span>
                </div>
                <div class="terminal-gate-grid">
                    ${gateHtml || "<div class='gate-empty'>No gates available</div>"}
                </div>
            </div>
        `;

        grid.querySelectorAll(".terminal-tab").forEach((button) => {
            button.addEventListener("click", () => {
                const terminalId = button.getAttribute("data-terminal-id") || "1";
                if (terminalId !== activeGateTerminal) {
                    activeGateTerminal = terminalId;
                    loadGateWaitTimes();
                }
            });
        });

        const level = String(data.level || "LOW").toUpperCase();
        levelEl.textContent = `${level} (${data.average_wait_min || 0}m avg)`;
        levelEl.className = `gate-level-pill ${gateLevelClass(level)}`;
    } catch (error) {
        console.error("Error loading gate wait times:", error);
        grid.innerHTML = "<div class='gate-empty'>Gate timing data unavailable</div>";
        levelEl.textContent = "--";
        levelEl.className = "gate-level-pill";
    }
}

async function loadDepartures() {
    const t1Id = "board-t1-body";
    const t2Id = "board-t2-body";
    const t3Id = "board-t3-body";

    try {
        const response = await fetch("/api/departures");
        if (!response.ok) {
            renderBoardRows(t1Id, []);
            renderBoardRows(t2Id, []);
            renderBoardRows(t3Id, []);
            return;
        }

        const data = await response.json();
        const flights = (data.departures || []).slice().sort((a, b) => {
            const at = parseDate(a.scheduled_time);
            const bt = parseDate(b.scheduled_time);
            if (!at && !bt) return 0;
            if (!at) return 1;
            if (!bt) return -1;
            return at.getTime() - bt.getTime();
        });
        allDepartures = flights;

        const terminals = data.terminals || {};
        const sortByTime = (list) => list.slice().sort((a, b) => {
            const at = parseDate(a.scheduled_time);
            const bt = parseDate(b.scheduled_time);
            if (!at && !bt) return 0;
            if (!at) return 1;
            if (!bt) return -1;
            return at.getTime() - bt.getTime();
        });

        const t1Flights = sortByTime([
            ...((terminals["1"] || {}).domestic || []),
            ...((terminals["1"] || {}).international || []),
        ]);
        const t2Flights = sortByTime([
            ...((terminals["2"] || {}).domestic || []),
            ...((terminals["2"] || {}).international || []),
        ]);
        const t3Flights = sortByTime([
            ...((terminals["3"] || {}).domestic || []),
            ...((terminals["3"] || {}).international || []),
        ]);

        const departureCount = document.getElementById("departure-count");
        if (departureCount) {
            departureCount.textContent = String(flights.length);
        }

        const windowNote = document.getElementById("window-note");
        if (windowNote) {
            const start = toShortTime(data.window_start);
            const end = toShortTime(data.window_end);
            windowNote.textContent = `${start} - ${end} IST`;
        }

        renderBoardRows(t1Id, t1Flights);
        renderBoardRows(t2Id, t2Flights);
        renderBoardRows(t3Id, t3Flights);

        updateTerminalCounts(terminals);
    } catch (error) {
        console.error("Error loading departures:", error);
        allDepartures = [];
        renderBoardRows(t1Id, []);
        renderBoardRows(t2Id, []);
        renderBoardRows(t3Id, []);
    }
}

updateClock();
setInterval(updateClock, 1000);

// Flight Detail Modal Functions
async function openFlightModal(flightNumber) {
    const modal = document.getElementById('flight-detail-modal');
    const modalContent = document.getElementById('flight-detail-content');
    const modalTitle = document.getElementById('modal-flight-number');
    
    if (!modal) return;
    
    modalTitle.textContent = flightNumber;
    modalContent.innerHTML = '<div class="loading">Loading flight details...</div>';
    modal.classList.remove('hide');

    const normalizedTarget = normalizeFlightNumber(flightNumber);
    const flight = allDepartures.find((f) => normalizeFlightNumber(f.flight_number) === normalizedTarget);

    if (flight) {
        displayFlightDetails(flight);
        return;
    }

    try {
        const response = await fetch(`/api/flight-detail?flight_number=${encodeURIComponent(flightNumber)}`);
        if (!response.ok) {
            modalContent.innerHTML = '<div class="error">Flight details not available</div>';
            return;
        }
        const apiFlight = await response.json();
        displayFlightDetails(apiFlight);
    } catch (error) {
        console.error("Error loading flight details:", error);
        modalContent.innerHTML = '<div class="error">Flight details not available</div>';
    }
}

function closeFlightModal() {
    const modal = document.getElementById('flight-detail-modal');
    if (modal) {
        modal.classList.add('hide');
    }
}

function displayFlightDetails(flight) {
    const modalContent = document.getElementById('flight-detail-content');
    
    const html = `
        <div class="detail-section">
            <div class="detail-row">
                <span class="detail-label">Airline</span>
                <span class="detail-value">${airlineLabel(flight)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Aircraft</span>
                <span class="detail-value">${flight.aircraft_name || flight.aircraft_iata || 'Unknown'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Route Type</span>
                <span class="detail-value">${flight.route_type === 'domestic' ? 'Domestic' : 'International'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Route</span>
                <span class="detail-value">${flight.origin || 'DEL'} → ${flight.destination || 'Unknown'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Terminal</span>
                <span class="detail-value">${flight.terminal === 'unknown' ? 'TBD' : 'Terminal ' + flight.terminal}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Gate</span>
                <span class="detail-value">${flight.gate || 'TBD'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Scheduled Time</span>
                <span class="detail-value">${formatDetailTime(flight.scheduled_time)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Estimated Time</span>
                <span class="detail-value">${formatDetailTime(flight.estimated_time || flight.scheduled_time)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status</span>
                <span class="detail-value">${normalizeStatus(flight)}</span>
            </div>
        </div>
        
        ${flight.terminal_food && flight.terminal_food.length > 0 ? `
        <div class="detail-section">
            <h3>Food & Beverage</h3>
            ${flight.terminal_food.map(item => `
                <div class="amenity-item">
                    <span class="amenity-name">${item.name || 'Unknown'}</span>
                    <span class="amenity-type">${item.type || ''}</span>
                </div>
            `).join('')}
        </div>
        ` : ''}
        
        ${flight.terminal_lounges && flight.terminal_lounges.length > 0 ? `
        <div class="detail-section">
            <h3>Lounges</h3>
            ${flight.terminal_lounges.map(item => `
                <div class="amenity-item">
                    <span class="amenity-name">${item.name || 'Unknown'}</span>
                    <span class="amenity-type">${item.type || ''}</span>
                </div>
            `).join('')}
        </div>
        ` : ''}
    `;
    
    modalContent.innerHTML = html;
}

function formatDetailTime(isoTime) {
    if (!isoTime) return 'N/A';
    try {
        const date = new Date(isoTime);
        return date.toLocaleString('en-IN', {
            dateStyle: 'short',
            timeStyle: 'short',
            timeZone: 'Asia/Kolkata'
        });
    } catch (e) {
        return isoTime;
    }
}

// Load Amenities
async function loadAmenities() {
    const container = document.getElementById('amenities-container');
    if (!container) return;
    
    try {
        const response = await fetch('/api/amenities');
        if (!response.ok) {
            container.innerHTML = '<div class="error">Amenities data unavailable</div>';
            return;
        }
        
        const data = await response.json();
        displayAmenities(data);
    } catch (error) {
        console.error('Error loading amenities:', error);
        container.innerHTML = '<div class="error">Error loading amenities</div>';
    }
}

function displayAmenities(data) {
    const container = document.getElementById('amenities-container');
    const foodRaw = data.food || {};
    const loungesRaw = data.lounges || {};

    const groupByTerminal = (items) => {
        if (!Array.isArray(items)) {
            return items || {};
        }
        return items.reduce((acc, item) => {
            const terminalText = String(item.terminal || "");
            const terminalId = terminalText.replace(/[^0-9]/g, "") || "1";
            if (!acc[terminalId]) {
                acc[terminalId] = [];
            }
            acc[terminalId].push(item);
            return acc;
        }, {});
    };

    const food = groupByTerminal(foodRaw);
    const lounges = groupByTerminal(loungesRaw);
    
    const html = `
        <div class="amenities-grid">
            ${['1', '2', '3'].map(terminalId => `
                <div class="terminal-amenity-card">
                    <h3 class="terminal-amenity-title">Terminal ${terminalId}</h3>
                    
                    <div class="amenity-group">
                        <h4 class="amenity-group-title">Food & Beverage</h4>
                        ${food[terminalId] && food[terminalId].length > 0 ? `
                            <ul class="amenity-list">
                                ${food[terminalId].map(item => `
                                    <li class="amenity-item">
                                        <span class="amenity-name">${item.name || 'Unknown'}</span>
                                        ${(item.type || item.category) ? `<span class="amenity-type">${item.type || item.category}</span>` : ''}
                                    </li>
                                `).join('')}
                            </ul>
                        ` : '<p class="amenity-empty">No food options available</p>'}
                    </div>
                    
                    <div class="amenity-group">
                        <h4 class="amenity-group-title">Lounges</h4>
                        ${lounges[terminalId] && lounges[terminalId].length > 0 ? `
                            <ul class="amenity-list">
                                ${lounges[terminalId].map(item => `
                                    <li class="amenity-item">
                                        <span class="amenity-name">${item.name || 'Unknown'}</span>
                                        ${(item.type || item.access) ? `<span class="amenity-type">${item.type || item.access}</span>` : ''}
                                    </li>
                                `).join('')}
                            </ul>
                        ` : '<p class="amenity-empty">No lounges available</p>'}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    container.innerHTML = html;
}

loadDepartures();
loadGateWaitTimes();
loadAmenities();
setInterval(loadDepartures, 30000);
setInterval(loadGateWaitTimes, 30000);
