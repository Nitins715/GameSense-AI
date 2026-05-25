import urllib.request
import zipfile
import io
import os
import json
import glob

ZIP_URL = "https://cricsheet.org/downloads/ipl_json.zip"
TARGET_DIR = "ipl_json_data"

def download_and_extract():
    print("====================================================")
    print("        IPL Ball-by-Ball JSON Data Downloader       ")
    print("====================================================\n")
    
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        
    print(f"[Info] Downloading full IPL JSON dataset from Cricsheet...")
    print(f"       Source: {ZIP_URL}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = urllib.request.Request(ZIP_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            zip_data = response.read()
            print(f"[Success] Download complete! Size: {len(zip_data) / (1024 * 1024):.2f} MB")
            
            print(f"[Info] Extracting zip contents to '{TARGET_DIR}'...")
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                zip_ref.extractall(TARGET_DIR)
            print(f"[Success] Successfully extracted all match files!")
            
    except Exception as e:
        print(f"[Error] Failed to download/extract dataset: {e}")
        return False
    return True

def inspect_sample_match():
    # Find all json files in the extracted directory (excluding metadata/readme files)
    match_files = glob.glob(os.path.join(TARGET_DIR, "[0-9]*.json"))
    
    if not match_files:
        print("[Error] No match files found in extracted directory.")
        return
        
    print(f"\n[Info] Total match files extracted: {len(match_files)}")
    
    # Pick the first match file to inspect
    sample_file = match_files[0]
    print(f"[Info] Loading sample match file: {os.path.basename(sample_file)}\n")
    
    with open(sample_file, "r", encoding="utf-8") as f:
        match_data = json.load(f)
        
    # Print Match Information
    info = match_data.get("info", {})
    teams = info.get("teams", [])
    outcome = info.get("outcome", {})
    winner = outcome.get("winner", "No Result")
    by = outcome.get("by", {})
    by_str = f"by {list(by.values())[0]} {list(by.keys())[0]}" if by else ""
    venue = info.get("venue", "N/A")
    date = info.get("dates", ["N/A"])[0]
    
    print("=" * 60)
    print("                 SAMPLE MATCH DETAILS               ")
    print("=" * 60)
    print(f" Match Date: {date}")
    print(f" Venue     : {venue}")
    print(f" Teams     : {teams[0]} vs {teams[1]}")
    print(f" Result    : {winner} won {by_str}")
    print("=" * 60)
    
    # Inspect Ball-by-Ball structure
    innings = match_data.get("innings", [])
    if not innings:
        print("[Warning] No innings data found in this match file.")
        return
        
    # Get 1st ball of the 1st innings
    first_innings = innings[0]
    first_innings_name = first_innings.get("team", "Unknown Team")
    overs = first_innings.get("overs", [])
    
    print(f"\nBALL-BY-BALL STRUCTURE (First Innings - {first_innings_name}):")
    print(f"Showing the first 3 deliveries of the match as a structured reference:")
    
    delivery_count = 0
    for over_data in overs:
        over_num = over_data.get("over", 0)
        deliveries = over_data.get("deliveries", [])
        
        for d_idx, details in enumerate(deliveries):
            delivery_count += 1
            ball_num = f"{over_num}.{d_idx + 1}"
            
            print(f"\n--- Ball: {ball_num} ---")
            print(f"  Batter      : {details.get('batter')}")
            print(f"  Bowler      : {details.get('bowler')}")
            print(f"  Non-striker : {details.get('non_striker')}")
            
            runs = details.get("runs", {})
            print(f"  Runs        : Batter: {runs.get('batter')}, Extras: {runs.get('extras')}, Total: {runs.get('total')}")
            
            if "extras" in details:
                print(f"  Extras Info : {details.get('extras')}")
                
            if "wickets" in details:
                print(f"  *** WICKET! ***")
                for w in details.get("wickets", []):
                    print(f"    Player Out: {w.get('player_out')} ({w.get('kind')})")
            
            if delivery_count >= 3:
                break
        if delivery_count >= 3:
            break

    print("\n" + "=" * 60)
    print(f"[Info] Every match file has this detailed JSON schema!")
    print(f"[Info] Files are named by their official ESPNCricinfo match ID (e.g. 335982.json)")
    print("=" * 60)

def main():
    if download_and_extract():
        inspect_sample_match()

if __name__ == "__main__":
    main()
