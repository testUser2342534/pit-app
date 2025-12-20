import os
import csv
from datetime import datetime
from bs4 import BeautifulSoup

def format_pit_date(date_str, year="2025"):
    """Converts 'Sat Oct 18' + '2025' to '2025-10-18'"""
    try:
        # Clean the string: Sat Oct 18 -> Oct 18
        clean_date = " ".join(date_str.split()[1:])
        # Parse and add year
        date_obj = datetime.strptime(f"{clean_date} {year}", "%b %d %Y")
        return date_obj.strftime("%Y-%m-%d")
    except:
        return date_str

def parse_schedules():
    folder = 'scraped_schedules'
    master_data = []

    if not os.listdir(folder):
        print("No files found in folder.")
        return

    for filename in os.listdir(folder):
        if not filename.endswith('.html'):
            continue
            
        parts = filename.replace('.html', '').split('_')
        league = parts[0]
        schedule_type = parts[-1] 
        division = "_".join(parts[1:-1])

        with open(os.path.join(folder, filename), 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        games = soup.select('section ul li.grid')
        
        for game in games:
            try:
                spans = game.select('span.text-xxs')
                teams = game.select('a.text-xs b')
                scores = game.select('span.text-xs.font-bold')
                location = game.select_one('a.underline b')

                raw_date = spans[0].get_text(strip=True) if len(spans) > 0 else "N/A"
                formatted_date = format_pit_date(raw_date)

                game_info = {
                    "Date": formatted_date,
                    "Time": spans[1].get_text(strip=True) if len(spans) > 1 else "N/A",
                    "League": league,
                    "Division": division,
                    "Type": schedule_type,
                    "Away_Team": teams[0].get_text(strip=True) if len(teams) > 0 else "N/A",
                    "Away_Score": scores[0].get_text(strip=True) if len(scores) > 0 else "",
                    "Home_Team": teams[1].get_text(strip=True) if len(teams) > 1 else "N/A",
                    "Home_Score": scores[1].get_text(strip=True) if len(scores) > 1 else "",
                    "Location": location.get_text(strip=True) if location else "N/A"
                }
                master_data.append(game_info)
            except Exception as e:
                print(f"Error parsing game in {filename}: {e}")

    # Sort by Date and Time
    master_data.sort(key=lambda x: (x['Date'], x['Time']))

    with open('data/compiled_schedule.csv', 'w', newline='', encoding='utf-8') as f:
        keys = master_data[0].keys()
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(master_data)

    print(f"Compiled {len(master_data)} games into compiled_schedule.csv")

if __name__ == "__main__":
    parse_schedules()