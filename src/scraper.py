import asyncio
import os
from playwright.async_api import async_playwright

async def run_scraper():
    base_url = "https://pitfootball.com"
    start_url = f"{base_url}/league/pit-football/"
    
    season_ids = ["F25"]
    
    # Path setup
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_folder = os.path.join(base_dir, 'scraped_schedules')
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    async with async_playwright() as p:
        # Masking as a real user to prevent headless blocking
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
       ## browser = await p.chromium.launch(
        ##    headless=True, 
        ##    args=["--disable-blink-features=AutomationControlled"]
        ##)
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()
        
        print(f"Navigating to {start_url}...")
        await page.goto(start_url)
        await page.wait_for_load_state("networkidle")

        # Get all Season IDs dynamically
        season_options = await page.locator('select[name="season_id"] option').all()
        ## season_ids = [await opt.get_attribute("value") for opt in season_options if await opt.get_attribute("value")]
        
        for s_id in season_ids:
            print(f"\n🚀 STARTING SEASON: {s_id}")
            await page.select_option('select[name="season_id"]', value=s_id)
            await page.wait_for_load_state("networkidle")

            # Open Divisions menu for the first time in this season
            try:
                await page.click(".bw-trigger:has-text('Divisions')", timeout=8000)
            except:
                print(f"Skipping {s_id}: Divisions menu not found.")
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
                await page.wait_for_timeout(600) 

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
                        await page.wait_for_selector("li.grid", timeout=6000)
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
                        await page.wait_for_timeout(1500) 
                        
                        playoff_html = await page.content()
                        p_filename = os.path.join(output_folder, f"{s_id}_{league_name}_{safe_div_name}_PLAYOFFS.html")
                        with open(p_filename, "w", encoding="utf-8") as f:
                            f.write(playoff_html)

                    # --- STABILITY RESET: Re-prime the menu for the next division ---
                    await page.goto(start_url)
                    await page.select_option('select[name="season_id"]', value=s_id)
                    await page.wait_for_load_state("networkidle")
                    
                    try:
                        # Click divisions menu
                        trigger = page.locator(".bw-trigger:has-text('Divisions')")
                        await trigger.wait_for(state="visible", timeout=5000)
                        await trigger.click()
                        
                        # Re-hover the specific league to keep sub-menu open
                        current_league = page.locator(".multi-dropdown-parent").nth(i)
                        await current_league.wait_for(state="visible", timeout=5000)
                        await current_league.hover()
                        await page.wait_for_timeout(400)
                    except Exception as e:
                        print(f"      ! Stability Reset Failed: {e}")
                        # If UI fails to reset, attempt to recover by proceeding
                        continue

        await browser.close()
        print("\n✅ Full historical scrape complete.")

if __name__ == "__main__":
    asyncio.run(run_scraper())