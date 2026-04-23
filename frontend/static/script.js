// Real-time clock with IST timezone and status auto-refresh
let lastRefreshTime = null;
let flightDataCache = {};

function updateClock() {
    const clockElement = document.getElementById("current-time");
    if (clockElement) {
        const now = new Date();
        const timeStr = now.toLocaleString("en-IN", {
            weekday: "short",
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true,
            timeZone: "Asia/Kolkata"
        });
        clockElement.textContent = timeStr;
    }
    
    // Update flight statuses based on elapsed time
    updateFlightStatuses();
}

// Calculate flight status based on current time
function getFlightStatus(flight, currentTime) {
    const scheduled = new Date(flight.scheduled_time);
    const estimated = new Date(flight.estimated_time);
    const timeUntilDeparture = (scheduled - currentTime) / 1000 / 60; // minutes

    // Status progression based on time to departure
    if (timeUntilDeparture > 120) {
        return { status: "scheduled", label: "Scheduled" };
    } else if (timeUntilDeparture > 60) {
        return { status: "check-in", label: "Check-in" };
    } else if (timeUntilDeparture > 30) {
        return { status: "boarding", label: "Boarding" };
    } else if (timeUntilDeparture > 0) {
        return { status: "final-call", label: "Final Call" };
    } else if (timeUntilDeparture > -5) {
        return { status: "gate-closed", label: "Gate Closed" };
    } else {
        return { status: "departed", label: "Departed" };
    }
}

function updateFlightStatuses() {
    const currentTime = new Date();
    const flightElements = document.querySelectorAll('.flight-card');
    
    flightElements.forEach(element => {
        const flightNumber = element.getAttribute('data-flight-number');
        const scheduledTime = element.getAttribute('data-scheduled-time');
        
        if (!flightNumber || !scheduledTime) return;
        
        const flight = { scheduled_time: scheduledTime };
        const newStatus = getFlightStatus(flight, currentTime);
        const statusElement = element.querySelector('.flight-status');
        
        if (statusElement) {
            statusElement.textContent = newStatus.label;
            statusElement.className = `flight-status status-${newStatus.status}`;
        }
    });
}

updateClock();
setInterval(updateClock, 1000);

const flightForm = document.getElementById("flight-form");
const flightResult = document.getElementById("flight-result");
const flightError = document.getElementById("flight-error");

if (flightForm) {
    flightForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        flightError.textContent = "";
        flightResult.innerHTML = "";
        const flightNumber = document.getElementById("flight-number").value.trim().toUpperCase();
        if (!flightNumber) {
            flightError.textContent = "Please enter a flight number.";
            return;
        }

        try {
            const response = await fetch(`/api/flight-detail?flight_number=${encodeURIComponent(flightNumber)}`);
            const data = await response.json();
            if (!response.ok) {
                flightError.textContent = data.error || "Unable to fetch flight.";
                return;
            }

            window.location.href = `/flight?flight=${encodeURIComponent(flightNumber)}`;
        } catch (error) {
            flightError.textContent = "Network error while retrieving flight data.";
        }
    });
}

const terminalDepartures = document.getElementById("terminal-departures");
const departureCount = document.getElementById("departure-count");
const passengerCount = document.getElementById("passenger-count");
const windowNote = document.getElementById("window-note");
const waitTime = document.getElementById("wait-time");
const congestionLevel = document.getElementById("congestion-level");
const foodList = document.getElementById("food-list");
const loungeList = document.getElementById("lounge-list");

async function loadDepartures() {
    if (!terminalDepartures) return;
    terminalDepartures.innerHTML = "";

    const response = await fetch("/api/departures");
    const data = await response.json();
    if (!response.ok) {
        terminalDepartures.innerHTML = `<p class="error-text">${data.error || "Unable to load departures."}</p>`;
        return;
    }

    departureCount.textContent = data.count;
    if (windowNote) {
        if (data.used_fallback) {
            windowNote.textContent = "No departures in the next 7 hours. Showing the next available 7-hour window.";
        } else {
            windowNote.textContent = "";
        }
    }
    const passengerEstimate = data.departures.reduce((sum, flight) => {
        const code = flight.aircraft_iata || "";
        const wide = code.startsWith("33") || code.startsWith("34") || code.startsWith("35") ||
            code.startsWith("38") || code.startsWith("74") || code.startsWith("75") ||
            code.startsWith("76") || code.startsWith("77") || code.startsWith("78") ||
            code.startsWith("87") || code.startsWith("88") || code.startsWith("90");
        return sum + (wide ? 300 : 180);
    }, 0);
    passengerCount.textContent = passengerEstimate;

    const terminals = data.terminals || {};
    const terminalOrder = ["1", "2", "3"];
    const sections = terminalOrder.map((terminalId) => {
        const groups = terminals[terminalId] || { domestic: [], international: [] };
        const domesticList = groups.domestic || [];
        const internationalList = groups.international || [];
        const total = domesticList.length + internationalList.length;

        const buildFlightCard = (flight) => {
            const isInternational = flight.route_type === "international";
            const cardClass = isInternational ? "international" : "domestic";
            const depTime = new Date(flight.scheduled_time);
            const timeStr = depTime.toLocaleTimeString("en-IN", {
                hour: "2-digit",
                minute: "2-digit",
                hour12: true
            });
            
            // Format status nicely (check-in -> Check-in, gate-closed -> Gate Closed, etc.)
            const statusText = (flight.status || "scheduled")
                .split("-")
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(" ");
            
            const statusClass = `status-${flight.status || "scheduled"}`;

            return `
                <a href="/flight?flight=${flight.flight_number}" style="text-decoration: none; color: inherit;">
                    <div class="flight-card ${cardClass}" data-flight-number="${flight.flight_number}" data-scheduled-time="${flight.scheduled_time}" style="cursor: pointer;">
                        <div class="flight-header">
                            <div class="flight-number">${flight.flight_number}</div>
                            <span class="flight-status ${statusClass}">${statusText}</span>
                        </div>
                        <div class="flight-route">
                            <div class="route-airport">
                                <div class="airport-code">${flight.origin}</div>
                                <div class="airport-name">Origin</div>
                            </div>
                            <div class="route-arrow">→</div>
                            <div class="route-airport">
                                <div class="airport-code">${flight.destination}</div>
                                <div class="airport-name">${flight.destination_country}</div>
                            </div>
                        </div>
                        <div class="flight-details">
                            <div class="detail-item">
                                <div class="detail-label">Departure</div>
                                <div class="detail-value">${timeStr}</div>
                            </div>
                            <div class="detail-item gate-info">
                                <div class="detail-label">Gate</div>
                                <div class="detail-value">${flight.gate || "TBD"}</div>
                            </div>
                            ${flight.aircraft_name ? `
                                <div class="detail-item aircraft-type">
                                    <div class="detail-label">Aircraft</div>
                                    <div class="detail-value">${flight.aircraft_name}</div>
                                </div>
                            ` : ""}
                            <div class="detail-item">
                                <div class="detail-label">Type</div>
                                <div class="detail-value">${isInternational ? "International" : "Domestic"}</div>
                            </div>
                        </div>
                    </div>
                </a>
            `;
        };

        const showInternational = terminalId === "3";
        const domesticHtml = domesticList.length 
            ? domesticList.map(buildFlightCard).join("") 
            : '<div class="empty-state">No domestic departures in window</div>';
        
        const internationalHtml = showInternational
            ? (internationalList.length 
                ? internationalList.map(buildFlightCard).join("") 
                : '<div class="empty-state">No international departures in window</div>')
            : '<div class="empty-state">International departures are serviced at Terminal 3 only</div>';

        return `
            <div class="terminal-card">
                <div class="terminal-header">
                    <h3>Terminal ${terminalId}</h3>
                    <span class="chip">${total} departures</span>
                </div>
                <div class="terminal-section">
                    <h4>🛫 Domestic Flights</h4>
                    ${domesticHtml}
                </div>
                <div class="terminal-section">
                    <h4>✈️ ${showInternational ? "International Flights" : "International Flights"}</h4>
                    ${internationalHtml}
                </div>
            </div>
        `;
    });

    terminalDepartures.innerHTML = sections.join("");
}

async function loadCongestion() {
    if (!waitTime) return;
    const response = await fetch("/api/congestion");
    const data = await response.json();
    if (!response.ok) {
        waitTime.textContent = "--";
        congestionLevel.textContent = data.error || "Unavailable";
        return;
    }

    waitTime.textContent = `${data.wait_time_min} min`;
    congestionLevel.textContent = data.level;
    congestionLevel.className = `badge ${data.level.toLowerCase()}`;

    const ctx = document.getElementById("congestion-chart");
    if (ctx) {
        new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Arrival Rate", "Service Capacity"],
                datasets: [
                    {
                        label: "Passengers per Minute",
                        data: [data.arrival_rate_per_min, data.service_rate_per_min],
                        backgroundColor: ["#c35a2a", "#0d5c63"],
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }
}

async function loadAmenities() {
    if (!foodList || !loungeList) return;
    const response = await fetch("/api/amenities");
    const data = await response.json();
    if (!response.ok) {
        foodList.innerHTML = `<p class="error-text">${data.error || "Unable to load amenities."}</p>`;
        return;
    }

    const foodByTerminal = { "Terminal 1": [], "Terminal 2": [], "Terminal 3": [] };
    const loungeByTerminal = { "Terminal 1": [], "Terminal 2": [], "Terminal 3": [] };

    data.food.forEach((item) => {
        if (foodByTerminal.hasOwnProperty(item.terminal)) {
            foodByTerminal[item.terminal].push(item);
        }
    });

    data.lounges.forEach((item) => {
        if (loungeByTerminal.hasOwnProperty(item.terminal)) {
            loungeByTerminal[item.terminal].push(item);
        }
    });

    const buildTerminalSection = (groupedData, isFood = true) => {
        const terminals = ["Terminal 1", "Terminal 2", "Terminal 3"];
        return terminals
            .map((terminal) => {
                const items = groupedData[terminal] || [];
                const id = `${isFood ? "food" : "lounge"}-${terminal.replace(/\s+/g, "")}`;
                const itemHtml = items
                    .map(
                        (item) =>
                            `<div class="amenity-item">
                                <strong>${item.name}</strong>
                                <p>${isFood ? item.category : `Access: ${item.access}`}</p>
                                <p class="amenity-location">${item.location}${!isFood ? ` | ${item.booking}` : ""}</p>
                            </div>`
                    )
                    .join("");

                return `
                    <div class="terminal-dropdown">
                        <button class="dropdown-toggle" onclick="toggleDropdown('${id}')">
                            <span class="dropdown-arrow">▼</span>
                            ${terminal} <span class="item-count">(${items.length})</span>
                        </button>
                        <div id="${id}" class="dropdown-content">
                            ${itemHtml || '<p class="empty-state">No items available</p>'}
                        </div>
                    </div>
                `;
            })
            .join("");
    };

    foodList.innerHTML = buildTerminalSection(foodByTerminal, true);
    loungeList.innerHTML = buildTerminalSection(loungeByTerminal, false);
}

function toggleDropdown(id) {
    const element = document.getElementById(id);
    if (element) {
        element.classList.toggle("open");
        const button = element.previousElementSibling;
        if (button) {
            button.classList.toggle("active");
        }
    }
}

loadDepartures();
loadCongestion();
loadAmenities();

setTimeout(() => {
    const firstFoodDropdown = document.getElementById("food-Terminal1");
    const firstLoungeDropdown = document.getElementById("lounge-Terminal1");
    if (firstFoodDropdown) {
        firstFoodDropdown.classList.add("open");
        firstFoodDropdown.previousElementSibling.classList.add("active");
    }
    if (firstLoungeDropdown) {
        firstLoungeDropdown.classList.add("open");
        firstLoungeDropdown.previousElementSibling.classList.add("active");
    }
}, 100);
// Auto-refresh dashboard every 30 seconds with smooth transitions
setInterval(() => {
    loadDepartures();
    loadCongestion();
}, 30000);

// Every 2 minutes, also refresh amenities (less frequently as they change less often)
setInterval(() => {
    loadAmenities();
}, 120000);