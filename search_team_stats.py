import urllib.request
import urllib.parse
import json
import re
import os
import sys

STATS_API_URL = "https://www.iplt20.com/comparison/show-team-stats"
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

def fetch_live_team_stats(team_code):
    """Queries the IPL team stats API for live statistics."""
    params = {
        'team_one': team_code,
        'team_two': ''
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
            
            # Simple regex to parse the metrics and values
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
                    
            return stats
            
    except Exception as e:
        print(f"[Error] Failed to fetch team stats: {e}")
        return None

def print_team_stats_card(team_code, team_name, stats):
    """Renders a gorgeous terminal stats card for the team."""
    border = "=" * 60
    header_title = f" IPL TEAM STATISTICS: {team_name.upper()} ({team_code}) "
    padded_title = header_title.center(60, "=")
    
    print(f"\n{padded_title}")
    print(border)
    
    # Define primary stats categories for clean rendering
    match_metrics = ["Played", "Won", "Lost", "Tied", "No Result"]
    record_metrics = ["Highest Team Total", "Lowest Team Total", "Avg. Runs", "Avg. Wkts"]
    top_performer_metrics = ["Most Runs", "Most Wickets", "Highest Individual Score", "Best Bowling"]
    
    # 1. Matches Record
    print(" MATCH RECORD:")
    for metric in match_metrics:
        val = stats.get(metric, "0")
        print(f"  - {metric:<25}: {val}")
        
    # 2. Team Records
    print("\n TEAM TOTALS & AVERAGES:")
    for metric in record_metrics:
        val = stats.get(metric, "N/A")
        print(f"  - {metric:<25}: {val}")
        
    # 3. Top Performers
    print("\n INDIVIDUAL TEAM LEADER RECORDS:")
    for metric in top_performer_metrics:
        val = stats.get(metric, "N/A")
        print(f"  - {metric:<25}: {val}")
        
    print(border + "\n")

def main():
    print("====================================================")
    print("        IPL Team Live Statistics Search             ")
    print("====================================================")
    
    combined_teams = {**ACTIVE_TEAMS, **HISTORICAL_TEAMS}
    
    while True:
        print("\nAvailable Teams:")
        print("--- Active Teams ---")
        for i, (code, name) in enumerate(ACTIVE_TEAMS.items(), 1):
            print(f" {i:<2}. {code:<6} : {name}")
            
        print("--- Historical Teams ---")
        for i, (code, name) in enumerate(HISTORICAL_TEAMS.items(), len(ACTIVE_TEAMS) + 1):
            print(f" {i:<2}. {code:<6} : {name}")
            
        choice = input("\nSelect team by number or enter Team Code (or 'q' to quit): ").strip()
        if not choice:
            continue
        if choice.lower() == 'q':
            print("Goodbye!")
            break
            
        selected_code = None
        selected_name = None
        
        # Check if selection is numeric choice
        try:
            choice_idx = int(choice)
            all_teams_list = list(combined_teams.items())
            if 1 <= choice_idx <= len(all_teams_list):
                selected_code, selected_name = all_teams_list[choice_idx - 1]
        except ValueError:
            # Check if selection is Team Code
            team_code_upper = choice.upper()
            if team_code_upper in combined_teams:
                selected_code = team_code_upper
                selected_name = combined_teams[team_code_upper]
                
        if not selected_code:
            print("[Error] Invalid selection. Please enter a valid number or team code.")
            continue
            
        print(f"\n[Info] Querying live team stats for {selected_name} ({selected_code}) from iplt20.com...")
        stats = fetch_live_team_stats(selected_code)
        
        if stats:
            print_team_stats_card(selected_code, selected_name, stats)
        else:
            print(f"[Error] Could not retrieve team stats for {selected_name}.")

if __name__ == "__main__":
    main()
