import os
import csv
import datetime
import pytz # Make sure to add this to your requirements.txt
from datetime import datetime
from bs4 import BeautifulSoup

def format_pit_date(date_str, year="2025"):
    """Converts 'Sat Oct 18' + '2025' to '2025-10-18'"""
    try:
        clean_date = " ".join(date_str.split()[1:])
        date_obj = datetime.strptime(f"{clean_date} {year}", "%b %d %Y")
        return date_obj.strftime("%Y-%m-%d")
    except:
        return date_str

def parse_schedules():
    # --- PATH LOGIC ---
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_folder = os.path.join(base_dir, 'scraped_schedules')
    output_file = os.path.join(base_dir, 'data', 'Fall_2025.csv')
    
    master_data = []
    domain = "https://pitfootball.com"

    # Define Central Timezone
    central_tz = pytz.timezone('US/Central')
    # Get current time in Central and format it
    sync_timestamp = datetime.now(central_tz).strftime('%Y-%m-%d %H:%M:%S')

    if not os.path.exists(input_folder) or not os.listdir(input_folder):
        print(f"No files found in {input_folder}")
        return

    for filename in os.listdir(input_folder):
        if not filename.endswith('.html'):
            continue
            
        parts = filename.replace('.html', '').split('_')
        season = parts[0]
        league = parts[1]
        schedule_type = parts[-1] 
        division = "_".join(parts[2:-1])

        with open(os.path.join(input_folder, filename), 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        games = soup.select('li.grid')
        
        for game in games:
            try:
                spans = game.select('span.text-xxs')
                team_anchor_tags = game.find_all('a', href=lambda x: x and '/teams/' in x)
                scores = game.select('span.text-xs.font-bold')
                location = game.select_one('a.underline b')
                summary_tag = game.find('a', class_='link')

                raw_date = spans[0].get_text(strip=True) if len(spans) > 0 else "N/A"
                
                game_info = {
                    "Date": format_pit_date(raw_date),
                    "Time": spans[1].get_text(strip=True) if len(spans) > 1 else "N/A",
                    "League": league,
                    "Division": division,
                    "Type": schedule_type,
                    "Away_Team": team_anchor_tags[0].get_text(strip=True) if len(team_anchor_tags) > 0 else "N/A",
                    "Away_Link": domain + team_anchor_tags[0]['href'] if len(team_anchor_tags) > 0 else "",
                    "Away_Score": scores[0].get_text(strip=True) if len(scores) > 0 else "",
                    "Home_Team": team_anchor_tags[1].get_text(strip=True) if len(team_anchor_tags) > 1 else "N/A",
                    "Home_Link": domain + team_anchor_tags[1]['href'] if len(team_anchor_tags) > 1 else "",
                    "Home_Score": scores[1].get_text(strip=True) if len(scores) > 1 else "",
                    "Location": location.get_text(strip=True) if location else "N/A",
                    "Summary": domain + summary_tag['href'] if summary_tag else "",
                    "Scraped_At": sync_timestamp  # <--- Added Hidden Column here
                }
                master_data.append(game_info)
            except Exception as e:
                print(f"Error parsing game in {filename}: {e}")

    if not master_data:
        print("No game data extracted.")
        return

    # Sort by Date and Time
    master_data.sort(key=lambda x: (x['Date'], x['Time']), reverse=True)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        keys = master_data[0].keys()
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(master_data)

    print(f"Compiled {len(master_data)} games into {output_file} at {sync_timestamp}")

if __name__ == "__main__":
    parse_schedules()