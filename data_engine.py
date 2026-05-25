import os
import glob
import json
import time

class IPLDataEngine:
    def __init__(self, data_dir="ipl_json_data"):
        self.data_dir = data_dir
        self.deliveries = []
        self.players = set()
        self.load_data()
        
    def load_data(self):
        """Pre-loads all IPL match JSON files into memory as a flat delivery list."""
        start_time = time.time()
        match_files = glob.glob(os.path.join(self.data_dir, "[0-9]*.json"))
        
        print(f"[Data Engine] Loading {len(match_files)} match files into memory...")
        
        for file_path in match_files:
            match_id = os.path.basename(file_path).split('.')[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    match_data = json.load(f)
                    
                info = match_data.get("info", {})
                venue = info.get("venue", "Unknown Venue")
                dates = info.get("dates", ["Unknown Date"])
                match_date = dates[0]
                
                innings = match_data.get("innings", [])
                for inning in innings:
                    team_batting = inning.get("team", "Unknown")
                    overs = inning.get("overs", [])
                    
                    for over_data in overs:
                        over_num = over_data.get("over", 0)
                        deliveries = over_data.get("deliveries", [])
                        
                        for d_idx, d in enumerate(deliveries):
                            batter = d.get("batter")
                            bowler = d.get("bowler")
                            non_striker = d.get("non_striker")
                            
                            runs = d.get("runs", {})
                            runs_batter = runs.get("batter", 0)
                            runs_extras = runs.get("extras", 0)
                            runs_total = runs.get("total", 0)
                            
                            extras = d.get("extras", {})
                            extras_type = list(extras.keys())[0] if extras else None
                            
                            is_wicket = False
                            wicket_player_out = None
                            wicket_kind = None
                            
                            if "wickets" in d:
                                is_wicket = True
                                w = d["wickets"][0]
                                wicket_player_out = w.get("player_out")
                                wicket_kind = w.get("kind")
                            
                            # Add players to master set
                            if batter: self.players.add(batter)
                            if bowler: self.players.add(bowler)
                            if non_striker: self.players.add(non_striker)
                            
                            # Append flat delivery structure
                            self.deliveries.append({
                                "match_id": match_id,
                                "date": match_date,
                                "venue": venue,
                                "team_batting": team_batting,
                                "batter": batter,
                                "bowler": bowler,
                                "runs_batter": runs_batter,
                                "runs_extras": runs_extras,
                                "runs_total": runs_total,
                                "extras_type": extras_type,
                                "is_wicket": is_wicket,
                                "wicket_player_out": wicket_player_out,
                                "wicket_kind": wicket_kind
                            })
                            
            except Exception as e:
                # Log error and skip corrupt files
                print(f"[Warning] Failed to parse match file {file_path}: {e}")
                
        end_time = time.time()
        print(f"[Data Engine] Load completed successfully!")
        print(f"              Parsed Deliveries: {len(self.deliveries)}")
        print(f"              Unique Players indexed: {len(self.players)}")
        print(f"              Time Taken: {end_time - start_time:.2f} seconds")

    def find_cricsheet_name(self, full_name):
        """
        Dynamically maps a player's full roster name (e.g. 'Virat Kohli', 'Yuzvendra Chahal')
        to their short standard Cricsheet database name (e.g. 'V Kohli', 'YS Chahal').
        """
        parts = full_name.lower().strip().split()
        if not parts:
            return full_name
            
        last_name = parts[-1]
        first_name = parts[0]
        
        # 1. Filter candidates by exact last name matching
        candidates = [p for p in self.players if p.lower().endswith(last_name)]
        
        # 2. Sub-search fallback: last name appears anywhere in the name
        if not candidates:
            candidates = [p for p in self.players if last_name in p.lower()]
            
        if not candidates:
            return full_name  # Fallback to input if no candidate matches
            
        if len(candidates) == 1:
            return candidates[0]
            
        # 3. Handle multiple matching candidates (e.g., T Kohli vs V Kohli for Kohli)
        # Check matching of the first initial
        first_initial = first_name[0]
        for c in candidates:
            c_parts = c.lower().split()
            if c_parts and (c_parts[0].startswith(first_initial) or first_initial in c_parts[0]):
                return c
                
        # Default to first matched candidate
        return candidates[0]

    def get_head_to_head(self, batter_name, bowler_name):
        """Calculates exact head-to-head statistics between a specific batter and bowler."""
        c_batter = self.find_cricsheet_name(batter_name)
        c_bowler = self.find_cricsheet_name(bowler_name)
        
        runs = 0
        balls = 0
        fours = 0
        sixes = 0
        dismissals = 0
        dots = 0
        dismissal_types = {}
        
        # Filter deliveries
        matchup_deliveries = [
            d for d in self.deliveries 
            if d["batter"] == c_batter and d["bowler"] == c_bowler
        ]
        
        for d in matchup_deliveries:
            # Wides do not count as a ball faced for the batter
            if d["extras_type"] != "wides":
                balls += 1
                
            runs += d["runs_batter"]
            if d["runs_batter"] == 4:
                fours += 1
            elif d["runs_batter"] == 6:
                sixes += 1
            elif d["runs_batter"] == 0 and d["runs_extras"] == 0:
                dots += 1
                
            if d["is_wicket"] and d["wicket_player_out"] == c_batter:
                # Bowler gets credit for wickets except run out, retired hurt, obstructing field
                if d["wicket_kind"] not in ["run out", "retired hurt", "obstructing the field"]:
                    dismissals += 1
                    kind = d["wicket_kind"]
                    dismissal_types[kind] = dismissal_types.get(kind, 0) + 1
                    
        strike_rate = (runs / balls * 100) if balls > 0 else 0
        boundary_runs = (fours * 4) + (sixes * 6)
        boundary_pct = (boundary_runs / runs * 100) if runs > 0 else 0
        
        return {
            "runs": runs,
            "balls": balls,
            "fours": fours,
            "sixes": sixes,
            "dots": dots,
            "dismissals": dismissals,
            "strike_rate": round(strike_rate, 2),
            "boundary_pct": round(boundary_pct, 2),
            "dismissal_types": dismissal_types
        }

    def get_all_matches_for_stats(self, batter_name=None, bowler_name=None):
        """Helper to get general overall career stats for batter/bowler inside the IPL."""
        runs = 0
        balls = 0
        dismissals = 0
        fours = 0
        sixes = 0
        
        if batter_name:
            c_batter = self.find_cricsheet_name(batter_name)
            batt_deliveries = [d for d in self.deliveries if d["batter"] == c_batter]
            for d in batt_deliveries:
                if d["extras_type"] != "wides":
                    balls += 1
                runs += d["runs_batter"]
                if d["runs_batter"] == 4: fours += 1
                elif d["runs_batter"] == 6: sixes += 1
                if d["is_wicket"] and d["wicket_player_out"] == c_batter:
                    if d["wicket_kind"] not in ["run out", "retired hurt"]:
                        dismissals += 1
                        
            strike_rate = (runs / balls * 100) if balls > 0 else 0
            avg = (runs / dismissals) if dismissals > 0 else runs
            return {
                "runs": runs,
                "balls": balls,
                "dismissals": dismissals,
                "average": round(avg, 2),
                "strike_rate": round(strike_rate, 2),
                "fours": fours,
                "sixes": sixes
            }
            
        elif bowler_name:
            c_bowler = self.find_cricsheet_name(bowler_name)
            runs_conceded = 0
            legal_balls = 0
            wickets = 0
            bowl_deliveries = [d for d in self.deliveries if d["bowler"] == c_bowler]
            for d in bowl_deliveries:
                # Wides and no-balls do not count as legal deliveries faced by bowler
                if d["extras_type"] not in ["wides", "noballs"]:
                    legal_balls += 1
                    
                # Bowler runs conceded does not include legbyes/byes
                if d["extras_type"] not in ["legbyes", "byes"]:
                    runs_conceded += d["runs_batter"] + d["runs_extras"]
                    
                if d["is_wicket"]:
                    if d["wicket_kind"] not in ["run out", "retired hurt", "obstructing the field"]:
                        wickets += 1
                        
            overs = f"{legal_balls // 6}.{legal_balls % 6}"
            economy = (runs_conceded / (legal_balls / 6)) if legal_balls > 0 else 0
            avg = (runs_conceded / wickets) if wickets > 0 else runs_conceded
            return {
                "overs": overs,
                "runs_conceded": runs_conceded,
                "wickets": wickets,
                "economy": round(economy, 2),
                "average": round(avg, 2)
            }
            
        return {}

# Quick standalone debug test
if __name__ == "__main__":
    engine = IPLDataEngine()
    print("Testing Kohli vs Bumrah head-to-head:")
    stats = engine.get_head_to_head("Virat Kohli", "Jasprit Bumrah")
    print(json.dumps(stats, indent=2))
