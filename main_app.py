from flask import Flask, render_template, request, jsonify
import json
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from modules.matchup_simulator.data_engine import IPLDataEngine
from modules.ground_analysis.ground_engine import IPLVenueEngine
from modules.fantasy_optimizer.fantasy_engine import IPLFantasyEngine

app = Flask(__name__)

# Paths
DATABASE_FILE = "ipl_players_data.json"
CACHE_FILE = "player_bios.json"
STATS_API_URL = "https://www.iplt20.com/comparison/show-player-stats"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

IPL_STANDINGS = [
    {"name": "Royal Challengers Bengaluru", "code": "RCB", "played": 14, "won": 9, "lost": 5, "no_result": 0, "points": 18, "nrr": "+0.783", "color": "#ec1c24"},
    {"name": "Gujarat Titans", "code": "GT", "played": 14, "won": 9, "lost": 5, "no_result": 0, "points": 18, "nrr": "+0.695", "color": "#0b1e36"},
    {"name": "Sunrisers Hyderabad", "code": "SRH", "played": 14, "won": 9, "lost": 5, "no_result": 0, "points": 18, "nrr": "+0.524", "color": "#f26522"},
    {"name": "Rajasthan Royals", "code": "RR", "played": 14, "won": 8, "lost": 6, "no_result": 0, "points": 16, "nrr": "+0.189", "color": "#ea1a85"},
    {"name": "Punjab Kings", "code": "PBKS", "played": 14, "won": 7, "lost": 6, "no_result": 1, "points": 15, "nrr": "+0.309", "color": "#dd1f26"},
    {"name": "Delhi Capitals", "code": "DC", "played": 14, "won": 7, "lost": 7, "no_result": 0, "points": 14, "nrr": "-0.651", "color": "#0078bc"},
    {"name": "Kolkata Knight Riders", "code": "KKR", "played": 14, "won": 6, "lost": 7, "no_result": 1, "points": 13, "nrr": "-0.147", "color": "#3a225d"},
    {"name": "Chennai Super Kings", "code": "CSK", "played": 14, "won": 6, "lost": 8, "no_result": 0, "points": 12, "nrr": "-0.345", "color": "#fdb913"},
    {"name": "Mumbai Indians", "code": "MI", "played": 14, "won": 4, "lost": 10, "no_result": 0, "points": 8, "nrr": "-0.584", "color": "#004ba0"},
    {"name": "Lucknow Super Giants", "code": "LSG", "played": 14, "won": 4, "lost": 10, "no_result": 0, "points": 8, "nrr": "-0.740", "color": "#005780"}
]

ORANGE_CAP_LEADERS = [
    {"name": "Sai Sudharsan", "team": "GT", "runs": 638, "avg": "49.08", "sr": "157.92"},
    {"name": "Shubman Gill", "team": "GT", "runs": 616, "avg": "47.38", "sr": "161.67"},
    {"name": "Heinrich Klaasen", "team": "SRH", "runs": 606, "avg": "50.50", "sr": "159.47"},
    {"name": "KL Rahul", "team": "DC", "runs": 593, "avg": "45.61", "sr": "174.41"},
    {"name": "Vaibhav Sooryavanshi", "team": "RR", "runs": 583, "avg": "41.64", "sr": "232.27"}
]

PURPLE_CAP_LEADERS = [
    {"name": "Bhuvneshwar Kumar", "team": "RCB", "wickets": 24, "econ": "8.07", "bbi": "4/23"},
    {"name": "Kagiso Rabada", "team": "GT", "wickets": 24, "econ": "9.19", "bbi": "3/25"},
    {"name": "Jofra Archer", "team": "RR", "wickets": 21, "econ": "8.77", "bbi": "3/17"},
    {"name": "Anshul Kamboj", "team": "CSK", "wickets": 21, "econ": "10.53", "bbi": "3/22"},
    {"name": "Rashid Khan", "team": "GT", "wickets": 19, "econ": "8.72", "bbi": "4/33"}
]

# Global Data Cache
player_bios = {}
player_roster = []

def init_app_databases():
    """Initializes local JSON database structures and loads configurations."""
    global player_bios, player_roster
    print("[Flask Dashboard] Pre-loading local databases...")
    
    # 1. Load Bios Cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                player_bios = json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to read bios cache: {e}.")
            
    # 2. Load players roster (autocomplete search index)
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
            print(f"[Flask Dashboard] Roster indexed successfully! Total: {len(player_roster)} players.")
        except Exception as e:
            print(f"[Error] Failed to load roster: {e}")
    else:
        print(f"[Warning] Roster file '{DATABASE_FILE}' not found.")

def save_bios_cache():
    """Saves player bios cache locally."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(player_bios, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Error] Failed to write bios cache: {e}")

def resolve_player_bio(player_id, player_name, team_code):
    """Looks up a player's batting stance and bowling style in the cache or scrapes it live."""
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
                bat_style = "Right Hand Bat"
                bowl_style = "N/A"
                
                bio_match = re.search(r'<div class="details">\s*<span>([^<]+)</span>\s*<span>([^<]+)</span>\s*<span>([^<]*)</span>', bio_html, re.DOTALL)
                if bio_match:
                    dob = bio_match.group(1).strip()
                    bat_style = bio_match.group(2).strip()
                    bowl_style = bio_match.group(3).strip() if bio_match.group(3) else "N/A"
                
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
        
    return {
        "name": player_name,
        "dob": "N/A",
        "bat_style": "Right Hand Bat",
        "bowl_style": "Right Arm Medium"
    }

# Initialize data engines
init_app_databases()
data_engine = IPLDataEngine()
venue_engine = IPLVenueEngine()
fantasy_engine = IPLFantasyEngine(data_engine=data_engine, venue_engine=venue_engine)

@app.route('/')
def home():
    """Renders the master IPL Season Dashboard page."""
    return render_template('dashboard.html', 
                           standings=IPL_STANDINGS, 
                           orange_cap=ORANGE_CAP_LEADERS, 
                           purple_cap=PURPLE_CAP_LEADERS)

@app.route('/simulator')
def simulator():
    """Renders the GameSense AI Batter vs. Bowler matchup simulator page."""
    return render_template('simulator.html')

@app.route('/ground-analysis')
def ground_analysis():
    """Renders the Pitch Profiler & Toss Strategist page."""
    venues = venue_engine.get_all_venues()
    return render_template('ground_analysis.html', venues=venues)

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
        
    batter_profile = None
    bowler_profile = None
    
    for p in player_roster:
        if p["name"].lower() == batter_name.lower():
            batter_profile = p
        if p["name"].lower() == bowler_name.lower():
            bowler_profile = p
            
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
        
    batter_bio = resolve_player_bio(batter_profile["id"], batter_profile["name"], batter_profile["team_code"])
    bowler_bio = resolve_player_bio(bowler_profile["id"], bowler_profile["name"], bowler_profile["team_code"])
    
    batter_career = data_engine.get_all_matches_for_stats(batter_name=batter_profile["name"])
    bowler_career = data_engine.get_all_matches_for_stats(bowler_name=bowler_profile["name"])
    
    h2h = data_engine.get_head_to_head(batter_profile["name"], bowler_profile["name"])
    
    batter_stance = batter_bio.get("bat_style", "Right Hand Bat")
    bowler_style = bowler_bio.get("bowl_style", "Right Arm Fast")
    
    bowler_style_clean = bowler_style.lower()
    is_pace = any(t in bowler_style_clean for t in ["fast", "medium", "seam", "swing", "pace"])
    style_label = "Pace" if is_pace else "Spin"
    if "legbreak" in bowler_style_clean or "wrist" in bowler_style_clean or "chinaman" in bowler_style_clean:
        style_label = "Wrist Spin (Legbreak)"
    elif "offbreak" in bowler_style_clean or "finger" in bowler_style_clean or "orthodox" in bowler_style_clean:
        style_label = "Finger Spin (Offbreak)"
        
    matching_bowler_names = []
    for bid, binfo in player_bios.items():
        bstyle = binfo.get("bowl_style", "").lower()
        if style_label == "Pace" and any(t in bstyle for t in ["fast", "medium", "seam", "swing", "pace"]):
            matching_bowler_names.append(binfo.get("name", bid))
        elif style_label == "Wrist Spin (Legbreak)" and any(t in bstyle for t in ["legbreak", "wrist", "chinaman"]):
            matching_bowler_names.append(binfo.get("name", bid))
        elif style_label == "Finger Spin (Offbreak)" and any(t in bstyle for t in ["offbreak", "finger", "orthodox"]):
            matching_bowler_names.append(binfo.get("name", bid))
            
    arch_batter_runs = 0
    arch_batter_balls = 0
    arch_batter_dismissals = 0
    arch_batter_fours = 0
    arch_batter_sixes = 0
    
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

@app.route('/api/venue-stats')
def get_api_venue_stats():
    """Exposes REST API endpoint for normalized venue intelligence calculations."""
    venue_name = request.args.get('venue')
    if not venue_name:
        return jsonify({"status": False, "error": "Venue name parameter is required."}), 400
    stats = venue_engine.get_venue_stats(venue_name)
    return jsonify(stats)

@app.route('/fantasy-optimizer')
def fantasy_optimizer():
    """Renders the AI Fantasy Optimizer (Squad Builder) page."""
    teams = [
        {"name": "Royal Challengers Bengaluru", "code": "RCB"},
        {"name": "Gujarat Titans", "code": "GT"},
        {"name": "Sunrisers Hyderabad", "code": "SRH"},
        {"name": "Rajasthan Royals", "code": "RR"},
        {"name": "Punjab Kings", "code": "PBKS"},
        {"name": "Delhi Capitals", "code": "DC"},
        {"name": "Kolkata Knight Riders", "code": "KKR"},
        {"name": "Chennai Super Kings", "code": "CSK"},
        {"name": "Mumbai Indians", "code": "MI"},
        {"name": "Lucknow Super Giants", "code": "LSG"}
    ]
    venues = venue_engine.get_all_venues()
    return render_template('fantasy_optimizer.html', teams=teams, venues=venues)

@app.route('/api/fantasy-squad')
def get_api_fantasy_squad():
    """Exposes REST API endpoint to generate statistically optimal 11-player fantasy squad."""
    team_a = request.args.get('team_a')
    team_b = request.args.get('team_b')
    venue = request.args.get('venue', 'Wankhede Stadium, Mumbai')
    
    if not team_a or not team_b:
        return jsonify({"status": False, "error": "Both team_a and team_b parameters are required."}), 400
        
    if team_a == team_b:
        return jsonify({"status": False, "error": "Please select two different teams."}), 400
        
    squad_data = fantasy_engine.optimize_squad(team_a, team_b, venue)
    return jsonify(squad_data)

@app.route('/api/impact-player')
def get_api_impact_player():
    """Exposes REST API endpoint for tactical innings break Impact Player suggestions."""
    team_bat = request.args.get('team_batting')
    team_bowl = request.args.get('team_bowling')
    wickets = int(request.args.get('wickets', 0))
    score = int(request.args.get('score', 0))
    innings = int(request.args.get('innings', 1))
    opponent_spin = int(request.args.get('opponent_spin', 0))
    
    if not team_bat or not team_bowl:
        return jsonify({"status": False, "error": "Both team_batting and team_bowling parameters are required."}), 400
        
    suggestion = fantasy_engine.suggest_impact_player(
        team_batting_code=team_bat,
        team_bowling_code=team_bowl,
        wickets=wickets,
        score=score,
        innings_num=innings,
        opponent_spin_count=opponent_spin
    )
    return jsonify(suggestion)

@app.route('/api/player-prediction')
def get_api_player_prediction():
    """Exposes REST API endpoint for matchup-aware player performance predictions."""
    player_id = request.args.get('player_id')
    opponent = request.args.get('opponent')
    venue = request.args.get('venue')
    
    if not player_id or not opponent or not venue:
        return jsonify({"status": False, "error": "Player ID, opponent, and venue parameters are required."}), 400
        
    prediction = fantasy_engine.predict_player_performance(player_id, opponent, venue)
    return jsonify(prediction)

if __name__ == '__main__':
    app.run(debug=True, port=5005)
