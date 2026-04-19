import asyncio
import os
from playwright.async_api import async_playwright
import shutil

async def run_scraper():
    base_url = "https://pitfootball.com"
    start_url = f"{base_url}/league/pit-football/"
    
    # --- UNIFIED PATH SETUP ---
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_folder = os.path.join(base_dir, 'scraped_schedules')

    # Environment variables
    raw_ids = os.getenv("SEASON_IDS", "S26")
    season_ids = [s.strip() for s in raw_ids.split(",") if s.strip()]
    
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Targeting root-level directory: {output_folder}")

    async with async_playwright() as p:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()
        
        for s_id in season_ids:
            print(f"\n🚀 STARTING SEASON: {s_id}")
            
            # 1. Map the Season Structure (Run once per season)
            # We go to the main page to find all league/division links
            await page.goto(start_url)
            await page.select_option('select[name="season_id"]', value=s_id)
            await page.wait_for_load_state("networkidle")
            
            try:
                trigger = page.locator(".bw-trigger:has-text('Divisions')")
                await trigger.wait_for(state="visible", timeout=8000)
                await trigger.click()
            except Exception as e:
                print(f"Skipping {s_id}: Divisions menu not found.")
                continue

            # Identify all Leagues and their Divisions via DOM mapping
            # This extracts the data without needing to hover/click repeatedly
            leagues = page.locator(".multi-dropdown-parent")
            league_count = await leagues.count()
            all_division_tasks = []

            for i in range(league_count):
                league = leagues.nth(i)
                league_name = (await league.locator("span[x-text='category']").first.inner_text()).replace(" ", "_").strip()
                
                # Find all links inside this league's sub-menu
                division_links = league.locator("ul.multi-dropdown-sublevel a[href*='division/']")
                div_count = await division_links.count()
                
                for j in range(div_count):
                    link = division_links.nth(j)
                    div_name = await link.inner_text()
                    div_path = await link.get_attribute("href")
                    
                    # Construct the direct schedule URL
                    # Logic: /division/123/overview -> /division/123/schedule
                    schedule_path = div_path.replace('overview', 'schedule')
                    target_url = f"{start_url}{schedule_path}"
                    
                    all_division_tasks.append({
                        "league": league_name,
                        "name": div_name.replace("/", "-").replace(" ", "_").strip(),
                        "url": target_url
                    })

            print(f"Found {len(all_division_tasks)} divisions. Starting direct navigation...")

            # 2. Direct Navigation Scrape
            # Bypasses all menus, clicks, and hovers
            for task in all_division_tasks:
                print(f"  -> Scraping: {task['league']} | {task['name']}")
                
                try:
                    await page.goto(task['url'], wait_until="networkidle", timeout=30000)
                    
                    # Ensure schedule content is loaded
                    try:
                        await page.wait_for_selector("li.grid", timeout=5000)
                    except:
                        pass # No games scheduled yet

                    # Save Regular Season
                    reg_html = await page.content()
                    filename = f"{s_id}_{task['league']}_{task['name']}_REGULAR.html"
                    with open(os.path.join(output_folder, filename), "w", encoding="utf-8") as f:
                        f.write(reg_html)

                    # Check for Playoffs toggle
                    playoff_label = page.locator("label[for='playoff']")
                    if await playoff_label.is_visible():
                        await playoff_label.click()
                        await page.wait_for_load_state("networkidle")
                        
                        p_html = await page.content()
                        p_filename = f"{s_id}_{task['league']}_{task['name']}_PLAYOFFS.html"
                        with open(os.path.join(output_folder, p_filename), "w", encoding="utf-8") as f:
                            f.write(p_html)
                            
                except Exception as e:
                    print(f"      ! Failed to scrape {task['name']}: {e}")

        await browser.close()
        print(f"\n✅ Scrape complete. Files in: {output_folder}")

if __name__ == "__main__":
    asyncio.run(run_scraper())