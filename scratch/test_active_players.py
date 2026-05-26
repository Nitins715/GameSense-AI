import json
import os
import sys
from collections import defaultdict

# Add workspace root to sys.path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.matchup_simulator.data_engine import IPLDataEngine

def test_dates():
    print("Initializing Data Engine...")
    data_engine = IPLDataEngine()
    
    # Track latest match date for each player name
    latest_player_dates = defaultdict(str)
    
    for d in data_engine.deliveries:
        b_name = d["batter"]
        bo_name = d["bowler"]
        date = d["date"]
        
        if date > latest_player_dates[b_name]:
            latest_player_dates[b_name] = date
        if date > latest_player_dates[bo_name]:
            latest_player_dates[bo_name] = date
            
    # Load roster to check our names mapping
    roster_file = "ipl_players_data.json"
    with open(roster_file, "r", encoding="utf-8") as f:
        db_data = json.load(f)
        
    print("\nSample Roster Players and their Latest Match Dates:")
    
    historical_count = 0
    active_count = 0
    missing_count = 0
    
    for team_name, team_data in db_data.get("teams", {}).items():
        print(f"\n--- {team_name} ---")
        team_players = []
        for cat, players in team_data.get("categories", {}).items():
            for p in players[:3]:  # Look at a few players
                name = p["name"]
                c_name = data_engine.find_cricsheet_name(name)
                latest_date = latest_player_dates.get(c_name, "N/A")
                
                status = "ACTIVE" if latest_date >= "2021-01-01" else "HISTORICAL"
                if latest_date == "N/A":
                    status = "MISSING IN DATABASE"
                    missing_count += 1
                elif status == "ACTIVE":
                    active_count += 1
                else:
                    historical_count += 1
                    
                print(f"  {name} ({c_name}): Latest Date = {latest_date} -> {status}")
                
    print(f"\nSummary of Roster Player Statuses in Sample:")
    print(f"  Active (Played since 2021): {active_count}")
    print(f"  Historical (Played before 2021): {historical_count}")
    print(f"  Missing in DB: {missing_count}")

if __name__ == "__main__":
    test_dates()
