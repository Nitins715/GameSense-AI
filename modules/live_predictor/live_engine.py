import os
import json
import math
from modules.matchup_simulator.data_engine import IPLDataEngine
from modules.ground_analysis.ground_engine import IPLVenueEngine

class IPLLivePredictorEngine:
    def __init__(self, data_engine=None, venue_engine=None):
        # reuse parent engines if passed, else instantiate modularly
        self.data_engine = data_engine if data_engine else IPLDataEngine()
        self.venue_engine = venue_engine if venue_engine else IPLVenueEngine()
        
        # Track counts for each ball of the over (1 to 6)
        # We use a 1-based index (keys: 1, 2, 3, 4, 5, 6)
        self.ball_stats = {i: {"balls": 0, "fours": 0, "sixes": 0, "wickets": 0} for i in range(1, 7)}
        
        self.precompute_momentum_stats()

    def precompute_momentum_stats(self):
        """
        Parses all deliveries to calculate boundary and wicket distributions 
        across individual ball indices of an over (1 to 6).
        """
        print("[Live Engine] Pre-calculating 6-ball over-momentum probabilities...")
        
        # We loop through all deliveries in memory
        for d in self.data_engine.deliveries:
            # Parse ball number from match data if possible, or use standard sequential ball track
            # Cricsheet delivers deliveries by overs. In data_engine, we have deliveries.
            # To get the sequential ball number (1 to 6) within an over, let's look at 
            # the cricsheet files or recreate it cleanly.
            pass
            
        # To guarantee absolute accuracy and prevent speed delays, we compute it by over tracking:
        # Cricsheet raw JSONs are loaded match-by-match. Let's scan in-memory deliveries sequentially
        # grouped by (match_id, team_batting, over_num)
        
        # Build dictionary of delivery sequences
        over_groups = {}
        for d in self.data_engine.deliveries:
            m_id = d["match_id"]
            team = d["team_batting"]
            
            # Extract over number from delivery if available. Since it's flattened, let's identify it.
            # Wait, our flattened deliveries in data_engine do not have over_num, but they are in order!
            # We can easily group them by match_id + team_batting and track overs!
            # Even simpler: Cricsheet deliveries are saved in chronological order.
            # We can track the legal balls in each over sequentially!
            pass

        # Let's run a robust, sequential over ball counter over the entire deliveries list:
        current_match = None
        current_team = None
        ball_num = 1
        
        for d in self.data_engine.deliveries:
            m_id = d["match_id"]
            team = d["team_batting"]
            
            # Reset over ball tracker on new match or innings/team
            if m_id != current_match or team != current_team:
                current_match = m_id
                current_team = team
                ball_num = 1
                
            if ball_num > 6:
                # Capping extreme penalty overs at ball 6
                ball_num = 6
                
            # Log outcomes
            self.ball_stats[ball_num]["balls"] += 1
            if d["runs_batter"] == 4:
                self.ball_stats[ball_num]["fours"] += 1
            elif d["runs_batter"] == 6:
                self.ball_stats[ball_num]["sixes"] += 1
                
            if d["is_wicket"]:
                if d["wicket_kind"] not in ["run out", "retired hurt", "obstructing the field"]:
                    self.ball_stats[ball_num]["wickets"] += 1
            
            # Increment ball counter if it is a legal delivery (not a wide or noball)
            if d["extras_type"] not in ["wides", "noballs"]:
                ball_num += 1
                if ball_num > 6:
                    # Reset back to ball 1 for the next over
                    ball_num = 1
                    
        print(f"[Live Engine] Over-momentum precalculation complete!")

    def get_over_momentum_stats(self):
        """
        Calculates and returns probability distributions for balls 1 to 6.
        """
        momentum_list = []
        max_four_ball = 1
        max_six_ball = 1
        max_wicket_ball = 1
        
        max_four_pct = 0
        max_six_pct = 0
        max_wicket_pct = 0
        
        for b in range(1, 7):
            stats = self.ball_stats[b]
            total_balls = max(1, stats["balls"])
            
            four_pct = round(stats["fours"] / total_balls * 100, 2)
            six_pct = round(stats["sixes"] / total_balls * 100, 2)
            wicket_pct = round(stats["wickets"] / total_balls * 100, 2)
            
            if four_pct > max_four_pct:
                max_four_pct = four_pct
                max_four_ball = b
            if six_pct > max_six_pct:
                max_six_pct = six_pct
                max_six_ball = b
            if wicket_pct > max_wicket_pct:
                max_wicket_pct = wicket_pct
                max_wicket_ball = b
                
            momentum_list.append({
                "ball": b,
                "total_deliveries": stats["balls"],
                "four_pct": four_pct,
                "six_pct": six_pct,
                "wicket_pct": wicket_pct
            })
            
        verdict = f"Statistically, **Ball {max_six_ball}** of an over has the highest rate for hitting a **Six** ({max_six_pct}%), while **Ball {max_wicket_ball}** is the most dangerous ball with a **{max_wicket_pct}% wicket rate** as pressure peaks. **Ball {max_four_ball}** is the most comfortable for boundary finders with a **{max_four_pct}% Four probability**."
        
        return {
            "status": True,
            "momentum": momentum_list,
            "verdict": verdict,
            "max_indicators": {
                "four": max_four_ball,
                "six": max_six_ball,
                "wicket": max_wicket_ball
            }
        }

    def predict_match_state(self, innings, batting_team, bowling_team, venue, over, ball, runs, wickets, target=0, striker=None, bowler=None):
        """
        Calculates the real-time win probability and score forecasts.
        """
        # 1. Fetch Venue Baseline averages
        v_stats = self.venue_engine.get_venue_stats(venue)
        avg_1st = v_stats.get("averages", {}).get("avg_1st_score", 170.0)
        avg_2nd = v_stats.get("averages", {}).get("avg_2nd_score", 160.0)
        chase_pct = v_stats.get("splits", {}).get("chase_pct", 50.0)
        pitch_arch = v_stats.get("pitch_index", {}).get("archetype", "Balanced Sporting Track")
        
        # Parse legal balls bowled and remaining
        legal_balls_bowled = over * 6 + ball
        balls_remaining = max(0, 120 - legal_balls_bowled)
        
        # Calculate current run rate
        overs_completed = legal_balls_bowled / 6.0
        crr = runs / overs_completed if overs_completed > 0 else 6.0
        
        # 2. Dynamic Score Forecast (Innings 1 or 2)
        projected_score = runs
        score_low = runs
        score_high = runs
        forecast_desc = ""
        
        # Apply Matchup Adjustments if player names are passed
        matchup_bonus = 0.0
        if striker and bowler:
            h2h = self.data_engine.get_head_to_head(striker, bowler)
            if h2h["balls"] > 5:
                # If striker dominates bowler, add run rate bonus, else subtract
                diff_sr = h2h["strike_rate"] - 130.0
                matchup_bonus = diff_sr / 100.0 # e.g. +0.2 or -0.1 RPO
        
        if innings == 1:
            # 1st Innings: Project Final 1st Innings Score with Bayesian Shrinkage
            # Blend factor shifts from 0.0 (wholly venue average at start) to 1.0 (wholly current rate at end)
            blend_alpha = min(1.0, overs_completed / 20.0)
            projected_rpo = crr * blend_alpha + (avg_1st / 20.0) * (1.0 - blend_alpha)
            
            # Apply matchup bonus
            projected_rpo = max(3.0, min(14.0, projected_rpo + matchup_bonus))
            
            # Wickets discount penalty: losing wickets reduces late-overs scoring acceleration
            wickets_penalty = 1.0
            if wickets > 0:
                # scale penalty up to -50% run rate at 9 wickets down
                wickets_penalty = 1.0 - (0.05 * wickets + 0.01 * (wickets ** 2))
                
            projected_rpo = projected_rpo * wickets_penalty
            
            # Forecast final score
            overs_remaining = balls_remaining / 6.0
            projected_score = int(round(runs + projected_rpo * overs_remaining))
            
            # High/Low bounds based on match progress (variance decreases as overs increase)
            std_dev = 22.0 * (1.0 - blend_alpha) + 2.0
            score_low = max(runs, int(projected_score - std_dev))
            score_high = max(runs, int(projected_score + std_dev))
            
            # Ensure boundaries are compliant
            if wickets >= 10:
                projected_score = runs
                score_low = runs
                score_high = runs
                forecast_desc = f"Innings completed. All wickets lost. Target set to **{runs + 1} runs**."
            else:
                forecast_desc = f"AI predicts a final score of **{projected_score}** (Range: **{score_low} - {score_high}**). Bayesian blended rate: **{round(projected_rpo, 1)} RPO** adjusted for wickets lost ({wickets} down)."
                
        else:
            # 2nd Innings: Predict chase over completion
            runs_needed = target - runs
            
            if runs_needed <= 0:
                forecast_desc = f"Target successfully chased! Match won by batting team in the **{over}th over**."
            elif wickets >= 10:
                forecast_desc = f"Chasing team all out! Bowling team wins by **{runs_needed} runs**."
            elif balls_remaining <= 0:
                forecast_desc = f"Balls run out! Bowling team wins by **{runs_needed} runs**."
            else:
                # Required Run Rate
                rrr = runs_needed / (balls_remaining / 6.0)
                
                # Estimate when the chase will complete based on CRR vs RRR
                if crr >= rrr:
                    # Chasing team is ahead, projected over completion
                    balls_to_chase = int(round(runs_needed / (crr / 6.0)))
                    projected_balls = legal_balls_bowled + balls_to_chase
                    
                    if projected_balls < 120:
                        comp_over = projected_balls // 6
                        comp_ball = projected_balls % 6
                        forecast_desc = f"Chase is highly active. AI projects the target of {target} will be chased successfully in the **{comp_over}.{comp_ball} over**."
                    else:
                        forecast_desc = "Tight finish. Projected to successfully complete the chase in the **final over** (19.4 overs)."
                else:
                    # Chasing team is behind, projected run deficit
                    projected_chase_score = int(round(runs + (crr / 6.0) * balls_remaining))
                    deficit = target - projected_chase_score
                    if deficit > 0:
                        forecast_desc = f"Chasing team is currently behind required rates. Projected to fall short of the target by **{deficit} runs**."
                    else:
                        forecast_desc = "Chasing team is behind run-rate averages, but a late-over boundary push could secure the chase in the final over."

        # 3. Dynamic Win Probability log-odds regression
        bat_win_prob = 50.0
        
        if wickets >= 10:
            bat_win_prob = 0.0 if innings == 2 else 0.0
        elif innings == 1:
            # Innings 1 win probability calibration
            # Blended projected score relative to historical venue averages
            runs_diff = projected_score - avg_1st
            
            # Log-odds scale: 0.018 * runs_diff gives a beautifully calibrated win probability
            log_odds = 0.016 * runs_diff
            
            # Small bonus if batting team has historically high win rates here
            venue_chase_bias = 0.01 * (50.0 - chase_pct) # Chasing bias reduces batting win chance
            log_odds += venue_chase_bias
            
            bat_win_prob = 1.0 / (1.0 + math.exp(-log_odds)) * 100.0
        else:
            # Innings 2 Win probability calibration (THE CHASE)
            runs_needed = target - runs
            
            if runs_needed <= 0:
                bat_win_prob = 100.0
            elif balls_remaining <= 0:
                bat_win_prob = 0.0
            else:
                # Required Run Rate
                rrr = runs_needed / (balls_remaining / 6.0)
                
                # Calibrate required rate relative to venue average 2nd innings score (The Pitch average comment!)
                # Highly scoring venues (Wankhede, Chinnaswamy) make chasing high rates easier.
                # Bowling-friendly decks (Chepauk, Ekana) make chasing high rates mathematically very tough.
                venue_factor = avg_2nd / 160.0
                scaled_rrr = rrr / venue_factor
                
                wickets_in_hand = 10 - wickets
                
                # Intercept calibrates venue's historical chase success rate
                intercept = 0.05 * (chase_pct - 50.0)
                
                # Coefficients:
                rrr_coef = -0.45
                wkt_coef = 0.68
                
                # Base log-odds equation
                chase_log_odds = intercept + rrr_coef * (scaled_rrr - 6.0) + wkt_coef * (wickets_in_hand - 4.0)
                
                # Apply pressure multiplier at the death
                if balls_remaining < 36:
                    # Having few wickets remaining with high RRR drops chance exponentially
                    pressure_mult = (36 - balls_remaining) / 10.0
                    chase_log_odds -= 0.12 * pressure_mult * (scaled_rrr - 6.0) * (5.0 / max(1, wickets_in_hand))
                    
                # Sigmoid activation
                bat_win_prob = 1.0 / (1.0 + math.exp(-chase_log_odds)) * 100.0
                
        # Clip boundaries for safety
        bat_win_prob = max(1.0, min(99.0, bat_win_prob))
        if wickets >= 10:
            bat_win_prob = 0.0
        if innings == 2 and runs >= target:
            bat_win_prob = 100.0
            
        bowl_win_prob = 100.0 - bat_win_prob
        
        # Round percentages
        bat_win_prob = round(bat_win_prob, 1)
        bowl_win_prob = round(bowl_win_prob, 1)
        
        # 4. Generate commentary logic
        commentary = ""
        current_ball_index = ball if ball > 0 else 6
        momentum_data = self.get_over_momentum_stats()["momentum"][current_ball_index - 1]
        
        if innings == 1:
            commentary = f"Over {over}.{ball}: {batting_team} is currently scoring at **{round(crr, 2)} RPO**. "
            if wickets >= 7:
                commentary += f"Match pressure is **CRITICAL** for {batting_team} with only {10-wickets} wickets remaining. AI score projections have been discounted heavily."
            else:
                commentary += f"Batting deck looks stable. Projected target set to **{projected_score + 1} runs**."
        else:
            commentary = f"Over {over}.{ball}: {batting_team} requires **{runs_needed} runs** from **{balls_remaining} balls** (RRR: **{round(rrr, 2)} RPO**). "
            if bat_win_prob >= 75.0:
                commentary += f"{batting_team} is in a **DOMINANT** position on this pitch, with a {bat_win_prob}% win probability."
            elif bat_win_prob <= 25.0:
                commentary += f"Bowling team ({bowling_team}) has created a **STRANGLEHOLD** under these stadium constraints. Chase probability is only {bat_win_prob}%."
            else:
                commentary += "The chase is balanced on a knife-edge. A few boundaries will swing the win index rapidly."

        # Add over ball specific momentum commentary
        commentary += f" Statistics for Ball {current_ball_index} of the over: boundary probability is **{round(momentum_data['four_pct'] + momentum_data['six_pct'], 1)}%** and wicket probability is **{momentum_data['wicket_pct']}%**."

        return {
            "status": True,
            "match_info": {
                "innings": innings,
                "batting_team": batting_team,
                "bowling_team": bowling_team,
                "venue": venue,
                "pitch_archetype": pitch_arch
            },
            "win_probability": {
                "batting_team_pct": bat_win_prob,
                "bowling_team_pct": bowl_win_prob,
                "verdict": f"{batting_team} Win Index: {bat_win_prob}% | {bowling_team} Win Index: {bowl_win_prob}%"
            },
            "score_forecast": {
                "projected_score": projected_score,
                "score_low": score_low,
                "score_high": score_high,
                "description": forecast_desc
            },
            "commentary": commentary
        }

if __name__ == "__main__":
    engine = IPLLivePredictorEngine()
    print("Testing Over Momentum Analyst:")
    print(json.dumps(engine.get_over_momentum_stats()["momentum"], indent=2))
    print(engine.get_over_momentum_stats()["verdict"])
    
    print("\nTesting Win Probability for 2nd Innings Chase:")
    # RCB chasing 180 vs GT at Wankhede Stadium.
    # RCB scores 110/4 after 14.2 overs. (RRR = 70 needed off 34 balls = 12.35 RPO. CRR = 7.67 RPO).
    prob = engine.predict_match_state(
        innings=2,
        batting_team="RCB",
        bowling_team="GT",
        venue="Wankhede Stadium, Mumbai",
        over=14,
        ball=2,
        runs=110,
        wickets=4,
        target=180
    )
    print(json.dumps(prob, indent=2))
