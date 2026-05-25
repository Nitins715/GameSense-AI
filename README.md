# GameSense AI & CricSense 🏏

A high-performance full-stack cricket analytics ecosystem and interactive **IPL Matchup Battleground Simulator** web application. 

GameSense AI simulates micro-battles between batters and bowlers (e.g. *Virat Kohli vs. Jasprit Bumrah*) by parsing **1,235 complete historical IPL matches** (over **293,000+ legal deliveries** faced from 2008 to today) in less than **10 milliseconds** using an optimized in-memory Python engine.

---

## 🚀 Key Features

### 🔮 1. GameSense AI: Matchup Battleground (Web UI)
* **Autocomplete Player Search**: Intelligent dropdown menus showing player headshots and active team rosters.
* **Live Matchup Predictor Gauge**: Dynamic circular speedometer rendering the calculated **Batter Dominance Index** dynamically.
* **Dismissal Breakdown Chart**: Dynamic progress bars displaying how the bowler has dismissed the batter historically (caught, bowled, LBW, etc.).
* **Intel Skill Archetypes**: Compares stances vs. bowling categories (e.g. *Virat Kohli vs. Finger Spin*) when direct head-to-head match data is sparse.
* **Preset Battles**: One-click quick actions to simulate iconic matchups (Kohli vs Bumrah, Dhoni vs Narine, etc.).

### 📋 2. CricSense CLI Utilities
* **Roster Scraper (`scrape_ipl_players.py`)**: Crawls active rosters from the official IPL server to build a master [ipl_players_data.json](ipl_players_data.json) index.
* **Live Player Stats Search (`search_player_stats.py`)**: CLI utility to look up any player, fetching their live career milestones on-demand.
* **Live Team Stats Search (`search_team_stats.py`)**: CLI utility returning comprehensive franchise milestones (highest/lowest totals, run/wicket averages).
* **Ball-by-Ball Downloader (`download_ipl_matches.py`)**: Direct data fetcher that grabs Cricsheet's official compressed ball-by-ball package and unpacks it.

---

## 🛠️ Technology Stack

* **Backend**: Python 3.13+, Flask
* **Data Processing**: In-Memory flat delivery array indexing (`urllib`, `re`, `json`)
* **Frontend**: HTML5 Semantic Structure
* **Styling**: Vanilla CSS (midnight stadium dark theme, glassmorphic layout, glowing neon accents, fully responsive grids)
* **Logic**: Vanilla JavaScript ES6 (dynamic SVGs, AJAX queries, autocomplete suggest search, gauge rotation)

---

## 📂 Project Directory Structure

```text
CricSense/
│
├── static/
│   ├── css/
│   │   └── style.css            # Dark mode stadium visuals & animations
│   └── js/
│       └── app.js               # Search autocomplete & gauge manipulators
│
├── templates/
│   └── index.html               # Main frontend simulator interface
│
├── data_engine.py               # In-memory parsing & matchup engine
├── app.py                       # Flask server & dynamic bio cached scraper
│
├── scrape_ipl_players.py        # Active rosters scraper
├── search_player_stats.py       # Live player stats CLI search
├── search_team_stats.py         # Live team stats CLI search
├── download_ipl_matches.py      # Ball-by-ball dataset downloader
│
├── ipl_players_data.json        # Scraped players roster database
├── .gitignore                   # Excludes virtual env, datasets & caches
└── README.md                    # Repository documentation
```

---

## 🏁 Quick Start Setup Guide

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/CricSense.git
cd CricSense
```

### 2. Create and Activate Virtual Environment
```bash
# Create environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Mac/Linux
source .venv/bin/activate
```

### 3. Install Flask
```bash
pip install Flask
```

### 4. Fetch the Ball-by-Ball Dataset & Rosters
To pre-load the 1,235 matches locally, run the Cricsheet downloader script:
```bash
python download_ipl_matches.py
```

### 5. Launch the Application!
Run the Flask server:
```bash
python app.py
```
Open your browser and navigate to **[http://127.0.0.1:5005](http://127.0.0.1:5005)** to start simulating matchups!

---

## 🛡️ License & Sources
* **Data Source**: Ball-by-ball datasets provided by [Cricsheet](https://cricsheet.org/).
* **Statistics & Bio**: Resolved from the official [IPLT20 website](https://www.iplt20.com/).
