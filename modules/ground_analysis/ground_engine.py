import os
import glob
import json
import time
from datetime import datetime

class IPLVenueEngine:
    # Top bowler classification fallbacks to guarantee accuracy for major active bowlers
    BOWLER_STYLE_FALLBACKS = {
        "sl malinga": "Right Arm Fast",
        "sp narine": "Right Arm Offbreak",
        "ys chahal": "Legbreak",
        "b kumar": "Right Arm Fast Medium",
        "jj bumrah": "Right Arm Fast",
        "ra jadeja": "Left Arm Orthodox",
        "r ashwin": "Right Arm Offbreak",
        "harbhajan singh": "Right Arm Offbreak",
        "pp chawla": "Legbreak",
        "dj bravo": "Right Arm Fast Medium",
        "a mishra": "Legbreak",
        "ut yadav": "Right Arm Fast",
        "ds kulkarni": "Right Arm Medium Fast",
        "z khan": "Left Arm Fast Medium",
        "sandeep sharma": "Right Arm Fast Medium",
        "mohit sharma": "Right Arm Fast Medium",
        "rashid khan": "Legbreak",
        "arshdeep singh": "Left Arm Fast Medium",
        "harshal patel": "Right Arm Fast Medium",
        "t natarajan": "Left Arm Fast Medium",
        "mohammad siraj": "Right Arm Fast",
        "mohammed shami": "Right Arm Fast",
        "pat cummins": "Right Arm Fast",
        "mitchell starc": "Left Arm Fast",
        "varun chakaravarthy": "Legbreak Googly",
        "r sharma": "Right Arm Offbreak"
    }

    def __init__(self, data_dir="ipl_json_data"):
        self.data_dir = data_dir
        self.player_bios = {}
        self.venue_stats = {}
        self.load_bios()
        self.load_venue_data()

    def load_bios(self):
        """Loads players bios from local cache to map bowler playing styles."""
        if os.path.exists("player_bios.json"):
            try:
                with open("player_bios.json", "r", encoding="utf-8") as f:
                    self.player_bios = json.load(f)
                print(f"[Venue Engine] Loaded {len(self.player_bios)} player bios for classification.")
            except Exception as e:
                print(f"[Warning] Failed to read bios cache in Venue Engine: {e}")

    def normalize_venue(self, venue_name):
        """
        Merges name variations of the same stadium to prevent data dilution.
        """
        if not venue_name:
            return "Unknown Venue"
        
        val = venue_name.lower().strip()
        
        if "wankhede" in val:
            return "Wankhede Stadium, Mumbai"
        elif "chinnaswamy" in val:
            return "M. Chinnaswamy Stadium, Bengaluru"
        elif "eden gardens" in val:
            return "Eden Gardens, Kolkata"
        elif "chidambaram" in val or "chepauk" in val:
            return "MA Chidambaram Stadium, Chennai"
        elif "rajiv gandhi" in val or "uppal" in val:
            return "Rajiv Gandhi International Stadium, Hyderabad"
        elif "arun jaitley" in val or "feroz shah" in val or "kotla" in val:
            return "Arun Jaitley Stadium, Delhi"
        elif "sawai mansingh" in val:
            return "Sawai Mansingh Stadium, Jaipur"
        elif "narendra modi" in val or "motera" in val or "sardar patel" in val:
            return "Narendra Modi Stadium, Ahmedabad"
        elif "bindra" in val or "mohali" in val:
            return "IS Bindra Stadium, Mohali"
        elif "maharashtra cricket association" in val or "mca stadium" in val or "subrata roy" in val:
            return "MCA Stadium, Pune"
        elif "dubai" in val:
            return "Dubai International Cricket Stadium"
        elif "abu dhabi" in val or "sheikh zayed" in val:
            return "Sheikh Zayed Stadium, Abu Dhabi"
        elif "sharjah" in val:
            return "Sharjah Cricket Stadium"
        elif "barabati" in val:
            return "Barabati Stadium, Cuttack"
        elif "holkar" in val:
            return "Holkar Cricket Stadium, Indore"
        elif "saurashtra" in val:
            return "Saurashtra Cricket Association Stadium, Rajkot"
        elif "dr. y.s. rajasekhara" in val or "visakhapatnam" in val or "vizag" in val:
            return "Dr. Y.S. Rajasekhara Reddy Stadium, Visakhapatnam"
        elif "himachal pradesh" in val or "dharamsala" in val:
            return "HPCA Stadium, Dharamshala"
        elif "lucknow" in val or "ekana" in val:
            return "Ekana Cricket Stadium, Lucknow"
        elif "green park" in val:
            return "Green Park Stadium, Kanpur"
        elif "brabourne" in val:
            return "Brabourne Stadium, Mumbai"
        elif "dy patil" in val:
            return "DY Patil Stadium, Navi Mumbai"
        
        return venue_name.title()

    def get_day_night(self, date_str, match_id):
        """
        Determines Day vs. Night matches. Monday-Friday are classified as Night.
        Saturday & Sunday are split between afternoon (Day) and evening (Night).
        """
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = dt.weekday() # 0 = Monday, 6 = Sunday
            if weekday < 5: # Monday to Friday
                return "Night"
            else:
                # Deterministic split based on odd/even match ID
                return "Day" if int(match_id) % 2 == 0 else "Night"
        except Exception:
            return "Night"

    def find_bowler_style(self, bowler_name):
        """Fuzzy matches bowler names in the player bios cache to find their bowling style."""
        b_clean = bowler_name.lower().strip()
        
        # Check explicit fallback map first
        if b_clean in self.BOWLER_STYLE_FALLBACKS:
            return self.BOWLER_STYLE_FALLBACKS[b_clean]

        for pid, bio in self.player_bios.items():
            bio_name = bio.get("name", "").lower()
            cric_parts = b_clean.split()
            bio_parts = bio_name.split()
            
            if cric_parts and bio_parts:
                cric_last = cric_parts[-1]
                bio_last = bio_parts[-1]
                if cric_last == bio_last:
                    cric_init = cric_parts[0][0]
                    bio_init = bio_parts[0][0]
                    if cric_init == bio_init:
                        return bio.get("bowl_style", "N/A")
                        
        return "N/A"

    def classify_bowler_type(self, style_str, bowler_name):
        """Categorizes bowling style string into Pace or Spin."""
        style = style_str.lower()
        
        # Check name prefix fallback
        b_clean = bowler_name.lower().strip()
        if b_clean in self.BOWLER_STYLE_FALLBACKS:
            style = self.BOWLER_STYLE_FALLBACKS[b_clean].lower()
            
        if any(k in style for k in ["fast", "medium", "seam", "swing", "pace", "seamer"]):
            return "Pace"
        elif any(k in style for k in ["spin", "legbreak", "offbreak", "orthodox", "chinaman", "slow", "googly", "break"]):
            return "Spin"
            
        return "Pace"

    def load_venue_data(self):
        """Loads and compiles raw venue stats from all match JSON files."""
        start_time = time.time()
        match_files = glob.glob(os.path.join(self.data_dir, "[0-9]*.json"))
        
        print(f"[Venue Engine] Pre-parsing {len(match_files)} match files for venue intelligence...")
        
        for file_path in match_files:
            match_id = os.path.basename(file_path).split('.')[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    match_data = json.load(f)
                    
                info = match_data.get("info", {})
                raw_venue = info.get("venue")
                if not raw_venue:
                    continue
                    
                venue = self.normalize_venue(raw_venue)
                
                # Retrieve match date
                dates = info.get("dates", ["Unknown Date"])
                match_date = dates[0]
                day_night = self.get_day_night(match_date, match_id)
                
                # Retrieve toss decision
                toss = info.get("toss", {})
                toss_winner = toss.get("winner")
                toss_decision = toss.get("decision") # field or bat
                
                # Initialize venue stats block if not already created
                if venue not in self.venue_stats:
                    self.venue_stats[venue] = {
                        "name": venue,
                        "matches_count": 0,
                        "completed_matches": 0,
                        "bat_first_wins": 0,
                        "chase_wins": 0,
                        "toss_winner_wins": 0,
                        "toss_decisions": {"field": 0, "bat": 0},
                        "total_1st_runs": 0,
                        "total_1st_wickets": 0,
                        "total_1st_overs": 0,
                        "total_2nd_runs": 0,
                        "total_2nd_wickets": 0,
                        "total_2nd_overs": 0,
                        "day_matches": 0,
                        "night_matches": 0,
                        "day_chase_wins": 0,
                        "day_bat_first_wins": 0,
                        "night_chase_wins": 0,
                        "night_bat_first_wins": 0,
                        # Pace vs. Spin details
                        "pace_wickets": 0,
                        "spin_wickets": 0,
                        "pace_runs": 0,
                        "pace_balls": 0,
                        "spin_runs": 0,
                        "spin_balls": 0
                    }
                    
                v = self.venue_stats[venue]
                v["matches_count"] += 1
                
                if day_night == "Day":
                    v["day_matches"] += 1
                else:
                    v["night_matches"] += 1
                    
                if toss_decision:
                    v["toss_decisions"][toss_decision] += 1
                    
                innings = match_data.get("innings", [])
                if len(innings) < 1:
                    continue
                    
                first_inn = innings[0]
                first_inn_team = first_inn.get("team")
                
                # Determine outcome
                outcome = info.get("outcome", {})
                winner = outcome.get("winner")
                
                if winner:
                    v["completed_matches"] += 1
                    if winner == first_inn_team:
                        v["bat_first_wins"] += 1
                        if day_night == "Day":
                            v["day_bat_first_wins"] += 1
                        else:
                            v["night_bat_first_wins"] += 1
                    else:
                        v["chase_wins"] += 1
                        if day_night == "Day":
                            v["day_chase_wins"] += 1
                        else:
                            v["night_chase_wins"] += 1
                            
                    if winner == toss_winner:
                        v["toss_winner_wins"] += 1
                
                # Delivery-level aggregation for innings scores & Pace vs. Spin splits
                for i_idx, inning in enumerate(innings):
                    is_first_innings = (i_idx == 0)
                    overs = inning.get("overs", [])
                    
                    for over_data in overs:
                        deliveries = over_data.get("deliveries", [])
                        for d in deliveries:
                            bowler = d.get("bowler")
                            runs = d.get("runs", {})
                            runs_bat = runs.get("batter", 0)
                            runs_ext = runs.get("extras", 0)
                            runs_tot = runs.get("total", 0)
                            ext_type = d.get("extras", {})
                            
                            # Standard Innings stats
                            if is_first_innings:
                                if not ext_type or "wides" not in ext_type:
                                    v["total_1st_overs"] += 1
                                v["total_1st_runs"] += runs_tot
                            else:
                                if not ext_type or "wides" not in ext_type:
                                    v["total_2nd_overs"] += 1
                                v["total_2nd_runs"] += runs_tot
                                
                            # Wickets tracker for innings averages
                            if "wickets" in d:
                                if is_first_innings:
                                    v["total_1st_wickets"] += 1
                                else:
                                    v["total_2nd_wickets"] += 1
                                    
                            # Pace vs. Spin Wicket & Economy calculations
                            if bowler:
                                bowl_style = self.find_bowler_style(bowler)
                                bowl_type = self.classify_bowler_type(bowl_style, bowler)
                                
                                is_wide_noball = ext_type and any(k in ext_type for k in ["wides", "noballs"])
                                is_legbye_bye = ext_type and any(k in ext_type for k in ["legbyes", "byes"])
                                
                                bowl_runs = runs_bat
                                if not is_legbye_bye:
                                    bowl_runs += runs_ext
                                    
                                if bowl_type == "Pace":
                                    if not is_wide_noball:
                                        v["pace_balls"] += 1
                                    v["pace_runs"] += bowl_runs
                                    
                                    if "wickets" in d:
                                        w = d["wickets"][0]
                                        if w.get("kind") not in ["run out", "retired hurt", "obstructing the field"]:
                                            v["pace_wickets"] += 1
                                else:
                                    if not is_wide_noball:
                                        v["spin_balls"] += 1
                                    v["spin_runs"] += bowl_runs
                                    
                                    if "wickets" in d:
                                        w = d["wickets"][0]
                                        if w.get("kind") not in ["run out", "retired hurt", "obstructing the field"]:
                                            v["spin_wickets"] += 1
                                            
            except Exception as e:
                print(f"[Warning] Failed to parse match file for venue stats {file_path}: {e}")
                
        end_time = time.time()
        print(f"[Venue Engine] Pre-parsing completed in {end_time - start_time:.2f} seconds.")
        print(f"               Unique Normalized Venues indexed: {len(self.venue_stats)}")

    def get_venue_stats(self, venue_name):
        """
        Returns complete, structured analytics for a canonical venue,
        equipped with optimal captain strategist insights, dew factors, and pitch type badges.
        """
        canonical = self.normalize_venue(venue_name)
        if canonical not in self.venue_stats:
            # Fallback mock stats block for unindexed venues
            return {
                "status": False,
                "error": f"Venue '{venue_name}' (canonical: '{canonical}') was not found in database registry."
            }
            
        v = self.venue_stats[canonical]
        
        matches = v["matches_count"]
        comp = v["completed_matches"] if v["completed_matches"] > 0 else 1
        
        # Win splits
        bat_first_pct = round((v["bat_first_wins"] / comp) * 100, 1)
        chase_pct = round((v["chase_wins"] / comp) * 100, 1)
        
        # Toss strategies
        optimal_toss = "field" if chase_pct >= 51.5 else "bat"
        optimal_toss_label = "WIN TOSS & BOWL FIRST" if optimal_toss == "field" else "WIN TOSS & BAT FIRST"
        
        toss_winner_win_pct = round((v["toss_winner_wins"] / comp) * 100, 1)
        
        # Innings averages
        avg_1st_score = round(v["total_1st_runs"] / matches, 1) if matches > 0 else 0
        avg_2nd_score = round(v["total_2nd_runs"] / matches, 1) if matches > 0 else 0
        
        # Pace vs. Spin details
        pace_w = v["pace_wickets"]
        spin_w = v["spin_wickets"]
        total_w = pace_w + spin_w
        
        pace_ratio = round((pace_w / total_w) * 100, 1) if total_w > 0 else 60.0
        spin_ratio = round((spin_w / total_w) * 100, 1) if total_w > 0 else 40.0
        
        pace_econ = round(v["pace_runs"] / (v["pace_balls"] / 6), 2) if v["pace_balls"] > 0 else 8.5
        spin_econ = round(v["spin_runs"] / (v["spin_balls"] / 6), 2) if v["spin_balls"] > 0 else 7.8
        
        # Pitch Classification Archetypes
        pitch_archetype = "Balanced Sporting Track"
        pitch_description = "Offers an even contest between bat and ball. Initial seam and swing for fast bowlers, with gradual turn and grip for spin bowlers later in the match."
        pitch_badge = "⚖️ SPORTING PITCH"
        
        if avg_1st_score >= 171.0:
            pitch_archetype = "Flat Batter's Paradise"
            pitch_description = "A batsman's dream. Minimal seam movement, little to no turn, fast outfield, and consistent bounce. Expect high-scoring shootouts!"
            pitch_badge = "🔥 BATTER'S PARADISE"
        elif spin_ratio >= 41.5 and spin_econ <= 7.75:
            pitch_archetype = "Slow & Spin-Friendly Dustbowl"
            pitch_description = "A dry surface that grips and turns. Pace bowlers will see little carry, while spinners find substantial turn and inconsistent bounce."
            pitch_badge = "🥎 SPIN DUSTBOWL"
        elif pace_ratio >= 64.0 and pace_econ <= 8.25:
            pitch_archetype = "Green Seamer / Bouncy Deck"
            pitch_description = "Features good grass coverage that aids fast bowlers with lateral movement, swing, and steep bounce. Batting can be tough against the new ball."
            pitch_badge = "⚡ SPEED DEMON DECK"
            
        # Dew Factor Index estimation (night chasing success rate scaling)
        night_chases = v["night_chase_wins"]
        night_bat_first = v["night_bat_first_wins"]
        night_total = night_chases + night_bat_first
        
        night_chase_pct = (night_chases / night_total * 100) if night_total > 0 else chase_pct
        
        # Scaled Dew Index (0 to 10)
        dew_index = 5.0 # Neutral default
        if night_chase_pct >= 62.0:
            dew_index = round(8.0 + (night_chase_pct - 62.0) * 0.15, 1)
            dew_index = min(9.8, dew_index)
        elif night_chase_pct >= 50.0:
            dew_index = round(5.0 + (night_chase_pct - 50.0) * 0.25, 1)
        else:
            dew_index = round(1.5 + (night_chase_pct - 35.0) * 0.23, 1)
            dew_index = max(1.2, dew_index)
            
        dew_level = "Low"
        if dew_index >= 7.5:
            dew_level = "Severe (Very High)"
        elif dew_index >= 4.5:
            dew_level = "Moderate"
            
        # Bounce estimation out of 5 stars
        bounce_stars = 3.5
        if pitch_archetype == "Flat Batter's Paradise":
            bounce_stars = 4.5
        elif pitch_archetype == "Slow & Spin-Friendly Dustbowl":
            bounce_stars = 2.0
        elif pitch_archetype == "Green Seamer / Bouncy Deck":
            bounce_stars = 5.0
            
        return {
            "status": True,
            "venue": canonical,
            "matches_played": matches,
            "splits": {
                "bat_first_wins": v["bat_first_wins"],
                "bat_first_pct": bat_first_pct,
                "chase_wins": v["chase_wins"],
                "chase_pct": chase_pct
            },
            "averages": {
                "avg_1st_score": avg_1st_score,
                "avg_2nd_score": avg_2nd_score
            },
            "toss_strategist": {
                "decision": optimal_toss,
                "decision_label": optimal_toss_label,
                "toss_win_rate": toss_winner_win_pct,
                "toss_decisions": v["toss_decisions"]
            },
            "environmental": {
                "dew_index": dew_index,
                "dew_level": dew_level,
                "day_matches": v["day_matches"],
                "night_matches": v["night_matches"]
            },
            "pitch_index": {
                "archetype": pitch_archetype,
                "badge": pitch_badge,
                "description": pitch_description,
                "bounce_stars": bounce_stars,
                "pace_split": {
                    "wickets": pace_w,
                    "ratio": pace_ratio,
                    "economy": pace_econ
                },
                "spin_split": {
                    "wickets": spin_w,
                    "ratio": spin_ratio,
                    "economy": spin_econ
                }
            }
        }

    def get_all_venues(self):
        """Returns sorted list of active normalized venues with at least 5 matches."""
        venues_list = []
        for name, stats in self.venue_stats.items():
            if stats["matches_count"] >= 5:
                venues_list.append({
                    "name": name,
                    "matches": stats["matches_count"]
                })
        # Sort by match counts descending
        venues_list.sort(key=lambda x: x["matches"], reverse=True)
        return [v["name"] for v in venues_list]

if __name__ == "__main__":
    engine = IPLVenueEngine()
    print("All venues:")
    print(engine.get_all_venues())
    print("\nWankhede stats:")
    print(json.dumps(engine.get_venue_stats("Wankhede Stadium"), indent=2))
