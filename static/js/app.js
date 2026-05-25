// GameSense AI - Interactive Frontend Controller

document.addEventListener("DOMContentLoaded", () => {
    let playersDatabase = [];
    const simulatedBatter = document.getElementById("batter-input");
    const simulatedBowler = document.getElementById("bowler-input");
    const batterDropdown = document.getElementById("batter-dropdown");
    const bowlerDropdown = document.getElementById("bowler-dropdown");
    const simulateBtn = document.getElementById("simulate-btn");
    const loadingSpinner = document.getElementById("loading-spinner");
    const dashboard = document.getElementById("matchup-dashboard");

    // 1. Fetch Players Database on Startup
    fetch("/api/players")
        .then(response => response.json())
        .then(data => {
            playersDatabase = data;
            console.log(`[GameSense] Loaded ${playersDatabase.length} players into search index.`);
        })
        .catch(err => console.error("[Error] Failed to fetch players registry:", err));

    // 2. Setup Autocomplete Dropdowns
    setupAutocomplete(simulatedBatter, batterDropdown, "Batsman");
    setupAutocomplete(simulatedBowler, bowlerDropdown, "Bowler");

    function setupAutocomplete(inputElement, dropdownElement, roleFilter) {
        inputElement.addEventListener("input", () => {
            const query = inputElement.value.trim().toLowerCase();
            dropdownElement.innerHTML = "";
            
            if (query.length < 2) {
                dropdownElement.classList.add("hidden");
                return;
            }

            // Filter matching players (fuzzy match by name, also check role filter roughly)
            const matches = playersDatabase.filter(p => {
                const nameMatches = p.name.toLowerCase().includes(query);
                // Batsmen can also be all-rounders or wicket-keepers, bowlers can be all-rounders
                if (roleFilter === "Batsman") {
                    return nameMatches && (p.category === "Batsman" || p.category === "All Rounder" || p.category === "Wicket Keeper");
                } else {
                    return nameMatches && (p.category === "Bowler" || p.category === "All Rounder");
                }
            }).slice(0, 8); // Limit to top 8 matches

            if (matches.length === 0) {
                dropdownElement.classList.add("hidden");
                return;
            }

            matches.forEach(player => {
                const item = document.createElement("div");
                item.className = "autocomplete-item";
                item.innerHTML = `
                    <img src="${player.image_url}" alt="${player.name}" class="item-thumb" onerror="this.src='https://documents.iplt20.com/ipl/assets/images/Default-Men.png'">
                    <div class="item-info">
                        <span class="item-name">${player.name}</span>
                        <span class="item-sub">${player.team_code} — ${player.category}</span>
                    </div>
                `;
                item.addEventListener("click", () => {
                    inputElement.value = player.name;
                    dropdownElement.classList.add("hidden");
                });
                dropdownElement.appendChild(item);
            });

            dropdownElement.classList.remove("hidden");
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (!inputElement.contains(e.target) && !dropdownElement.contains(e.target)) {
                dropdownElement.classList.add("hidden");
            }
        });
    }

    // 3. Preset Quick Battles
    document.querySelectorAll(".preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const batter = btn.getAttribute("data-batter");
            const bowler = btn.getAttribute("data-bowler");
            
            simulatedBatter.value = batter;
            simulatedBowler.value = bowler;
            
            // Trigger simulation automatically!
            runMatchupSimulation();
        });
    });

    // 4. Run Simulation
    simulateBtn.addEventListener("click", runMatchupSimulation);

    function runMatchupSimulation() {
        const batter = simulatedBatter.value.trim();
        const bowler = simulatedBowler.value.trim();

        if (!batter || !bowler) {
            alert("Please select both a Batter and a Bowler to run the simulation!");
            return;
        }

        // UI Transitions: Show spinner, hide dashboard
        loadingSpinner.classList.remove("hidden");
        dashboard.classList.add("hidden");

        // Scroll to loading area smoothly
        loadingSpinner.scrollIntoView({ behavior: "smooth" });

        // Query API
        const url = `/api/matchup?batter=${encodeURIComponent(batter)}&bowler=${encodeURIComponent(bowler)}`;

        fetch(url)
            .then(res => res.json())
            .then(data => {
                if (!data.status) {
                    alert(`Simulation Error: ${data.error}`);
                    loadingSpinner.classList.add("hidden");
                    return;
                }
                
                // Populate Dashboard Cards
                populateDashboard(data);
                
                // Hide spinner, show dashboard
                loadingSpinner.classList.add("hidden");
                dashboard.classList.remove("hidden");
                
                // Smooth entry transition scroll
                dashboard.scrollIntoView({ behavior: "smooth" });
            })
            .catch(err => {
                console.error("[Error] Simulation failed:", err);
                alert("An error occurred during simulation. Please try again.");
                loadingSpinner.classList.add("hidden");
            });
    }

    // 5. Populate Web Dashboard elements
    function populateDashboard(data) {
        const b = data.batter;
        const bo = data.bowler;
        const h2h = data.head_to_head;
        const arch = data.archetypes;

        // --- A. Batter Profile Card ---
        document.getElementById("batter-name").textContent = b.name;
        document.getElementById("batter-team").textContent = b.team;
        document.getElementById("batter-dob").textContent = b.dob;
        document.getElementById("batter-stance").textContent = b.stance;
        document.getElementById("batter-role").textContent = b.category;
        
        const batterImg = document.getElementById("batter-img");
        batterImg.src = b.image_url;
        batterImg.onerror = () => batterImg.src = "https://documents.iplt20.com/ipl/assets/images/Default-Men.png";
        
        // Batter Stripe Theme Color
        setTeamColorStripe("batter-stripe", b.team_code);

        // Batter Career Stats
        document.getElementById("batter-career-runs").textContent = b.career.runs !== undefined ? b.career.runs : "0";
        document.getElementById("batter-career-balls").textContent = b.career.balls !== undefined ? b.career.balls : "0";
        document.getElementById("batter-career-avg").textContent = b.career.average !== undefined ? b.career.average : "0.00";
        document.getElementById("batter-career-sr").textContent = b.career.strike_rate !== undefined ? b.career.strike_rate : "0.00";

        // --- B. Bowler Profile Card ---
        document.getElementById("bowler-name").textContent = bo.name;
        document.getElementById("bowler-team").textContent = bo.team;
        document.getElementById("bowler-dob").textContent = bo.dob;
        document.getElementById("bowler-style").textContent = bo.style;
        document.getElementById("bowler-role").textContent = bo.category;
        
        const bowlerImg = document.getElementById("bowler-img");
        bowlerImg.src = bo.image_url;
        bowlerImg.onerror = () => bowlerImg.src = "https://documents.iplt20.com/ipl/assets/images/Default-Men.png";
        
        // Bowler Stripe Theme Color
        setTeamColorStripe("bowler-stripe", bo.team_code);

        // Bowler Career Stats
        document.getElementById("bowler-career-overs").textContent = bo.career.overs !== undefined ? bo.career.overs : "0.0";
        document.getElementById("bowler-career-wickets").textContent = bo.career.wickets !== undefined ? bo.career.wickets : "0";
        document.getElementById("bowler-career-econ").textContent = bo.career.economy !== undefined ? bo.career.economy : "0.00";
        document.getElementById("bowler-career-avg").textContent = bo.career.average !== undefined ? bo.career.average : "0.00";

        // --- C. Head-to-Head Duel Card ---
        document.getElementById("h2h-runs").textContent = h2h.runs;
        document.getElementById("h2h-balls").textContent = h2h.balls;
        document.getElementById("h2h-dismissals").textContent = h2h.dismissals;
        
        document.getElementById("h2h-strike-rate").textContent = h2h.strike_rate;
        document.getElementById("h2h-boundary-pct").textContent = h2h.boundary_pct + "%";
        document.getElementById("h2h-boundaries").textContent = `${h2h.fours} / ${h2h.sixes}`;
        document.getElementById("h2h-dots").textContent = h2h.dots;

        // Calculate Batter Dominance Index
        let dominancePct = 50; // Neutral default
        if (h2h.balls > 0) {
            // Formula balancing Strike Rate and Outs
            const srFactor = Math.min(1.0, h2h.strike_rate / 180.0) * 60;
            const outFactor = Math.max(0.0, 1.0 - (h2h.dismissals / (h2h.balls / 8.0 || 1.0))) * 40;
            dominancePct = Math.round(srFactor + outFactor);
            // Cap between 15% and 85% for balanced visual dials
            dominancePct = Math.max(15, Math.min(85, dominancePct));
        }
        
        // Animate Gauge Needle and Color Arc
        const needle = document.getElementById("win-gauge-needle");
        const gaugeFill = document.getElementById("win-gauge-fill");
        const dominanceLabel = document.getElementById("win-probability-pct");
        
        dominanceLabel.textContent = `${dominancePct}%`;
        
        // Rotate needle from -90deg (0% dominance) to 90deg (100% dominance)
        const rotationAngle = (dominancePct / 100) * 180 - 90;
        needle.style.transform = `rotate(${rotationAngle}deg)`;
        
        // Arc offset animation (circumference of stroke is 126)
        const strokeDashOffset = 126 - (dominancePct / 100) * 126;
        gaugeFill.style.strokeDashoffset = strokeDashOffset;

        // --- D. Dismissal Modes Breakdown ---
        const dismissalContainer = document.getElementById("dismissal-chart-container");
        const dismissalList = document.getElementById("dismissal-list");
        dismissalList.innerHTML = "";

        if (h2h.dismissals > 0 && h2h.dismissal_types) {
            dismissalContainer.style.display = "block";
            
            Object.entries(h2h.dismissal_types).forEach(([kind, count]) => {
                const pct = Math.round((count / h2h.dismissals) * 100);
                const row = document.createElement("div");
                row.className = "dismissal-row";
                row.innerHTML = `
                    <div class="dismissal-header">
                        <span class="dismissal-kind">${capitalizeFirst(kind)}</span>
                        <span class="dismissal-count">${count} (${pct}%)</span>
                    </div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: ${pct}%"></div>
                    </div>
                `;
                dismissalList.appendChild(row);
            });
        } else {
            dismissalContainer.style.display = "none";
        }

        // --- E. Skill vs. Skill Archetypes ---
        const archB = arch.batter_vs_style;
        const archBo = arch.bowler_vs_stance;

        // Label overrides
        document.getElementById("archetype-style-label").textContent = archB.style;
        document.getElementById("archetype-stance-label").textContent = archBo.stance;

        // Populate Batter vs Bowler Style
        document.getElementById("arch-batter-balls").textContent = archB.balls;
        document.getElementById("arch-batter-runs").textContent = archB.runs;
        document.getElementById("arch-batter-outs").textContent = archB.dismissals;
        document.getElementById("arch-batter-avg").textContent = archB.average;
        document.getElementById("arch-batter-sr").textContent = archB.strike_rate;

        // Populate Bowler vs Batter Stance
        document.getElementById("arch-bowler-balls").textContent = archBo.balls_bowled;
        document.getElementById("arch-bowler-runs").textContent = archBo.runs_conceded;
        document.getElementById("arch-bowler-outs").textContent = archBo.wickets;
        document.getElementById("arch-bowler-econ").textContent = archBo.economy;
        document.getElementById("arch-bowler-sr").textContent = archBo.strike_rate;
    }

    // Helpers
    function setTeamColorStripe(elementId, teamCode) {
        const stripe = document.getElementById(elementId);
        const colors = {
            "CSK": "#fdb913", // Gold
            "MI": "#004ba0",  // Blue
            "RCB": "#ec1c24", // Red
            "KKR": "#3a225d", // Purple
            "SRH": "#f26522", // Orange
            "DC": "#0078bc",  // Blue/Red
            "GT": "#0b1e36",  // Midnight Blue
            "LSG": "#005780", // Turquoise
            "PBKS": "#dd1f26", // Red/Silver
            "RR": "#ea1a85"   // Pink
        };
        const color = colors[teamCode] || "#1e3a8a"; // Default dark blue
        stripe.style.backgroundColor = color;
        stripe.style.boxShadow = `0 0 15px ${color}`;
    }

    function capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
});
