import os
import glob
import json
import time
import math
from modules.matchup_simulator.data_engine import IPLDataEngine
from modules.ground_analysis.ground_engine import IPLVenueEngine
from modules.live_predictor.live_engine import IPLLivePredictorEngine

class IPLPastAnalysisEngine:
    def __init__(self, data_engine=None, venue_engine=None, live_engine=None):
        self.data_engine = data_engine if data_engine else IPLDataEngine()
        self.venue_engine = venue_engine if venue_engine else IPLVenueEngine()
        self.live_engine = live_engine if live_engine else IPLLivePredictorEngine(
            data_engine=self.data_engine, 
            venue_engine=self.venue_engine
        )
        
        self.matches_index = []
        self.precompute_matches_metadata()

    def precompute_matches_metadata(self):
        """
        Lightweight metadata extraction (only parsing info block) 
        of all match JSONs on boot to populate the dropdown fast.
        """
        start_time = time.time()
        print("[Past Engine] Pre-indexing historical match metadata...")
        
        match_files = glob.glob(os.path.join(self.data_engine.data_dir, "[0-9]*.json"))
        
        for file_path in match_files:
            m_id = os.path.basename(file_path).split('.')[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    match_data = json.load(f)
                    
                info = match_data.get("info", {})
                teams = info.get("teams", ["Unknown Team 1", "Unknown Team 2"])
                venue = info.get("venue", "Unknown Venue")
                dates = info.get("dates", ["Unknown Date"])
                outcome = info.get("outcome", {})
                
                winner = outcome.get("winner", "No Result")
                by_info = outcome.get("by", {})
                
                margin_desc = "Tie / No Result"
                if "runs" in by_info:
                    margin_desc = f"won by {by_info['runs']} runs"
                elif "wickets" in by_info:
                    margin_desc = f"won by {by_info['wickets']} wickets"
                    
                self.matches_index.append({
                    "match_id": m_id,
                    "date": dates[0],
                    "team1": teams[0],
                    "team2": teams[1],
                    "venue": venue,
                    "winner": winner,
                    "margin": margin_desc,
                    "search_label": f"{dates[0]} - {teams[0]} vs {teams[1]} ({venue})"
                })
            except Exception as e:
                print(f"[Past Engine Warning] Failed indexing {file_path}: {e}")
                
        # Sort chronologically by date descending
        self.matches_index.sort(key=lambda x: x["date"], reverse=True)
        print(f"[Past Engine] Indexed {len(self.matches_index)} matches in {time.time() - start_time:.3f} seconds.")

    def get_all_matches(self):
        """Returns the sorted lightweight index of all matches."""
        return self.matches_index

    def calculate_win_prob(self, innings, batting_team, bowling_team, venue, over, ball, runs, wickets, target):
        """
        Wrapper around IPLLivePredictorEngine calculations to return batting win probability.
        """
        res = self.live_engine.predict_match_state(
            innings=innings,
            batting_team=batting_team,
            bowling_team=bowling_team,
            venue=venue,
            over=over,
            ball=ball,
            runs=runs,
            wickets=wickets,
            target=target
        )
        if res.get("status"):
            return res["win_probability"]["batting_team_pct"]
        return 50.0

    def analyze_match_timeline(self, match_id):
        """
        Flashes the full ball-by-ball analysis timeline of a selected past match.
        Computes dynamic win probability swings and smart pressure indexes.
        """
        file_path = os.path.join(self.data_engine.data_dir, f"{match_id}.json")
        if not os.path.exists(file_path):
            return {"status": False, "error": f"Match file '{match_id}.json' not found."}
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                match_data = json.load(f)
        except Exception as e:
            return {"status": False, "error": f"Failed reading match file: {e}"}

        info = match_data.get("info", {})
        venue = info.get("venue", "Unknown Venue")
        teams = info.get("teams", ["Unknown 1", "Unknown 2"])
        outcome = info.get("outcome", {})
        winner = outcome.get("winner", "No Result")
        margin = outcome.get("by", {})
        
        margin_text = ""
        if "runs" in margin:
            margin_text = f"won by {margin['runs']} runs"
        elif "wickets" in margin:
            margin_text = f"won by {margin['wickets']} wickets"
        else:
            margin_text = "Tie/No Result"

        innings_list = match_data.get("innings", [])
        
        # We first compile first innings final score to get the target for 2nd innings
        innings_1_runs = 0
        if len(innings_list) > 0:
            for over_data in innings_list[0].get("overs", []):
                for d in over_data.get("deliveries", []):
                    innings_1_runs += d.get("runs", {}).get("total", 0)
                    
        target = innings_1_runs + 1
        
        # Timeline data arrays
        deliveries_timeline = []
        
        # Let's keep state counters for dots and boundaries to calculate pressure
        # batter standard dot streak
        batter_dots = {}
        # bowler boundary conceded pressure
        bowler_boundaries = {}

        # Loop through innings
        for i_idx, inning in enumerate(innings_list):
            innings_num = i_idx + 1
            team_batting = inning.get("team", "Unknown")
            team_bowling = teams[1] if team_batting == teams[0] else teams[0]
            
            running_runs = 0
            running_wickets = 0
            
            overs = inning.get("overs", [])
            for over_data in overs:
                over_num = over_data.get("over", 0)
                deliveries = over_data.get("deliveries", [])
                
                # Cricsheet legal ball counter
                legal_ball_num = 1
                
                for d_idx, d in enumerate(deliveries):
                    batter = d.get("batter")
                    bowler = d.get("bowler")
                    runs_data = d.get("runs", {})
                    runs_batter = runs_data.get("batter", 0)
                    runs_total = runs_data.get("total", 0)
                    runs_extras = runs_data.get("extras", 0)
                    
                    extras = d.get("extras", {})
                    extras_type = list(extras.keys())[0] if extras else None
                    
                    is_wicket = "wickets" in d
                    wicket_desc = ""
                    if is_wicket:
                        w = d["wickets"][0]
                        wicket_desc = f"WKT: {w.get('player_out')} ({w.get('kind')})"
                        running_wickets += 1
                        
                    running_runs += runs_total
                    
                    # Update Pressure index
                    # Batter Dot Ball streak tracking
                    if batter not in batter_dots:
                        batter_dots[batter] = 0
                        
                    is_dot = (runs_batter == 0 and extras_type not in ["wides", "noballs"])
                    if is_dot:
                        batter_dots[batter] += 1
                    elif runs_batter > 0:
                        # streak reset on runs
                        batter_dots[batter] = 0
                        
                    # Bowler boundaries tracking
                    if bowler not in bowler_boundaries:
                        bowler_boundaries[bowler] = 0
                        
                    is_boundary = (runs_batter in [4, 6])
                    if is_boundary:
                        bowler_boundaries[bowler] += 1
                    elif runs_batter == 0:
                        # Bowler pressure relieved slightly on dot
                        bowler_boundaries[bowler] = max(0, bowler_boundaries[bowler] - 1)
                        
                    # Calculate Dynamic Pressure Indices (0 to 100)
                    # 1. Batter pressure calculation
                    pressure_bat = 20.0 # Base pressure
                    
                    if innings_num == 1:
                        # Innings 1 base pressure based on running run rate
                        balls_bowled = over_num * 6 + legal_ball_num
                        rpo = (running_runs / (balls_bowled / 6.0)) if balls_bowled > 0 else 6.0
                        # RPO under 7.5 increases pressure
                        pressure_bat += max(0, (7.5 - rpo) * 10.0)
                    else:
                        # Innings 2 base pressure based on required run rate
                        balls_left = max(1, 120 - (over_num * 6 + legal_ball_num))
                        runs_needed = target - running_runs
                        rrr = runs_needed / (balls_left / 6.0)
                        
                        v_stats = self.venue_engine.get_venue_stats(venue)
                        avg_2nd = v_stats.get("averages", {}).get("avg_2nd_score", 160.0)
                        venue_factor = avg_2nd / 160.0
                        scaled_rrr = rrr / venue_factor
                        
                        pressure_bat += (scaled_rrr - 6.0) * 8.0
                        
                    # Add Dot Ball Streak multiplier
                    dot_streak = batter_dots[batter]
                    if dot_streak == 1: pressure_bat += 8
                    elif dot_streak == 2: pressure_bat += 22
                    elif dot_streak == 3: pressure_bat += 45
                    elif dot_streak >= 4: pressure_bat += 70
                    
                    # Wickets pressure multiplier
                    wkt_factor = 1.0 + (running_wickets * 0.08)
                    pressure_bat = pressure_bat * wkt_factor
                    
                    # Clip boundaries
                    pressure_bat = max(5.0, min(95.0, pressure_bat))
                    if is_wicket:
                        pressure_bat = 95.0 # Max pressure peaks on dismissal
                        
                    # 2. Bowler pressure calculation
                    pressure_bowl = 20.0 # Base pressure
                    
                    b_streak = bowler_boundaries[bowler]
                    if b_streak == 1: pressure_bowl += 15
                    elif b_streak >= 2: pressure_bowl += 45
                    
                    if is_dot:
                        pressure_bowl = max(5.0, pressure_bowl - 8.0)
                    if is_wicket:
                        pressure_bowl = max(5.0, pressure_bowl - 30.0) # Massive pressure relief on taking a wicket
                        
                    pressure_bowl = max(5.0, min(95.0, pressure_bowl))
                    
                    # Round values
                    pressure_bat = round(pressure_bat, 1)
                    pressure_bowl = round(pressure_bowl, 1)
                    
                    # Calculate win probability splits
                    # We compute win probability at the START of the delivery (runs before this delivery)
                    prev_runs = running_runs - runs_total
                    prev_wickets = running_wickets - (1 if is_wicket else 0)
                    
                    prob_before = self.calculate_win_prob(
                        innings=innings_num,
                        batting_team=team_batting,
                        bowling_team=team_bowling,
                        venue=venue,
                        over=over_num,
                        ball=legal_ball_num,
                        runs=prev_runs,
                        wickets=prev_wickets,
                        target=target if innings_num == 2 else 0
                    )
                    
                    prob_after = self.calculate_win_prob(
                        innings=innings_num,
                        batting_team=team_batting,
                        bowling_team=team_bowling,
                        venue=venue,
                        over=over_num,
                        ball=legal_ball_num,
                        runs=running_runs,
                        wickets=running_wickets,
                        target=target if innings_num == 2 else 0
                    )
                    
                    # Create detail description
                    d_desc = f"{batter} faced {bowler}, scored {runs_batter} run(s)."
                    if runs_batter == 4: d_desc = f"FOUR! Beautiful shot by {batter} off {bowler}."
                    elif runs_batter == 6: d_desc = f"SIX! Massive hit by {batter} off {bowler}!"
                    elif is_wicket: d_desc = f"WICKET! {wicket_desc} by {bowler}."
                    
                    deliveries_timeline.append({
                        "innings": innings_num,
                        "batting_team": team_batting,
                        "bowling_team": team_bowling,
                        "over": over_num,
                        "ball": legal_ball_num,
                        "striker": batter,
                        "bowler": bowler,
                        "runs_batter": runs_batter,
                        "runs_total": runs_total,
                        "is_wicket": is_wicket,
                        "wicket_desc": wicket_desc,
                        "running_runs": running_runs,
                        "running_wickets": running_wickets,
                        "pressure_batter": pressure_bat,
                        "pressure_bowler": pressure_bowl,
                        "win_probability_before": prob_before,
                        "win_probability_after": prob_after,
                        "prob_shift": round(prob_after - prob_before, 1),
                        "description": d_desc
                    })
                    
                    # Increment ball count if it is a legal delivery
                    if extras_type not in ["wides", "noballs"]:
                        legal_ball_num += 1
                        
        # Extract Key Momentum Shift Events (Delta win probability >= 8.0%)
        momentum_shifts = []
        for idx, d in enumerate(deliveries_timeline):
            shift = d["prob_shift"]
            abs_shift = abs(shift)
            
            if abs_shift >= 8.0:
                # Compile swing explanation
                verdict = ""
                bat_team = d["batting_team"]
                bowl_team = d["bowling_team"]
                
                if shift > 0:
                    verdict = f"🏏 Momentum swing to Batting side (+{shift}% for {bat_team}). "
                    if d["runs_batter"] == 6:
                        verdict += f"A colossal Six by {d['striker']} relieves required rates pressure!"
                    elif d["runs_batter"] == 4:
                        verdict += f"Crucial boundary found by {d['striker']} disrupts bowler's lengths."
                    else:
                        verdict += "Steady strike rotation shifts the balance back in batting favor."
                else:
                    verdict = f"🛡️ Momentum swing to Bowling side ({shift}% reduction for {bat_team}). "
                    if d["is_wicket"]:
                        verdict += f"Massive wicket of {d['striker']} completely breaks batting momentum!"
                    else:
                        verdict += "Tight, disciplined dot balls spike batter's pressure index."
                        
                momentum_shifts.append({
                    "ball_index": idx,
                    "innings": d["innings"],
                    "over": d["over"],
                    "ball": d["ball"],
                    "event": d["wicket_desc"] if d["is_wicket"] else f"Boundary: {d['runs_batter']} runs",
                    "striker": d["striker"],
                    "bowler": d["bowler"],
                    "runs_total": d["runs_total"],
                    "is_wicket": d["is_wicket"],
                    "prob_before": d["win_probability_before"],
                    "prob_after": d["win_probability_after"],
                    "swing": shift,
                    "verdict": verdict
                })
                
        # Sort momentum shifts by descending absolute swing magnitude to highlight critical swing events
        momentum_shifts.sort(key=lambda x: abs(x["swing"]), reverse=True)
        
        return {
            "status": True,
            "match_info": {
                "match_id": match_id,
                "team1": teams[0],
                "team2": teams[1],
                "venue": venue,
                "winner": winner,
                "margin": margin_text
            },
            "timeline": deliveries_timeline,
            "momentum_shifts": momentum_shifts[:12] # return top 12 swing highlights
        }

if __name__ == "__main__":
    engine = IPLPastAnalysisEngine()
    print("\nTesting Past Matches metadata loading:")
    matches = engine.get_all_matches()
    if len(matches) > 0:
        print(f"Total Matches Loaded: {len(matches)}")
        print("First Match indexed:")
        print(json.dumps(matches[0], indent=2))
        
        print("\nTesting detailed timeline simulation for first match:")
        timeline = engine.analyze_match_timeline(matches[0]["match_id"])
        print(f"Match Info: {timeline['match_info']['team1']} vs {timeline['match_info']['team2']}")
        print(f"Total Deliveries simulated: {len(timeline['timeline'])}")
        print(f"Momentum inflections identified: {len(timeline['momentum_shifts'])}")
        if len(timeline['momentum_shifts']) > 0:
            print("Top Swing Event:")
            print(json.dumps(timeline['momentum_shifts'][0], indent=2))
    else:
        print("No matches parsed.")
