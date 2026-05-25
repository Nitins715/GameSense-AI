import urllib.request
import urllib.parse
import json
import re
import os
import sys

# Path to the player database
DATABASE_FILE = "ipl_players_data.json"
STATS_API_URL = "https://www.iplt20.com/comparison/show-player-stats"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

def load_database():
    """Loads the player database created by the scraper."""
    if not os.path.exists(DATABASE_FILE):
        print(f"[Error] Database file '{DATABASE_FILE}' not found.")
        print("Please run 'python scrape_ipl_players.py' first to build the player database.")
        sys.exit(1)
        
    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def search_players(db, query):
    """Searches for players matching the query case-insensitively."""
    query = query.lower().strip()
    matches = []
    
    for team_name, team_data in db.get("teams", {}).items():
        team_code = team_data.get("code")
        for category, players in team_data.get("categories", {}).items():
            for p in players:
                if query in p["name"].lower():
                    matches.append({
                        "id": p["id"],
                        "name": p["name"],
                        "image_url": p["image_url"],
                        "team": team_name,
                        "team_code": team_code,
                        "role": category
                    })
                    
    # Deduplicate matches (a player can be in multiple categories, e.g. All Rounder & Bowler)
    unique_matches = []
    seen_ids = set()
    for m in matches:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            unique_matches.append(m)
            
    return unique_matches

def fetch_live_stats(player_name, team_code):
    """Queries the IPL stats endpoint for a player's live metrics."""
    params = {
        'player_one[name]': player_name,
        'player_one[team]': team_code,
        'player_one[role]': '',
        'player_two[name]': '',
        'player_two[team]': '',
        'player_two[role]': ''
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f"{STATS_API_URL}?{query_string}"

    req = urllib.request.Request(full_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            data = json.loads(content)
            
            if not data.get('status'):
                return None
                
            html = data.get("html", "")
            
            # Extract player bio details (DOB, Batting/Bowling style) from player_one HTML
            bio_html = data.get("player_one", "")
            dob = "N/A"
            bat_style = "N/A"
            bowl_style = "N/A"
            
            # Simple regex to extract bio lines from player_one details block
            bio_match = re.search(r'<div class="details">\s*<span>([^<]+)</span>\s*<span>([^<]+)</span>\s*<span>([^<]*)</span>', bio_html, re.DOTALL)
            if bio_match:
                dob = bio_match.group(1).strip()
                bat_style = bio_match.group(2).strip()
                bowl_style = bio_match.group(3).strip() if bio_match.group(3) else "N/A"

            # Parse stats metrics using regex
            pattern = re.compile(
                r"<span\s+class=['\"]section2_progressBarPointleft['\"]>([^<]*)</span>\s*"
                r"<p\s+class=['\"]section2_text['\"]>([^<]*)</p>",
                re.DOTALL
            )
            
            metrics = pattern.findall(html)
            
            stats = {}
            for val, label in metrics:
                label_cleaned = label.strip()
                val_cleaned = val.strip()
                if label_cleaned:
                    stats[label_cleaned] = val_cleaned
                    
            return {
                "bio": {
                    "dob": dob,
                    "bat_style": bat_style,
                    "bowl_style": bowl_style
                },
                "stats": stats
            }
            
    except Exception as e:
        print(f"[Error] Failed to fetch live stats: {e}")
        return None

def print_stats_card(player, data):
    """Renders a gorgeous terminal stats card for the player."""
    name = player["name"]
    team = player["team"]
    code = player["team_code"]
    role = player["role"]
    bio = data["bio"]
    stats = data["stats"]
    
    # Check if we have valid stats (all zeroes usually means no official stats recorded)
    has_stats = any(v != "0" and v != "N/A" and v != "" for k, v in stats.items() if k not in ["Hat-tricks", "Maidens"])
    
    border = "=" * 60
    header_title = f" IPL PLAYER PROFILE: {name.upper()} "
    padded_title = header_title.center(60, "=")
    
    print(f"\n{padded_title}")
    print(f" Team: {team} ({code})")
    print(f" Squad Category: {role}")
    print(f" Date of Birth: {bio['dob']}")
    print(f" Batting Style: {bio['bat_style']}")
    print(f" Bowling Style: {bio['bowl_style']}")
    print(border)
    
    if not has_stats:
        print("  * No IPL career statistics found for this player. *")
        print(border)
        return
        
    # Group stats by category
    batting_metrics = ["Matches", "Innings", "Runs", "Balls Faced", "Average", "Strike Rate", "Highest Score", "100s", "50s", "4s", "6s", "Ducks"]
    bowling_metrics = ["Wickets", "Runs Conceded", "Dots", "Economy", "Maidens", "Best Bowling Figures", "4 Wickets Haul", "5 Wickets Haul", "Hat-tricks"]
    fielding_metrics = ["Catches", "Stumpings"]
    
    # 1. Batting Section
    print(" BATTING STATISTICS:")
    for metric in batting_metrics:
        val = stats.get(metric, "N/A")
        # Format strike rate and average beautifully
        print(f"  - {metric:<25}: {val}")
        
    # 2. Bowling Section
    # Show bowling section only if they have bowled balls/conceded runs
    has_bowled = stats.get("Runs Conceded", "0") != "0" or stats.get("Wickets", "0") != "0"
    if has_bowled:
        print(f"\n BOWLING STATISTICS:")
        for metric in bowling_metrics:
            val = stats.get(metric, "N/A")
            print(f"  - {metric:<25}: {val}")
            
    # 3. Fielding Section
    print(f"\n FIELDING STATISTICS:")
    for metric in fielding_metrics:
        val = stats.get(metric, "N/A")
        print(f"  - {metric:<25}: {val}")
        
    print(border + "\n")

def main():
    print("====================================================")
    print("        IPL Player Live Statistics Search           ")
    print("====================================================")
    
    db = load_database()
    
    while True:
        query = input("\nEnter player name to search (or 'q' to quit): ").strip()
        if not query:
            continue
        if query.lower() == 'q':
            print("Goodbye!")
            break
            
        matches = search_players(db, query)
        
        if len(matches) == 0:
            print(f"[Info] No players matching '{query}' found in database.")
            continue
            
        selected_player = None
        if len(matches) == 1:
            selected_player = matches[0]
        else:
            print(f"\nFound {len(matches)} matching players:")
            for idx, m in enumerate(matches, 1):
                print(f"{idx}. {m['name']} ({m['team_code']} - {m['role']})")
                
            choice = input(f"Select player (1-{len(matches)}) [or Enter to cancel]: ").strip()
            if not choice:
                continue
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(matches):
                    selected_player = matches[choice_idx]
                else:
                    print("[Error] Invalid selection.")
                    continue
            except ValueError:
                print("[Error] Please enter a valid number.")
                continue
                
        # Fetch and print live stats
        print(f"\n[Info] Querying live stats for {selected_player['name']} ({selected_player['team_code']}) from iplt20.com...")
        stats_data = fetch_live_stats(selected_player["name"], selected_player["team_code"])
        
        if stats_data:
            print_stats_card(selected_player, stats_data)
        else:
            print(f"[Error] Could not retrieve statistics for {selected_player['name']}.")

if __name__ == "__main__":
    main()
