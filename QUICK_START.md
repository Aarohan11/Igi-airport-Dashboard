# IGI Airport System - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Start the Application
```bash
cd "c:\Users\ASUS\Desktop\airport system"
.venv\Scripts\activate
python backend/app.py
```

The application will start on `http://127.0.0.1:3000`

### Step 2: Access the System

#### Option A: Explore the Dashboard
1. Open `http://127.0.0.1:3000/dashboard`
2. See all departures for the next 7 hours
3. Organized by terminals (1, 2, 3)
4. Real-time congestion metrics at the top

#### Option B: Search for a Specific Flight
1. Open `http://127.0.0.1:3000`
2. Enter a flight number (e.g., "AI101", "AXB126")
3. Click "Search Flight"
4. View detailed flight information

## 📊 Understanding the Dashboard

### Top Metrics
- **Departure Load**: Number of flights departing in next 7 hours
- **Estimated Passengers**: Total passenger count estimate
- **Congestion Level**: Current gate/security status
- **Wait Time**: Average estimated wait in minutes

### Flight Cards
Each flight shows:
- **Flight Number** (top left)
- **Status Badge** (top right) - Color indicates stage:
  - 🔵 Blue = Scheduled (>2 hours)
  - 🟢 Green = Check-in (1-2 hours)
  - 🟠 Orange = Boarding (30m-1h)
  - 🟡 Yellow = Final Call (0-30m)
  - 🔴 Red = Gate Closed
  - 🟣 Purple = Departed
- **Route** (DEL → destination code)
- **Departure Time**
- **Gate Number**
- **Aircraft Type**
- **Flight Type** (Domestic/International)

### Terminal Sections
- **Terminal 1**: Mostly domestic flights
- **Terminal 2**: Mix of domestic flights  
- **Terminal 3**: International + some domestic
- Click tabs to expand/collapse each terminal

### Terminal Amenities
- **Food & Beverage**: Restaurants, cafes, quick service
- **Lounges**: Premium lounges organized by terminal
- Click terminal section to expand amenities list

## ✨ Real-Time Features

### Auto-Refresh
- Dashboard data updates every **30 seconds** automatically
- No need to refresh the page manually
- Amenities update every **2 minutes**

### Live Status Updates
- ⏰ Clock in header shows current IST time (updates every second)
- Flight statuses update automatically where applicable
- No page refresh - smooth transitions
- Status changes based on current time vs. departure time

### Flight Detail Auto-Refresh
- Click any flight card to see full details
- Page refreshes every **20 seconds**
- Includes gate assignments and terminal amenities
- Terminal-specific food and lounge options

## 🔍 How to Use Flight Search

### Search a Flight
1. Go to home page: `http://127.0.0.1:3000`
2. Scroll to "Real Flight Tracking" section
3. Enter flight number (e.g., "AXB126")
4. Click "Search Flight"
5. If flight is found, you'll see detailed information

### Flight Detail Page Shows
- Current status (with color coding)
- Airline and aircraft type
- Route information (origin → destination)
- Gate and terminal assignment
- Current congestion level
- Average wait time
- Terminal amenities (food & lounges)
- Scheduled vs. estimated departure times

### What If Flight Not Found?
- Flight may not be in next 7-hour window
- Flight number might be wrong (should be like "AI101")
- Try clicking the "Open Operational Dashboard" button to see available flights

## 🛠️ Understanding the Status Colors

### Flight Status Progression

```
📅 SCHEDULED (>2 hours to departure) - Blue
├─ Check in at gate
│  
📍 CHECK-IN (1-2 hours to departure) - Green
├─ Doors opening for passengers
│  
🚪 BOARDING (30m-1 hour to departure) - Orange
├─ Boarding in progress
│  
📢 FINAL CALL (0-30 minutes to departure) - Yellow ⚠️
├─ Last call for boarding
├─ (Pulses to grab attention)
│  
🚪 GATE CLOSED (0 to -5 min) - Red
├─ Gate is closing
│  
✈️ DEPARTED (>5 min past time) - Purple
└─ Flight has left the airport
```

## 📱 Mobile Access

The system works on all devices:
- 💻 Desktop browsers
- 📱 Tablets
- 📱 Mobile phones

Just navigate to `http://127.0.0.1:3000` from any device on the same network (or localhost if on same computer).

## 🎨 Terminal Features

### Terminal Cards
- **Terminal Header**: Shows terminal name and total flights
- **Domestic Section**: All domestic departures for that terminal
- **International Section**: International departures (only Terminal 3)
- **Easy Scanning**: At a glance see all flights from a terminal

### Click Any Flight To View
- Full flight details page
- Gate and terminal info
- Congestion metrics
- Terminal amenities
- Food and lounge options

## ⚙️ Troubleshooting

### Dashboard Not Loading?
1. Check if Flask server is running in terminal
2. Try accessing `http://127.0.0.1:3000` directly
3. Check browser console for errors (F12 → Console tab)

### No Flights Showing?
1. Flights only show for next 7-hour window
2. Try refreshing the page (F5)
3. Check if airline API is responding

### Flight Search Not Working?
1. Verify flight number format (e.g., "AI101")
2. Flight might not be departing in next 7 hours
3. Check if it's in the dashboard to see available flights
4. Try entering just the flight code without spaces

### Status Not Updating?
1. Check if browser JavaScript is enabled
2. Refresh browser (F5)
3. Check if page is loading (watch the time update in header)

## 💡 Pro Tips

### Best For Airport Staff
1. Pin dashboard as favorite for quick access
2. Use full-screen view (F11) for constant monitoring
3. Familiarity with status colors for quick scanning
4. Check congestion metrics to manage gate usage

### Best For Passengers
1. Search your flight number on home page
2. Check gate opening times (status changes)
3. Note terminal and amenities information
4. Terminal amenities show exact locations

### Monitoring Tips
- Yellow status (Final Call) pulses - easy to spot
- Red means gate is closing soon
- Green means check-in is open
- Check "Estimated Time" if it's different from scheduled

## 📖 Full Documentation

For detailed information, see:
- **README.md** - Complete system documentation
- **IMPROVEMENTS.md** - What was improved and how

## 🆘 Need Help?

### Common Questions

**Q: Where's my flight?**
A: Search on the home page, or check the dashboard. If it's not there, it might be departing outside the 7-hour monitoring window.

**Q: How often does data update?**
A: Dashboard updates every 30 seconds automatically. Flight statuses update every second in real-time.

**Q: Can I use this on my phone?**
A: Yes! The system is fully responsive and works on all devices.

**Q: Is my data saved?**
A: No, this is a real-time system. It fetches live data and doesn't store user data.

**Q: What time zone is used?**
A: All times are in IST (Indian Standard Time / Asia/Kolkata).

---

**Ready to explore?** Start at `http://127.0.0.1:3000` 🎯
