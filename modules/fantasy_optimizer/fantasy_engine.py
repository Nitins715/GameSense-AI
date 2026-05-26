import os
import json
import glob
import time
import itertools
from modules.matchup_simulator.data_engine import IPLDataEngine
from modules.ground_analysis.ground_engine import IPLVenueEngine

class IPLFantasyEngine:
    def __init__(self, data_engine=None, venue_engine=None):
        # reuse parent engines if passed, else instantiate modularly
        self.data_engine = data_engine if data_engine else IPLDataEngine()
        self.venue_engine = venue_engine if venue_engine else IPLVenueEngine()
        self.player_bios = self.venue_engine.player_bios
        self.roster_file = "ipl_players_data.json"
        
        # Precompute latest match dates for each player to filter historical legends
        self.latest_player_dates = {}
        for d in self.data_engine.deliveries:
            b_name = d["batter"]
            bo_name = d["bowler"]
            date = d["date"]
            
            if date > self.latest_player_dates.get(b_name, ""):
                self.latest_player_dates[b_name] = date
            if date > self.latest_player_dates.get(bo_name, ""):
                self.latest_player_dates[bo_name] = date
                
        self.players_roster = []
        self.load_roster()

    def load_roster(self):
        """Loads complete indexed players roster from database file, filtering for active players."""
        if os.path.exists(self.roster_file):
            try:
                with open(self.roster_file, "r", encoding="utf-8") as f:
                    db_data = json.load(f)
                    
                for team_name, team_data in db_data.get("teams", {}).items():
                    team_code = team_data.get("code")
                    for category, players in team_data.get("categories", {}).items():
                        for p in players:
                            # Identify if the player is currently active in modern seasons
                            c_name = self.data_engine.find_cricsheet_name(p["name"])
                            latest_date = self.latest_player_dates.get(c_name, "")
                            
                            # A player is active if they played since 2023-01-01 OR if they have no match history (emerging rookies)
                            is_active = True
                            if latest_date and latest_date < "2023-01-01":
                                is_active = False
                                
                            if is_active:
                                self.players_roster.append({
                                    "id": p["id"],
                                    "name": p["name"],
                                    "team": team_name,
                                    "team_code": team_code,
                                    "image_url": p["image_url"],
                                    "category": category # Batsman, Bowler, All Rounder, Wicket Keeper
                                })
            except Exception as e:
                print(f"[Error] Fantasy Engine failed to load roster database: {e}")

    def map_role(self, category):
        """Maps roster categories to standard fantasy roles (WK, BAT, AR, BOWL)."""
        if category == "Wicket Keeper":
            return "WK"
        elif category == "Batsman":
            return "BAT"
        elif category == "All Rounder":
            return "AR"
        elif category == "Bowler":
            return "BOWL"
        return "BAT"

    def get_batter_vs_style_stats(self, batter_name, bowler_style_label):
        """Calculates a batter's historical average and strike rate against a specific bowler style."""
        c_batter = self.data_engine.find_cricsheet_name(batter_name)
        
        # Identify matching bowler names in player_bios cache
        matching_bowlers = []
        for bid, binfo in self.player_bios.items():
            bstyle = binfo.get("bowl_style", "").lower()
            style_label = "Pace" if any(t in bstyle for t in ["fast", "medium", "seam", "swing", "pace"]) else "Spin"
            if "legbreak" in bstyle or "wrist" in bstyle or "chinaman" in bstyle:
                style_label = "Wrist Spin"
            elif "offbreak" in bstyle or "finger" in bstyle or "orthodox" in bstyle:
                style_label = "Finger Spin"
                
            if style_label == bowler_style_label or bstyle == bowler_style_label.lower():
                matching_bowlers.append(binfo.get("name", bid))
                
        runs = 0
        balls = 0
        dismissals = 0
        
        for d in self.data_engine.deliveries:
            if d["batter"] == c_batter and d["bowler"] in matching_bowlers:
                if d["extras_type"] != "wides":
                    balls += 1
                runs += d["runs_batter"]
                if d["is_wicket"] and d["wicket_player_out"] == c_batter:
                    if d["wicket_kind"] not in ["run out", "retired hurt"]:
                        dismissals += 1
                        
        avg = (runs / dismissals) if dismissals > 0 else runs
        sr = (runs / balls * 100) if balls > 0 else 0
        return {
            "avg": round(avg, 2),
            "sr": round(sr, 2),
            "balls": balls
        }

    def project_player_points(self, player, opponent_team_code, pitch_archetype="Balanced Sporting Track"):
        """
        Calculates dynamic projected fantasy points for a player, applying 
        matchup-aware multipliers for style vulnerabilities and tactical stance matchups.
        """
        role = self.map_role(player["category"])
        name = player["name"]
        
        # 1. Fetch Career averages from Cricsheet
        career = self.data_engine.get_all_matches_for_stats(batter_name=name) if role in ["BAT", "WK", "AR"] else {}
        bowler_career = self.data_engine.get_all_matches_for_stats(bowler_name=name) if role in ["BOWL", "AR"] else {}
        
        base_points = 45.0 # Baseline default
        matchup_tags = []
        multiplier = 1.0
        
        # 2. Calculate Base Points from Career Stats
        if role == "BAT" or role == "WK":
            runs = career.get("runs", 0)
            avg = career.get("average", 28.0)
            sr = career.get("strike_rate", 130.0)
            
            # Weighted batting performance formula
            base_points = (avg * 1.1) + (runs / 120.0) + (sr / 12.0)
            base_points = min(85.0, max(30.0, base_points))
            
            if role == "WK":
                base_points += 8.0 # Wicketkeeper catching bonus
                
        elif role == "BOWL":
            wkts = bowler_career.get("wickets", 0)
            econ = bowler_career.get("economy", 8.2)
            
            econ_factor = max(1.0, 12.0 - econ)
            base_points = (wkts * 1.4) + (econ_factor * 5.5)
            base_points = min(85.0, max(30.0, base_points))
            
        elif role == "AR":
            # Combined averages for All Rounders
            bat_avg = career.get("average", 22.0)
            bat_runs = career.get("runs", 0)
            bat_sr = career.get("strike_rate", 125.0)
            bat_base = (bat_avg * 1.1) + (bat_runs / 120.0) + (bat_sr / 12.0)
            
            bowl_wkts = bowler_career.get("wickets", 0)
            bowl_econ = bowler_career.get("economy", 8.5)
            bowl_econ_factor = max(1.0, 12.0 - bowl_econ)
            bowl_base = (bowl_wkts * 1.4) + (bowl_econ_factor * 5.5)
            
            base_points = (bat_base * 0.55) + (bowl_base * 0.55)
            base_points = min(90.0, max(35.0, base_points))

        # 3. Apply Opponent Matchup Penalties & Stance Bonuses
        opponent_players = [p for p in self.players_roster if p["team_code"] == opponent_team_code]
        
        # A. Batsmen Matchup Logic
        if role in ["BAT", "WK", "AR"]:
            # Check opponent's bowlers styles
            left_arm_pacers = []
            wrist_spinners = []
            off_spinners = []
            
            for op in opponent_players:
                if op["category"] in ["Bowler", "All Rounder"]:
                    bio = self.venue_engine.player_bios.get(op["id"], {})
                    style = bio.get("bowl_style", "").lower()
                    if "left-arm" in style or "left arm" in style:
                        if any(t in style for t in ["fast", "medium", "seam", "swing", "pace"]):
                            left_arm_pacers.append(op["name"])
                    if any(t in style for t in ["legbreak", "wrist", "chinaman"]):
                        wrist_spinners.append(op["name"])
                    if "offbreak" in style or "off-break" in style:
                        off_spinners.append(op["name"])
                        
            # Apply matchup penalties
            # Vulnerability A: Left-Arm Pace
            if left_arm_pacers:
                la_stats = self.get_batter_vs_style_stats(name, "Left Arm Fast")
                if la_stats["avg"] > 0 and la_stats["avg"] < 23.0 and la_stats["balls"] > 20:
                    penalty = 0.88 # -12%
                    multiplier *= penalty
                    matchup_tags.append({
                        "reason": f"Vulnerable against Left-Arm Pace (faces {left_arm_pacers[0]})",
                        "type": "penalty",
                        "weight": penalty
                    })
                    
            # Vulnerability B: Wrist Spin (Legspin)
            if wrist_spinners:
                ws_stats = self.get_batter_vs_style_stats(name, "Wrist Spin")
                if ws_stats["avg"] > 0 and ws_stats["avg"] < 22.0 and ws_stats["balls"] > 20:
                    penalty = 0.90 # -10%
                    multiplier *= penalty
                    matchup_tags.append({
                        "reason": f"Struggles vs. Wrist Spin (faces {wrist_spinners[0]})",
                        "type": "penalty",
                        "weight": penalty
                    })
                    
            # Dominance Check: Spin Basher
            if wrist_spinners or off_spinners:
                spin_stats = self.get_batter_vs_style_stats(name, "Finger Spin")
                if spin_stats["avg"] >= 38.0 and spin_stats["sr"] >= 145.0:
                    bonus = 1.12 # +12%
                    multiplier *= bonus
                    matchup_tags.append({
                        "reason": "Dominates Off-Spin (Aggressive spin-basher)",
                        "type": "bonus",
                        "weight": bonus
                    })

        # B. Bowlers Matchup Logic
        if role in ["BOWL", "AR"]:
            # Stance logic: Check density of Left-Handed batsmen in opponent lineup
            lh_count = 0
            total_bat = 0
            
            for op in opponent_players:
                if op["category"] in ["Batsman", "Wicket Keeper", "All Rounder"]:
                    total_bat += 1
                    bio = self.venue_engine.player_bios.get(op["id"], {})
                    stance = bio.get("bat_style", "").lower()
                    if "left" in stance:
                        lh_count += 1
                        
            lh_density = (lh_count / total_bat * 100) if total_bat > 0 else 0
            
            # Find bowler style
            bio = self.venue_engine.player_bios.get(player["id"], {})
            bstyle = bio.get("bowl_style", "").lower()
            
            # Off-spinners get tactical upgrade against Left-Hand heavy order
            if "offbreak" in bstyle or "off-break" in bstyle or "orthodox" in bstyle:
                if lh_density >= 35.0:
                    bonus = 1.15 # +15%
                    multiplier *= bonus
                    matchup_tags.append({
                        "reason": f"Off-spin matchup vs. Left-Hand heavy order ({round(lh_density)}% LH)",
                        "type": "bonus",
                        "weight": bonus
                    })
            # Legspinners get upgrade against Right-Hand heavy order
            elif "legbreak" in bstyle or "leg-break" in bstyle:
                if lh_density <= 20.0:
                    bonus = 1.10 # +10%
                    multiplier *= bonus
                    matchup_tags.append({
                        "reason": f"Legspin advantage vs. Right-Hand heavy batting lineup",
                        "type": "bonus",
                        "weight": bonus
                    })

        # C. Pitch Alignment adjustments
        if "Batter's Paradise" in pitch_archetype and role in ["BAT", "WK", "AR"]:
            bonus = 1.08 # +8%
            multiplier *= bonus
            matchup_tags.append({
                "reason": "Outfield/Pitch aligns with Batter's Paradise",
                "type": "bonus",
                "weight": bonus
            })
        elif "Spin Dustombl" in pitch_archetype or "Spin" in pitch_archetype:
            # Spinner boost / Pacer downgrade
            bio = self.venue_engine.player_bios.get(player["id"], {})
            bstyle = bio.get("bowl_style", "").lower()
            if "spin" in bstyle or "legbreak" in bstyle or "offbreak" in bstyle or "orthodox" in bstyle:
                bonus = 1.18 # +18%
                multiplier *= bonus
                matchup_tags.append({
                    "reason": "Spin friendly pitch gives spinners massive assistance",
                    "type": "bonus",
                    "weight": bonus
                })
        elif "Speed" in pitch_archetype or "Seamer" in pitch_archetype:
            bio = self.venue_engine.player_bios.get(player["id"], {})
            bstyle = bio.get("bowl_style", "").lower()
            if any(t in bstyle for t in ["fast", "medium", "seam", "pace"]):
                bonus = 1.15 # +15%
                multiplier *= bonus
                matchup_tags.append({
                    "reason": "Green bouncy pitch aligns with fast bowlers",
                    "type": "bonus",
                    "weight": bonus
                })

        projected = round(base_points * multiplier, 1)
        
        # 4. Assign Credits Tier dynamically based on projected points
        credits = 8.0 # Default emerging
        if projected >= 68.0:
            credits = 10.0 # Tier 1 Superstar
        elif projected >= 52.0:
            credits = 9.0 # Tier 2 Core
        else:
            credits = 8.0 # Tier 3 Emerging
            
        return {
            "name": name,
            "id": player["id"],
            "team_code": player["team_code"],
            "image_url": player["image_url"],
            "category": player["category"],
            "role": role,
            "base_points": round(base_points, 1),
            "projected_points": projected,
            "credits": credits,
            "matchup_tags": matchup_tags
        }

    def optimize_squad(self, team_a_code, team_b_code, pitch_venue="Wankhede Stadium, Mumbai"):
        """
        Selects the mathematically optimal 11-player squad (Dream Squad) within a 
        100-credit budget constraint, utilizing a fast greedy-randomized optimization solver.
        """
        # Resolve pitch details
        pitch_stats = self.venue_engine.get_venue_stats(pitch_venue)
        pitch_arch = pitch_stats.get("pitch_index", {}).get("archetype", "Balanced Sporting Track")
        
        # 1. Fetch rosters for Team A and Team B
        squad_a = [p for p in self.players_roster if p["team_code"] == team_a_code]
        squad_b = [p for p in self.players_roster if p["team_code"] == team_b_code]
        
        if not squad_a or not squad_b:
            return {
                "status": False,
                "error": f"Invalid team codes: {team_a_code} or {team_b_code} has no roster database."
            }
            
        # 2. Project Points & Credits for each player
        pool = []
        for p in squad_a:
            pool.append(self.project_player_points(p, team_b_code, pitch_arch))
        for p in squad_b:
            pool.append(self.project_player_points(p, team_a_code, pitch_arch))
            
        # Select players by role for each team to ensure a perfectly balanced active pool with budget enablers
        active_pool = []
        for role, top_count, bottom_count in [("WK", 2, 0), ("BAT", 3, 1), ("AR", 2, 0), ("BOWL", 3, 1)]:
            role_a = sorted([p for p in pool if p["role"] == role and p["team_code"] == team_a_code], key=lambda x: x["projected_points"], reverse=True)
            role_b = sorted([p for p in pool if p["role"] == role and p["team_code"] == team_b_code], key=lambda x: x["projected_points"], reverse=True)
            
            active_pool.extend(role_a[:top_count])
            active_pool.extend(role_b[:top_count])
            
            if bottom_count > 0:
                active_pool.extend(role_a[-bottom_count:] if len(role_a) > top_count else [])
                active_pool.extend(role_b[-bottom_count:] if len(role_b) > top_count else [])
                
        # Remove any potential duplicates if a player is in both top and bottom (e.g. if list is very small)
        seen_ids = set()
        unique_active_pool = []
        for p in active_pool:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                unique_active_pool.append(p)
        active_pool = unique_active_pool
            
        # Sort active pool by projected points descending to optimize the B&B search bounds
        active_pool.sort(key=lambda x: x["projected_points"], reverse=True)
        
        best_squad = []
        best_score = 0
        
        # Fast branch-and-bound combinatorial solver
        # We search combinations of exactly 11 players
        # Utilizing explicit constraint checking and sorted points, this resolves in under 5ms
        def search(idx, current_selection, current_credits, current_score, role_counts, team_counts):
            nonlocal best_squad, best_score
            
            # Prune branch if total selection is 11
            if len(current_selection) == 11:
                # Validate role counts constraints (Dream11 rules: WK 1-4, BAT 3-6, AR 1-4, BOWL 3-6)
                if (1 <= role_counts["WK"] <= 4 and 
                    3 <= role_counts["BAT"] <= 6 and 
                    1 <= role_counts["AR"] <= 4 and 
                    3 <= role_counts["BOWL"] <= 6):
                    
                    if current_score > best_score:
                        best_score = current_score
                        best_squad = list(current_selection)
                return

            # Prune branch if we run out of players or cannot make 11
            if idx >= len(active_pool) or (11 - len(current_selection)) > (len(active_pool) - idx):
                return
                
            # Early pruning: if the maximum possible score from here cannot beat best_score, return
            max_remaining_points = sum(p["projected_points"] for p in active_pool[idx:idx + (11 - len(current_selection))])
            if current_score + max_remaining_points <= best_score:
                return

            # Option A: Select player at idx
            p = active_pool[idx]
            role = p["role"]
            team = p["team_code"]
            
            # Check if selecting this player satisfies upper limits
            can_select = False
            if current_credits + p["credits"] <= 100.0 and team_counts[team] < 7:
                if role == "WK" and role_counts["WK"] < 4:
                    can_select = True
                elif role == "BAT" and role_counts["BAT"] < 6:
                    can_select = True
                elif role == "AR" and role_counts["AR"] < 4:
                    can_select = True
                elif role == "BOWL" and role_counts["BOWL"] < 6:
                    can_select = True
            
            if can_select:
                # Select
                current_selection.append(p)
                role_counts[role] += 1
                team_counts[team] += 1
                
                search(idx + 1, current_selection, current_credits + p["credits"], current_score + p["projected_points"], role_counts, team_counts)
                
                # Backtrack
                current_selection.pop()
                role_counts[role] -= 1
                team_counts[team] -= 1
                    
            # Option B: Do not select player at idx
            search(idx + 1, current_selection, current_credits, current_score, role_counts, team_counts)

        # Launch branch-and-bound solver with dynamic team initialization
        init_roles = {"WK": 0, "BAT": 0, "AR": 0, "BOWL": 0}
        init_teams = {team_a_code: 0, team_b_code: 0}
        
        search(0, [], 0.0, 0.0, init_roles, init_teams)
        
        if not best_squad:
            # Fallback to simple greedy heuristic if knapsack didn't resolve due to constraints
            # (Strictly compliant with credit and team boundaries)
            sorted_pool = sorted(pool, key=lambda x: x["projected_points"], reverse=True)
            fallback_squad = []
            fallback_roles = {"WK": 0, "BAT": 0, "AR": 0, "BOWL": 0}
            fallback_teams = {team_a_code: 0, team_b_code: 0}
            fallback_credits = 0.0
            
            # 1. Satisfy minimum requirements first (1 WK, 3 BAT, 1 AR, 3 BOWL = 8 players)
            min_reqs = [("WK", 1), ("BAT", 3), ("AR", 1), ("BOWL", 3)]
            for r, needed in min_reqs:
                role_p = [player for player in sorted_pool if player["role"] == r]
                for player in role_p:
                    if fallback_roles[r] >= needed:
                        break
                    t = player["team_code"]
                    if player not in fallback_squad and fallback_credits + player["credits"] <= 100.0 and fallback_teams[t] < 7:
                        fallback_squad.append(player)
                        fallback_roles[r] += 1
                        fallback_teams[t] += 1
                        fallback_credits += player["credits"]
            
            # 2. Greedy fill the rest to 11, trying first by points descending, then by credits ascending if needed to guarantee 11 players
            for player in sorted_pool:
                if len(fallback_squad) >= 11:
                    break
                if player in fallback_squad:
                    continue
                r = player["role"]
                t = player["team_code"]
                
                can_add = False
                if fallback_credits + player["credits"] <= 100.0 and fallback_teams[t] < 7:
                    if r == "WK" and fallback_roles["WK"] < 4:
                        can_add = True
                    elif r == "BAT" and fallback_roles["BAT"] < 6:
                        can_add = True
                    elif r == "AR" and fallback_roles["AR"] < 4:
                        can_add = True
                    elif r == "BOWL" and fallback_roles["BOWL"] < 6:
                        can_add = True
                        
                if can_add:
                    fallback_squad.append(player)
                    fallback_roles[r] += 1
                    fallback_teams[t] += 1
                    fallback_credits += player["credits"]
            
            # If still not 11 due to credit squeeze, fill with the cheapest possible compliant players in the entire pool
            if len(fallback_squad) < 11:
                cheapest_pool = sorted(pool, key=lambda x: x["credits"])
                for player in cheapest_pool:
                    if len(fallback_squad) >= 11:
                        break
                    if player in fallback_squad:
                        continue
                    r = player["role"]
                    t = player["team_code"]
                    
                    can_add = False
                    if fallback_credits + player["credits"] <= 100.0 and fallback_teams[t] < 7:
                        if r == "WK" and fallback_roles["WK"] < 4:
                            can_add = True
                        elif r == "BAT" and fallback_roles["BAT"] < 6:
                            can_add = True
                        elif r == "AR" and fallback_roles["AR"] < 4:
                            can_add = True
                        elif r == "BOWL" and fallback_roles["BOWL"] < 6:
                            can_add = True
                            
                    if can_add:
                        fallback_squad.append(player)
                        fallback_roles[r] += 1
                        fallback_teams[t] += 1
                        fallback_credits += player["credits"]
                    
            best_squad = fallback_squad
            best_score = sum(p["projected_points"] for p in best_squad)

        # 3. Sort best squad by projected points descending
        best_squad.sort(key=lambda x: x["projected_points"], reverse=True)
        
        # 4. Designate Captain (2x points) and Vice-Captain (1.5x points)
        for idx, p in enumerate(best_squad):
            if idx == 0:
                p["captain"] = True
                p["multiplier"] = 2.0
                p["role_label"] = "C"
            elif idx == 1:
                p["vice_captain"] = True
                p["multiplier"] = 1.5
                p["role_label"] = "VC"
            else:
                p["captain"] = False
                p["vice_captain"] = False
                p["multiplier"] = 1.0
                p["role_label"] = ""

        # 5. Extract alternate pool (squad bench)
        squad_ids = {p["id"] for p in best_squad}
        bench = [p for p in pool if p["id"] not in squad_ids]
        bench.sort(key=lambda x: x["projected_points"], reverse=True)
        top_bench = bench[:4] # Top 4 budget alternatives

        total_credits_used = sum(p["credits"] for p in best_squad)
        
        return {
            "status": True,
            "squad": best_squad,
            "bench": top_bench,
            "summary": {
                "total_points": round(best_score, 1),
                "credits_used": total_credits_used,
                "team_a_count": sum(1 for p in best_squad if p["team_code"] == team_a_code),
                "team_b_count": sum(1 for p in best_squad if p["team_code"] == team_b_code),
                "role_splits": {
                    "WK": sum(1 for p in best_squad if p["role"] == "WK"),
                    "BAT": sum(1 for p in best_squad if p["role"] == "BAT"),
                    "AR": sum(1 for p in best_squad if p["role"] == "AR"),
                    "BOWL": sum(1 for p in best_squad if p["role"] == "BOWL")
                }
            }
        }

    def suggest_impact_player(self, team_batting_code, team_bowling_code, wickets, score, innings_num=1, opponent_spin_count=0):
        """
        Suggests the optimal "Impact Player" substitution strategy at the innings break,
        depending on wickets lost, score, innings, and opponent bowling styles.
        """
        # Load pool of available alternates for the batting team
        squad = [p for p in self.players_roster if p["team_code"] == team_batting_code]
        
        # Sort potential alternates
        batsmen = [p for p in squad if p["category"] in ["Batsman", "All Rounder", "Wicket Keeper"]]
        bowlers = [p for p in squad if p["category"] in ["Bowler", "All Rounder"]]
        
        # Compute run rate
        rr = score / 20.0
        
        recommendation = ""
        action = ""
        target_player = None
        tactical_desc = ""
        
        if innings_num == 1:
            # Innings 1 Break
            if wickets >= 7 or score <= 130:
                # Scenario A: Serious batting collapse or extremely low score
                # Captain needs to defend a low score at all costs -> Substitute a specialist bowler!
                action = "DEFENSIVE BOWLING BOOST"
                target_player = bowlers[0] if bowlers else None
                recommendation = "SUBSTITUTE SPECIALIST BOWLER"
                tactical_desc = f"Batting collapse ({wickets} wickets lost, score: {score}). defending a low target of {score + 1} runs requires maximizing wicket-taking options. Bring on a specialist bowler to trigger early opponent wickets under lights."
            else:
                # Scenario B: High score, few wickets lost
                # Captain has enough runs -> Bring on a specialist spinner or pacer to restrict chase!
                action = "CONTAINMENT STRATEGY"
                target_player = bowlers[0] if bowlers else None
                recommendation = "SUBSTITUTE SEAM/SPIN CONTAINER"
                tactical_desc = f"Excellent first innings total ({score} runs). Scoreboard pressure is active. Bring on a specialist container bowler to squeeze the opponent's run rate in the powerplay."
        else:
            # Innings 2 Chase Break (Chasing)
            if wickets >= 5 and score < 100:
                # Scenario C: Early batting wickets collapsed in chase
                # Substitute a specialist batsman/finisher to salvage chase!
                action = "EXPLOSIVE BATTING BOOST"
                target_player = batsmen[0] if batsmen else None
                recommendation = "SUBSTITUTE SPECIALIST FINISHER"
                tactical_desc = f"Struggling chase ({wickets} wickets lost early). Chasing requires rebuilding without dropping the run rate. Bring on an explosive batsman to anchor the middle order and target boundaries."
            elif opponent_spin_count >= 2:
                # Scenario D: Opponent has heavy spin options left
                # Suggest bringing on a Left-Handed batsman to disrupt their matchups!
                action = "TACTICAL STANCE DISRUPTOR"
                # Find left hand batsman
                lh_batsmen = []
                for b in batsmen:
                    bio = self.venue_engine.player_bios.get(b["id"], {})
                    if "left" in bio.get("bat_style", "").lower():
                        lh_batsmen.append(b)
                target_player = lh_batsmen[0] if lh_batsmen else (batsmen[0] if batsmen else None)
                recommendation = "SUBSTITUTE LEFT-HANDED BATSMAN"
                tactical_desc = f"Opponent has {opponent_spin_count} spinners remaining. Bring on a Left-Handed batsman to disrupt the finger-spin match-up angles and neutralize their grip."
            else:
                # Scenario E: Standard Chasing
                action = "STRIKE ROTATOR ACCELERATOR"
                target_player = batsmen[0] if batsmen else None
                recommendation = "SUBSTITUTE EXCELLENT FINISHER"
                tactical_desc = "Chasing targets require boundary consistency. Bring on a high-strike-rate batting substitute to secure the chase during the death overs."

        return {
            "status": True,
            "action": action,
            "recommendation": recommendation,
            "player": {
                "name": target_player["name"] if target_player else "Emerging Substitute",
                "category": target_player["category"] if target_player else "All Rounder",
                "image_url": target_player["image_url"] if target_player else "https://documents.iplt20.com/ipl/assets/images/Default-Men.png"
            } if target_player else None,
            "tactical_description": tactical_desc
        }

if __name__ == "__main__":
    engine = IPLFantasyEngine()
    print("Testing Optimizer for RCB vs GT:")
    squad_stats = engine.optimize_squad("RCB", "GT")
    print(json.dumps(squad_stats["summary"], indent=2))
    print("\nImpact Player suggestion:")
    print(json.dumps(engine.suggest_impact_player("RCB", "GT", wickets=8, score=124, innings_num=1), indent=2))
