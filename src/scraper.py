import asyncio
import os
from playwright.async_api import async_playwright

async def run_scraper():
    base_url = "https://pitfootball.com"
    start_url = f"{base_url}/league/pit-football/"
    
    if not os.path.exists('scraped_schedules'):
        os.makedirs('scraped_schedules')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        print(f"Navigating to {start_url}...")
        await page.goto(start_url)
        await page.wait_for_load_state("networkidle")

        # 1. Select the Season
        await page.select_option('select[name="season_id"]', value="F25")
        await page.wait_for_load_state("networkidle")

        # 2. Open the main "Divisions" menu
        await page.click(".bw-trigger:has-text('Divisions')")
        
        # 3. Find the League Categories
        leagues = page.locator(".multi-dropdown-parent")
        
        # --- LIMIT: Only the first league ---
        for i in range(1): 
            league = leagues.nth(i)
            league_name_raw = await league.locator("span[x-text='category']").first.inner_text()
            league_name = league_name_raw.replace(" ", "_").strip()
            
            print(f"\nTesting League: {league_name}")

            await league.hover()
            await page.wait_for_timeout(500) 

            # 4. Grab the Division links
            division_links = league.locator("ul.multi-dropdown-sublevel a[href*='division/']")
            
            div_items = []
            for j in range(await division_links.count()):
                link = division_links.nth(j)
                div_items.append({
                    "name": await link.inner_text(),
                    "path": await link.get_attribute("href")
                })

            # --- LIMIT: Only the first 5 divisions ---
            for div in div_items[:5]:
                safe_div_name = div['name'].replace("/", "-").replace(" ", "_").strip()
                target_url = f"{start_url}{div['path'].replace('overview', 'schedule')}"
                
                print(f"  -> Testing Div: {div['name']}")
                await page.goto(target_url)
                
                try:
                    await page.wait_for_selector("section ul li.grid", timeout=8000)
                except:
                    print(f"     ! Warning: Rows not found for {div['name']}")

                # Save Regular Season
                reg_html = await page.content()
                reg_filename = f"scraped_schedules/{league_name}_{safe_div_name}_REGULAR.html"
                with open(reg_filename, "w", encoding="utf-8") as f:
                    f.write(reg_html)

                # Playoff Logic
                playoff_label = page.locator("label[for='playoff']")
                if await playoff_label.is_visible():
                    print(f"     -> Capturing Playoffs...")
                    await playoff_label.click()
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(3000) 
                    
                    playoff_html = await page.content()
                    p_filename = f"scraped_schedules/{league_name}_{safe_div_name}_PLAYOFFS.html"
                    with open(p_filename, "w", encoding="utf-8") as f:
                        f.write(playoff_html)

                # Reset: Go back and re-open menu
                await page.goto(start_url)
                await page.click(".bw-trigger:has-text('Divisions')")
                await leagues.nth(i).hover()
                await page.wait_for_timeout(300)

        await browser.close()
        print("\nTest run complete.")

if __name__ == "__main__":
    asyncio.run(run_scraper())