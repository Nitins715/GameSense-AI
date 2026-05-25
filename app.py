from flask import Flask, render_template, request, jsonify
import json
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from data_engine import IPLDataEngine

app = Flask(__name__)

# Paths
DATABASE_FILE = "ipl_players_data.json"
CACHE_FILE = "player_bios.json"
STATS_API_URL = "https://www.iplt20.com/comparison/show-player-stats"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

# Preloaded bios to seed the cache with popular players for instant archetype results
SEED_PLAYER_BIOS = {
    "virat-kohli": {"name": "Virat Kohli", "dob": "05-11-1988", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Medium"},
    "ms-dhoni": {"name": "MS Dhoni", "dob": "07-07-1981", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Medium"},
    "rohit-sharma": {"name": "Rohit Sharma", "dob": "30-04-1987", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Offbreak"},
    "jj-bumrah": {"name": "Jasprit Bumrah", "dob": "06-12-1993", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast"},
    "yuzvendra-chahal": {"name": "Yuzvendra Chahal", "dob": "23-07-1990", "bat_style": "Right Hand Bat", "bowl_style": "Legbreak"},
    "rashid-khan": {"name": "Rashid Khan", "dob": "20-09-1998", "bat_style": "Right Hand Bat", "bowl_style": "Legbreak"},
    "sunil-narine": {"name": "Sunil Narine", "dob": "26-05-1988", "bat_style": "Left Hand Bat", "bowl_style": "Right Arm Offbreak"},
    "trent-boult": {"name": "Trent Boult", "dob": "22-07-1989", "bat_style": "Right Hand Bat", "bowl_style": "Left Arm Fast"},
    "ravindra-jadeja": {"name": "Ravindra Jadeja", "dob": "06-12-1988", "bat_style": "Left Hand Bat", "bowl_style": "Left Arm Orthodox"},
    "r-ashwin": {"name": "Ravichandran Ashwin", "dob": "17-09-1986", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Offbreak"},
    "glenn-maxwell": {"name": "Glenn Maxwell", "dob": "14-10-1988", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Offbreak"},
    "hardik-pandya": {"name": "Hardik Pandya", "dob": "11-10-1993", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast Medium"},
    "kl-rahul": {"name": "KL Rahul", "dob": "18-04-1992", "bat_style": "Right Hand Bat", "bowl_style": "N/A"},
    "shubman-gill": {"name": "Shubman Gill", "dob": "08-09-1999", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Offbreak"},
    "rishabh-pant": {"name": "Rishabh Pant", "dob": "04-10-1997", "bat_style": "Left Hand Bat", "bowl_style": "N/A"},
    "shreyas-iyer": {"name": "Shreyas Iyer", "dob": "06-12-1994", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Legbreak"},
    "suryakumar-yadav": {"name": "Suryakumar Yadav", "dob": "14-09-1990", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Medium"},
    "ab-de-villiers": {"name": "AB de Villiers", "dob": "17-02-1984", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Medium"},
    "chris-gayle": {"name": "Chris Gayle", "dob": "21-09-1979", "bat_style": "Left Hand Bat", "bowl_style": "Right Arm Offbreak"},
    "david-warner": {"name": "David Warner", "dob": "27-10-1986", "bat_style": "Left Hand Bat", "bowl_style": "Right Arm Legbreak"},
    "jos-buttler": {"name": "Jos Buttler", "dob": "08-09-1990", "bat_style": "Right Hand Bat", "bowl_style": "N/A"},
    "sanju-samson": {"name": "Sanju Samson", "dob": "11-11-1994", "bat_style": "Right Hand Bat", "bowl_style": "N/A"},
    "andre-russell": {"name": "Andre Russell", "dob": "29-04-1988", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast"},
    "axar-patel": {"name": "Axar Patel", "dob": "20-01-1994", "bat_style": "Left Hand Bat", "bowl_style": "Left Arm Orthodox"},
    "kuldeep-yadav": {"name": "Kuldeep Yadav", "dob": "14-12-1994", "bat_style": "Left Hand Bat", "bowl_style": "Left Arm Chinaman"},
    "mohammed-shami": {"name": "Mohammed Shami", "dob": "03-09-1990", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast"},
    "bhuvneshwar-kumar": {"name": "Bhuvneshwar Kumar", "dob": "05-02-1990", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast Medium"},
    "kagiso-rabada": {"name": "Kagiso Rabada", "dob": "25-05-1995", "bat_style": "Left Hand Bat", "bowl_style": "Right Arm Fast"},
    "arshdeep-singh": {"name": "Arshdeep Singh", "dob": "05-02-1999", "bat_style": "Left Hand Bat", "bowl_style": "Left Arm Fast Medium"},
    "harshal-patel": {"name": "Harshal Patel", "dob": "23-11-1990", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast Medium"},
    "mohammad-siraj": {"name": "Mohammed Siraj", "dob": "13-03-1994", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast"},
    "mitchell-starc": {"name": "Mitchell Starc", "dob": "30-01-1990", "bat_style": "Left Hand Bat", "bowl_style": "Left Arm Fast"},
    "pat-cummins": {"name": "Pat Cummins", "dob": "08-05-1993", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast"},
    "t-natarajan": {"name": "T Natarajan", "dob": "27-05-1991", "bat_style": "Left Hand Bat", "bowl_style": "Left Arm Fast Medium"},
    "sandeep-sharma": {"name": "Sandeep Sharma", "dob": "18-05-1993", "bat_style": "Right Hand Bat", "bowl_style": "Right Arm Fast Medium"},
    "varun-chakaravarthy": {"name": "Varun Chakaravarthy", "dob": "29-08-1991", "bat_style": "Right Hand Bat", "bowl_style": "Legbreak Googly"}
}

# Global Data Cache
player_bios = {}
player_roster = []

def init_app_databases():
    """Initializes local JSON database structures and loads configurations."""
    global player_bios, player_roster
    print("[Flask] Pre-loading local databases...")
    
    # 1. Load Bios Cache or initialize from seed
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                player_bios = json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to read bios cache: {e}. Seeding new cache.")
            player_bios = SEED_PLAYER_BIOS.copy()
    else:
        player_bios = SEED_PLAYER_BIOS.copy()
        save_bios_cache()
        
    # 2. Load players roster (useful for autocomplete names and IDs)
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                db_data = json.load(f)
                
            for team_name, team_data in db_data.get("teams", {}).items():
                team_code = team_data.get("code")
                for category, players in team_data.get("categories", {}).items():
                    for p in players:
                        player_roster.append({
                            "id": p["id"],
                            "name": p["name"],
                            "team": team_name,
                            "team_code": team_code,
                            "image_url": p["image_url"],
                            "category": category
                        })
            print(f"[Flask] Roster indexed successfully! Total: {len(player_roster)} players.")
        except Exception as e:
            print(f"[Error] Failed to load roster: {e}")
    else:
        print(f"[Warning] Roster file '{DATABASE_FILE}' not found. Please scrape roster first.")

def save_bios_cache():
    """Saves player bios cache locally."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(player_bios, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Error] Failed to write bios cache: {e}")

def resolve_player_bio(player_id, player_name, team_code):
    """
    Looks up a player's batting stance and bowling style in the cache.
    If missing, scrapes it live from iplt20.com on-demand and caches it.
    """
    global player_bios
    
    if player_id in player_bios:
        return player_bios[player_id]
        
    print(f"[Scraper] Live fetching bio details for '{player_name}' ({team_code})...")
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
            
            if data.get('status'):
                bio_html = data.get("player_one", "")
                dob = "N/A"
                bat_style = "Right Hand Bat" # Default
                bowl_style = "N/A"
                
                # Regex extract details
                bio_match = re.search(r'<div class="details">\s*<span>([^<]+)</span>\s*<span>([^<]+)</span>\s*<span>([^<]*)</span>', bio_html, re.DOTALL)
                if bio_match:
                    dob = bio_match.group(1).strip()
                    bat_style = bio_match.group(2).strip()
                    bowl_style = bio_match.group(3).strip() if bio_match.group(3) else "N/A"
                
                # Cache and save
                player_bios[player_id] = {
                    "name": player_name,
                    "dob": dob,
                    "bat_style": bat_style,
                    "bowl_style": bowl_style
                }
                save_bios_cache()
                return player_bios[player_id]
                
    except Exception as e:
        print(f"[Error] Failed to live scrape bio: {e}")
        
    # Fallback default if scrape fails
    return {
        "name": player_name,
        "dob": "N/A",
        "bat_style": "Right Hand Bat",
        "bowl_style": "Right Arm Medium"
    }

# Initialize data engine
init_app_databases()
data_engine = IPLDataEngine()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/players')
def get_players():
    """Serves the complete roster for search autocomplete suggestions."""
    return jsonify(player_roster)

@app.route('/api/matchup')
def get_matchup():
    """Calculates and returns complete simulated matchup analytics."""
    batter_name = request.args.get('batter')
    bowler_name = request.args.get('bowler')
    
    if not batter_name or not bowler_name:
        return jsonify({"status": False, "error": "Batter and Bowler names are required."}), 400
        
    # 1. Resolve players details from roster database
    batter_profile = None
    bowler_profile = None
    
    for p in player_roster:
        if p["name"].lower() == batter_name.lower():
            batter_profile = p
        if p["name"].lower() == bowler_name.lower():
            bowler_profile = p
            
    # Fallback structures if player is not registered in the 2026 rosters (historical player)
    if not batter_profile:
        batter_profile = {
            "id": batter_name.lower().replace(" ", "-"),
            "name": batter_name,
            "team": "Historical Legend",
            "team_code": "LEG",
            "image_url": "https://documents.iplt20.com/ipl/assets/images/Default-Men.png",
            "category": "Batsman"
        }
    if not bowler_profile:
        bowler_profile = {
            "id": bowler_name.lower().replace(" ", "-"),
            "name": bowler_name,
            "team": "Historical Legend",
            "team_code": "LEG",
            "image_url": "https://documents.iplt20.com/ipl/assets/images/Default-Men.png",
            "category": "Bowler"
        }
        
    # 2. Retrieve detailed bios (dob, stances, styles) from local cache or scraper
    batter_bio = resolve_player_bio(batter_profile["id"], batter_profile["name"], batter_profile["team_code"])
    bowler_bio = resolve_player_bio(bowler_profile["id"], bowler_profile["name"], bowler_profile["team_code"])
    
    # 3. Compute overall career stats
    batter_career = data_engine.get_all_matches_for_stats(batter_name=batter_profile["name"])
    bowler_career = data_engine.get_all_matches_for_stats(bowler_name=bowler_profile["name"])
    
    # 4. Compute direct head-to-head stats
    h2h = data_engine.get_head_to_head(batter_profile["name"], bowler_profile["name"])
    
    # 5. Compute Skill vs. Style Archetype stats
    # Stance: batter_bio['bat_style'] (e.g. "Right Hand Bat")
    # Style: bowler_bio['bowl_style'] (e.g. "Legbreak")
    batter_stance = batter_bio.get("bat_style", "Right Hand Bat")
    bowler_style = bowler_bio.get("bowl_style", "Right Arm Fast")
    
    # Let's clean the style label for grouping (e.g. group Fast, Fast Medium, Express under Fast/Pace)
    # Styles to search: fast/pace vs. spin
    bowler_style_clean = bowler_style.lower()
    is_pace = any(t in bowler_style_clean for t in ["fast", "medium", "seam", "swing", "pace"])
    style_label = "Pace" if is_pace else "Spin"
    if "legbreak" in bowler_style_clean or "wrist" in bowler_style_clean or "chinaman" in bowler_style_clean:
        style_label = "Wrist Spin (Legbreak)"
    elif "offbreak" in bowler_style_clean or "finger" in bowler_style_clean or "orthodox" in bowler_style_clean:
        style_label = "Finger Spin (Offbreak)"
        
    # Batter vs style archetype calculations (Find all deliveries where batter faces bowlers of this style)
    # To map other bowlers to style, we check our loaded player_bios cache!
    matching_bowler_names = []
    for bid, binfo in player_bios.items():
        bstyle = binfo.get("bowl_style", "").lower()
        if style_label == "Pace" and any(t in bstyle for t in ["fast", "medium", "seam", "swing", "pace"]):
            matching_bowler_names.append(binfo.get("name", bid))
        elif style_label == "Wrist Spin (Legbreak)" and any(t in bstyle for t in ["legbreak", "wrist", "chinaman"]):
            matching_bowler_names.append(binfo.get("name", bid))
        elif style_label == "Finger Spin (Offbreak)" and any(t in bstyle for t in ["offbreak", "finger", "orthodox"]):
            matching_bowler_names.append(binfo.get("name", bid))
            
    # Calculate batter vs this style
    arch_batter_runs = 0
    arch_batter_balls = 0
    arch_batter_dismissals = 0
    arch_batter_fours = 0
    arch_batter_sixes = 0
    
    # Filter engine deliveries
    for d in data_engine.deliveries:
        if d["batter"] == batter_profile["name"] and d["bowler"] in matching_bowler_names and d["bowler"] != bowler_profile["name"]:
            if d["extras_type"] != "wides":
                arch_batter_balls += 1
            arch_batter_runs += d["runs_batter"]
            if d["runs_batter"] == 4: arch_batter_fours += 1
            elif d["runs_batter"] == 6: arch_batter_sixes += 1
            if d["is_wicket"] and d["wicket_player_out"] == batter_profile["name"]:
                if d["wicket_kind"] not in ["run out", "retired hurt"]:
                    arch_batter_dismissals += 1
                    
    arch_batter_sr = (arch_batter_runs / arch_batter_balls * 100) if arch_batter_balls > 0 else 0
    arch_batter_avg = (arch_batter_runs / arch_batter_dismissals) if arch_batter_dismissals > 0 else arch_batter_runs
    
    # Bowler vs batter stance archetype calculations (Find all deliveries where bowler bowls to batters of this stance)
    matching_batter_names = []
    for pid, pinfo in player_bios.items():
        if pinfo.get("bat_style", "").lower() == batter_stance.lower():
            matching_batter_names.append(pinfo.get("name", pid))
            
    arch_bowler_runs = 0
    arch_bowler_balls = 0
    arch_bowler_wickets = 0
    arch_bowler_fours = 0
    arch_bowler_sixes = 0
    
    for d in data_engine.deliveries:
        if d["bowler"] == bowler_profile["name"] and d["batter"] in matching_batter_names and d["batter"] != batter_profile["name"]:
            if d["extras_type"] not in ["wides", "noballs"]:
                arch_bowler_balls += 1
            if d["extras_type"] not in ["legbyes", "byes"]:
                arch_bowler_runs += d["runs_batter"] + d["runs_extras"]
            if d["runs_batter"] == 4: arch_bowler_fours += 1
            elif d["runs_batter"] == 6: arch_bowler_sixes += 1
            if d["is_wicket"]:
                if d["wicket_kind"] not in ["run out", "retired hurt"]:
                    arch_bowler_wickets += 1
                    
    arch_bowler_econ = (arch_bowler_runs / (arch_bowler_balls / 6)) if arch_bowler_balls > 0 else 0
    arch_bowler_sr = (arch_bowler_balls / arch_bowler_wickets) if arch_bowler_wickets > 0 else 0
    
    # 6. Aggregate Response JSON
    response_data = {
        "status": True,
        "batter": {
            "id": batter_profile["id"],
            "name": batter_profile["name"],
            "team": batter_profile["team"],
            "team_code": batter_profile["team_code"],
            "image_url": batter_profile["image_url"],
            "category": batter_profile["category"],
            "dob": batter_bio["dob"],
            "stance": batter_stance,
            "career": batter_career
        },
        "bowler": {
            "id": bowler_profile["id"],
            "name": bowler_profile["name"],
            "team": bowler_profile["team"],
            "team_code": bowler_profile["team_code"],
            "image_url": bowler_profile["image_url"],
            "category": bowler_profile["category"],
            "dob": bowler_bio["dob"],
            "style": bowler_style,
            "career": bowler_career
        },
        "head_to_head": h2h,
        "archetypes": {
            "batter_vs_style": {
                "style": style_label,
                "runs": arch_batter_runs,
                "balls": arch_batter_balls,
                "dismissals": arch_batter_dismissals,
                "average": round(arch_batter_avg, 2),
                "strike_rate": round(arch_batter_sr, 2),
                "fours": arch_batter_fours,
                "sixes": arch_batter_sixes
            },
            "bowler_vs_stance": {
                "stance": batter_stance,
                "runs_conceded": arch_bowler_runs,
                "balls_bowled": arch_bowler_balls,
                "wickets": arch_bowler_wickets,
                "economy": round(arch_bowler_econ, 2),
                "strike_rate": round(arch_bowler_sr, 2),
                "fours": arch_bowler_fours,
                "sixes": arch_bowler_sixes
            }
        }
    }
    
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, port=5005)
