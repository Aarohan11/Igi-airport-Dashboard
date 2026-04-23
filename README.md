# IGI Airport Real-Time Operations System

## Overview
A comprehensive real-time flight operations and congestion monitoring system for Indira Gandhi International Airport (IGI Airport, Delhi). The system integrates live aviation data with operational analytics to provide real-time insights into departures, passenger loads, and gate/security congestion.

## ✨ Features

### Real-Time Dashboard
- **Live Flight Data**: Departures updated every 30 seconds from aviation network
- **Terminal Organization**: Flights grouped by terminal (1, 2, 3) with domestic/international separation
- **Passenger Load Analysis**: Automated estimation based on aircraft type and route
- **Congestion Monitoring**: Real-time security and gate utilization metrics
- **Auto-Refresh**: Dashboard automatically updates departures and congestion data

### Enhanced User Interface
- **Color-Coded Status Indicators**: Visual indicators for flight statuses with smooth transitions
  - **Scheduled** (Blue): ≥120 min to departure
  - **Check-in** (Green): 60-120 min to departure
  - **Boarding** (Orange): 30-60 min to departure
  - **Final Call** (Yellow): 0-30 min to departure (animated pulse)
  - **Gate Closed** (Red): Gate closing (up to 5 min after departure)
  - **Departed** (Purple): ≥5 min after departure
- **Responsive Grid Layout**: Organized flight cards with hover effects
- **Mobile-Friendly**: Adapts to all device sizes
- **Real-Time Status Updates**: Flight statuses update based on current time without page refresh

### Flight Search & Details
- **Flight Search**: Quick search for any flight number (e.g., "AI101", "AXB126")
- **Comprehensive Details**: 
  - Airline and aircraft information
  - Gate and terminal assignments
  - Origin and destination with country info
  - Real-time congestion metrics
- **Terminal Amenities**: Specific food & beverage and lounge information per terminal
- **Auto-Refresh**: Details page refreshes every 20 seconds

## System Architecture
- **Backend**: Flask REST API with Python 3.13+
- **Frontend**: Responsive HTML5, CSS3, and Vanilla JavaScript
- **Data Source**: Multi-provider real-time aviation APIs (Aviation Edge primary, fallback chain enabled)
- **Static Data**: JSON datasets for terminal amenities
- **Real-Time Updates**: AJAX-based automatic refresh without page reload

## How It Works

### Flight Status Timeline
The system automatically transitions flights through operational stages based on time to departure:

```
Scheduled (>2h)
    ↓
Check-in (1-2h)
    ↓
Boarding (30m-1h)
    ↓
Final Call (0-30m) ← Animated attention-getter
    ↓
Gate Closed (0 to -5m)
    ↓
Departed (>5m past scheduled time)
```

### Operational Monitoring
- **Terminal Distribution**: Real-time flight count per terminal
- **Passenger Estimation**: Aircraft capacity classification (narrow-body ~180 passengers, wide-body ~300+)
- **Congestion Modeling**: Queue-based analysis of departure loads
- **Amenities Lookup**: Terminal-specific food venues and lounges

## Installation & Setup

### Prerequisites
- Python 3.13+
- pip package manager

### 1. Clone Repository
```bash
git clone <repository-url>
cd airport-system
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```
FLIGHT_DATA_PROVIDER=auto
ALLOW_LOW_CONFIDENCE_FALLBACK=false

# Primary (recommended)
AVIATION_EDGE_API_KEY=your_aviation_edge_key_here
AVIATION_EDGE_BASE=https://aviation-edge.com/v2/public

# ADSB.lol live traffic API (optional, lower confidence for departure scheduling)
ADSB_LOL_BASE=https://api.adsb.lol/v2
ADSB_LOL_DELHI_LAT=28.5562
ADSB_LOL_DELHI_LON=77.1000
ADSB_LOL_DELHI_RADIUS_NM=40

# Fallback provider (optional)
AVIATION_API_KEY=your_aviationstack_key_here
AVIATION_API_BASE=http://api.aviationstack.com/v1

PORT=3000
FLASK_ENV=development
```

Provider behavior:
- `FLIGHT_DATA_PROVIDER=auto` (default) uses: Aviation Edge -> AviationStack -> ADSB.lol (emergency real-time fallback).
- `ALLOW_LOW_CONFIDENCE_FALLBACK=false` (default) disables OpenSky/local synthetic fallback to avoid inaccurate/estimated routes.
- Set `ALLOW_LOW_CONFIDENCE_FALLBACK=true` only if you prefer always-on availability over strict accuracy. This enables ADSB.lol/OpenSky/local providers.
- Set `FLIGHT_DATA_PROVIDER` to `aviation_edge`, `aviationstack`, `adsb_lol`, `opensky`, or `local` for fixed single-provider behavior.

### 5. Run the Application
```bash
python backend/app.py
```

The application will be available at `http://127.0.0.1:3000`

## Usage Guide

### Home Page (/)
- View system highlights and features
- **Flight Search Section**: Enter any flight number to search
- Navigate to Operational Dashboard via "Open Operational Dashboard" button

### Operational Dashboard (/dashboard)
- **Upper Section**: 
  - Departure count in next 7-hour window
  - Estimated total passengers
  - Current congestion level and wait time
- **Terminal Cards**: Organized by terminal (1, 2, 3)
  - Domestic flights listed first
  - International flights listed below
  - Each flight shows: Number, Status, Route, Departure Time, Gate, Aircraft Type
- **Terminal Amenities**: 
  - Expandable sections for food/beverage and lounges
  - Terminal 1-3 breakdowns
- **Auto-Refresh**: Page updates every 30 seconds for flights, 2 minutes for amenities

### Flight Detail Page (/flight?flight=FLIGHT_NUMBER)
Access via:
1. Search on home page
2. Click any flight card on dashboard

Displays:
- Flight status with color coding
- Airline and aircraft details
- Terminal and gate information
- Congestion metrics for that terminal
- Food & beverage options in terminal
- Available lounges
- Scheduled vs. estimated times

**Auto-Refresh**: Page updates every 20 seconds

## API Reference

### GET /api/departures
Returns departures for next 7-hour window organized by terminal.
```json
{
  "count": 17,
  "used_fallback": false,
  "departures": [...],
  "terminals": {
    "1": { "domestic": [...], "international": [...] },
    "2": { "domestic": [...], "international": [...] },
    "3": { "domestic": [...], "international": [...] }
  }
}
```

### GET /api/flight-detail?flight_number=FLIGHT_NUMBER
Returns comprehensive flight information.
```json
{
  "flight_number": "AXB126",
  "airline": "Unknown Airline",
  "aircraft": "Airbus A320",
  "route_type": "domestic",
  "origin": "DEL",
  "destination": "HYD",
  "destination_country": "India",
  "terminal": "2",
  "gate": "243",
  "status": "boarding",
  "scheduled_time": "2026-02-13T17:42:26.142300+00:00",
  "estimated_time": "2026-02-13T17:56:26.142300+00:00",
  "congestion_level": "LOW",
  "congestion_wait_time": 0.0,
  "terminal_food": [...],
  "terminal_lounges": [...]
}
```

### GET /api/congestion
Returns congestion metrics.
```json
{
  "level": "LOW",
  "wait_time_min": 0,
  "arrival_rate_per_min": 2.5,
  "service_rate_per_min": 3.2
}
```

### GET /api/amenities
Returns all terminal amenities.
```json
{
  "food": [...list of food venues...],
  "lounges": [...list of lounges...]
}
```

## Directory Structure
```
airport-system/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── api_client.py          # Aviation API client
│   ├── aircraft_data.py       # Aircraft information database
│   ├── opensky_client.py      # OpenSky data integration
│   ├── congestion_model.py    # Congestion calculation logic
│   ├── data/
│   │   ├── food.json          # Terminal food venues
│   │   └── lounges.json       # Terminal lounges
│   └── __pycache__/
├── frontend/
│   ├── templates/
│   │   ├── index.html         # Home page with flight search
│   │   ├── dashboard.html     # Operational dashboard
│   │   └── flight-detail.html # Flight detail page
│   └── static/
│       ├── script.js          # JavaScript with auto-refresh logic
│       └── styles.css         # Responsive styling
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── test_api.py               # API testing script
```

## Technology Stack
- **Backend Framework**: Flask 3.0.3
- **HTTP Requests**: requests 2.32.3
- **Environment Management**: python-dotenv 1.0.1
- **Python Version**: 3.13+
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Charting**: Chart.js (for congestion visualization)

## Color Palette
| Element | Color | Purpose |
|---------|-------|---------|
| Domestic Flights | #0d5c63 (Teal) | Left border on flight cards |
| International Flights | #c35a2a (Orange) | Left border on flight cards |
| Scheduled Status | #1976d2 (Blue) | Status indicator |
| Boarding Status | #e65100 (Orange) | Status indicator |
| Check-in Status | #2e7d32 (Green) | Status indicator |
| Final Call Status | #f57f17 (Yellow) | Status indicator + Animation |
| Gate Closed Status | #c62828 (Red) | Status indicator |
| Departed Status | #6a1b9a (Purple) | Status indicator |

## Performance Characteristics
- Dashboard initial load: ~1-2 seconds
- API response time: <500ms
- Auto-refresh intervals: 30s (flights), 2m (amenities), 20s (detail page)
- Minimal bandwidth usage with AJAX updates
- Supports ~50+ concurrent flights without degradation

## Testing
Run the test scripts to verify functionality:
```bash
python test_api.py
python test_flask.py
```

## Troubleshooting

### No flights appearing
- Verify AVIATION_API_KEY is valid
- Check internet connection
- API might be rate-limited (wait a few minutes)
- Check browser console for errors (F12)

### Dashboard not updating
- Verify JavaScript is enabled in browser
- Check browser console for errors
- Confirm backend is running (`http://127.0.0.1:3000` should load)

### Search not finding flights
- Verify flight number format (e.g., "AI101")
- Flight might not be in departure schedule for next 7 hours
- Check if flight is domestic/international and exists in system

## Browser Compatibility
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Future Enhancements
- Historical flight data and trends
- Push notifications for status changes
- Integration with airline systems
- Mobile native applications
- Live terminal maps with gate locations
- Weather impact analysis
- Predictive delay modeling

## Notes
- All times displayed in IST (Indian Standard Time / Asia/Kolkata)
- Passenger estimates are based on aircraft size classifications
- Congestion calculations use operational queue theory
- Real-time accuracy depends on aviation API availability
- Status transitions are automatic and client-side

## Support & Contact
For issues, feature requests, or questions:
- Check the project repository for known issues
- Review troubleshooting section above
- Contact airport operations team for system support

## License
This project is licensed under the MIT License.

## Changelog

### Version 2.0 (Current)
- ✨ Real-time status updates based on time to departure
- ✨ Auto-refresh dashboard (30s intervals)
- ✨ Enhanced flight status indicators with color coding
- ✨ Animated "Final Call" pulse attention-getter
- ✨ Flight detail page auto-refresh (20s intervals)
- 🎨 Improved responsive UI layout
- 🎨 Better visual hierarchy and spacing
- 🎨 Smooth transitions and hover effects
- ⚡ Optimized refresh intervals to reduce server load
- ✅ Mobile responsive improvements

### Version 1.0
- Initial release with basic flight search and dashboard
- Terminal-based flight organization
- Congestion monitoring
- Amenities listing

---

**Last Updated**: February 2025  
**Maintained by**: Airport Operations System Team
