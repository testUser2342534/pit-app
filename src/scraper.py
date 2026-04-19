Here is the full, standardized version of src/scraper.py.

I have consolidated the path logic to ensure that the scraped_schedules folder is correctly located at the project root. This ensures that the Parser will find the files exactly where the Scraper saved them, resolving the "No game data extracted" error.

Python
import asyncio
import os
from playwright.async_api import async_playwright
import shutil

async def run_scraper():
    base_url = "https://pitfootball.com"
    start_url = f"{base_url}/league/pit-football/"
    
    # --- UNIFIED PATH SETUP ---
    # This identifies the project root (one level up from /src)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_folder = os.path.join(base_dir, 'scraped_schedules')

    # Environment variables
    raw_ids = os.getenv("SEASON_IDS", "")
    season_ids = [s.strip() for s in raw_ids.split(",") if s.strip()]
    
    # Fresh start: Wipe and recreate the output folder
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Targeting root-level directory: {output_folder}")

    async with async_playwright() as p:
        # Masking as a real user to prevent headless blocking
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        browser = await p.chromium.launch(headless=True, slow_mo=500)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()
        
        print(f"Navigating to {start_url}...")
        await page.goto(start_url)
        await page.wait_for_load_state("networkidle")

        for s_id in season_ids:
            print(f"\n🚀 STARTING SEASON: {s_id}")
            await page.select_option('select[name="season_id"]', value=s_id)
            await page.wait_for_load_state("networkidle")

            # Open Divisions menu
            try:
                trigger = page.locator(".bw-trigger:has-text('Divisions')")
                await trigger.wait_for(state="visible", timeout=8000)
                await trigger.click()
            except Exception as e:
                print(f"Skipping {s_id}: Divisions menu not found. {e}")
                continue
            
            # Identify Leagues
            leagues_locator = page.locator(".multi-dropdown-parent")
            league_count = await leagues_locator.count()

            for i in range(league_count): 
                # Re-locate league to avoid stale element errors
                league = page.locator(".multi-dropdown-parent").nth(i)
                league_name_raw = await league.locator("span[x-text='category']").first.inner_text()
                league_name = league_name_raw.replace(" ", "_").strip()
                
                print(f"\n  League: {league_name}")
                await league.hover()
                await page.wait_for_timeout(2000) 

                # Collect division metadata
                division_links = league.locator("ul.multi-dropdown-sublevel a[href*='division/']")
                div_count = await division_links.count()
                
                div_items = []
                for j in range(div_count):
                    link = division_links.nth(j)
                    div_items.append({
                        "name": await link.inner_text(),
                        "path": await link.get_attribute("href")
                    })

                # Process every division in the league
                for div in div_items:
                    safe_div_name = div['name'].replace("/", "-").replace(" ", "_").strip()
                    target_url = f"{start_url}{div['path'].replace('overview', 'schedule')}"
                    
                    print(f"    -> Scraping: {div['name']}")
                    await page.goto(target_url)
                    
                    try:
                        # Wait for the schedule list to render
                        await page.wait_for_selector("li.grid", timeout=8000)
                    except:
                        pass # Continue if no games exist

                    # Capture Regular Season
                    reg_html = await page.content()
                    reg_filename = os.path.join(output_folder, f"{s_id}_{league_name}_{safe_div_name}_REGULAR.html")
                    with open(reg_filename, "w", encoding="utf-8") as f:
                        f.write(reg_html)

                    # Capture Playoffs if toggle exists
                    playoff_label = page.locator("label[for='playoff']")
                    if await playoff_label.is_visible():
                        await playoff_label.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(2000) 
                        
                        playoff_html = await page.content()
                        p_filename = os.path.join(output_folder, f"{s_id}_{league_name}_{safe_div_name}_PLAYOFFS.html")
                        with open(p_filename, "w", encoding="utf-8") as f:
                            f.write(playoff_html)

                    # --- STABILITY RESET ---
                    await page.goto(start_url)
                    await page.select_option('select[name="season_id"]', value=s_id)
                    await page.wait_for_load_state("networkidle")
                    
                    try:
                        trigger = page.locator(".bw-trigger:has-text('Divisions')")
                        await trigger.wait_for(state="visible", timeout=8000)
                        await trigger.click()
                        
                        current_league = page.locator(".multi-dropdown-parent").nth(i)
                        await current_league.wait_for(state="visible", timeout=2000)
                        await current_league.hover()
                        await page.wait_for_timeout(1000)
                    except Exception as e:
                        print(f"      ! Stability Reset Failed: {e}")
                        continue

        await browser.close()
        print(f"\n✅ Full scrape complete. Files saved in: {output_folder}")

if __name__ == "__main__":
    asyncio.run(run_scraper())