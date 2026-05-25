import urllib.request
import urllib.parse
import json
import re
import time
import os
import argparse
from datetime import datetime, timezone

# URL of the player list endpoint
API_URL = "https://www.iplt20.com/comparison/player-list"

# User-Agent and headers to look like a standard web browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

# Define IPL teams (Active and Historical)
ACTIVE_TEAMS = {
    "CSK": "Chennai Super Kings",
    "DC": "Delhi Capitals",
    "GT": "Gujarat Titans",
    "KKR": "Kolkata Knight Riders",
    "LSG": "Lucknow Super Giants",
    "MI": "Mumbai Indians",
    "PBKS": "Punjab Kings",
    "RR": "Rajasthan Royals",
    "RCB": "Royal Challengers Bengaluru",
    "SRH": "Sunrisers Hyderabad"
}

HISTORICAL_TEAMS = {
    "DEC": "Deccan Chargers",
    "GL": "Gujarat Lions",
    "KOCHI": "Kochi Tuskers Kerala",
    "PWI": "Pune Warriors India",
    "RPS": "Rising Pune Supergiant"
}

# Define the categories / roles
ROLES = {
    "bat": "Batsman",
    "bowl": "Bowler",
    "all": "All Rounder",
    "wk": "Wicket Keeper"
}

def fetch_players_for_team_role(team_code, role_code):
    """
    Fetches the players for a specific team and role combination.
    """
    params = {
        'team': team_code,
        'type': 'one',
        'role': role_code
    }
    query_string = urllib.parse.urlencode(params)
    full_url = f"{API_URL}?{query_string}"
    
    req = urllib.request.Request(full_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            
            if not data.get('status'):
                return []
                
            html = data.get('html', '')
            
            # Regex to find all player cards
            pattern = re.compile(
                r'<div[^>]*class="players team-details [^"]*"[^>]*data-name="([^"]+)"[^>]*id="([^"]+)"[^>]*>.*?'
                r'<img[^>]*src="([^"]+)"',
                re.DOTALL
            )
            
            players = []
            matches = pattern.findall(html)
            for name, player_id, img_url in matches:
                players.append({
                    "id": player_id,
                    "name": name.strip(),
                    "image_url": img_url.strip()
                })
            
            return players
            
    except Exception as e:
        print(f"  [Error] Failed to fetch data for {team_code} ({role_code}): {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="IPL Player Web Scraper Script")
    parser.add_argument("--mode", choices=["active", "all", "team"], help="Scraping mode")
    parser.add_argument("--team", type=str, help="Specific Team Code (e.g. CSK) if mode is 'team'")
    args = parser.parse_args()

    print("====================================================")
    print("           IPL Player Web Scraper Script            ")
    print("====================================================\n")
    
    mode = args.mode
    team_code = args.team
    
    # If no CLI args are passed, fall back to interactive mode
    if mode is None:
        print("Please select which teams you want to scrape:")
        print("1. Active Teams only (10 current teams - Recommended)")
        print("2. All Teams (Active + 5 Historical teams)")
        print("3. Specific Team only")
        
        choice = input("\nEnter choice (1/2/3) [Default: 1]: ").strip()
        if not choice or choice == "1":
            mode = "active"
        elif choice == "2":
            mode = "all"
        elif choice == "3":
            mode = "team"
            
    teams_to_scrape = {}
    combined = {**ACTIVE_TEAMS, **HISTORICAL_TEAMS}
    
    if mode == "active":
        teams_to_scrape = ACTIVE_TEAMS
    elif mode == "all":
        teams_to_scrape = combined
    elif mode == "team":
        if team_code is None:
            print("\nAvailable Teams:")
            for code, name in combined.items():
                status = "Active" if code in ACTIVE_TEAMS else "Historical"
                print(f"- {code}: {name} ({status})")
            team_code = input("\nEnter the Team Code (e.g., CSK): ").strip().upper()
        else:
            team_code = team_code.upper()
            
        if team_code in combined:
            teams_to_scrape = {team_code: combined[team_code]}
        else:
            print(f"[Error] Invalid Team Code '{team_code}'. Exiting.")
            return
            
    print(f"[Info] Starting scraping for {len(teams_to_scrape)} team(s) in mode '{mode}'...")
    
    results = {
        "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_teams": len(teams_to_scrape),
        "teams": {}
    }
    
    for i, (team_code, team_name) in enumerate(teams_to_scrape.items(), 1):
        print(f"\n[{i}/{len(teams_to_scrape)}] Scraping Team: {team_name} ({team_code})")
        
        results["teams"][team_name] = {
            "code": team_code,
            "categories": {}
        }
        
        team_total = 0
        for role_code, role_name in ROLES.items():
            print(f"  Fetching {role_name} list...", end="", flush=True)
            
            # Call API
            players = fetch_players_for_team_role(team_code, role_code)
            
            results["teams"][team_name]["categories"][role_name] = players
            team_total += len(players)
            
            print(f" Done. Found {len(players)} players.")
            
            # Polite delay to respect the server
            time.sleep(0.5)
            
        print(f"  -> Total player entries for {team_code}: {team_total}")
        
    # Write output to JSON file
    output_filename = "ipl_players_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("\n====================================================")
    print(f"[Success] Scraping completed successfully!")
    print(f"[Success] Data written to: {os.path.abspath(output_filename)}")
    print("====================================================")

if __name__ == "__main__":
    main()
