import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Ensure images directory exists
        os.makedirs("docs/images", exist_ok=True)
        
        # Node Editor
        page1 = await browser.new_page()
        try:
            await page1.goto("http://localhost:8080", timeout=10000)
            await asyncio.sleep(2) # wait for render
            await page1.screenshot(path="docs/images/node_editor.png", full_page=True)
            print("Captured Node Editor Screenshot")
        except Exception as e:
            print(f"Failed Node Editor: {e}")
            
        # AI Editor
        page2 = await browser.new_page()
        try:
            await page2.goto("http://localhost:8081", timeout=10000)
            await asyncio.sleep(2) # wait for render
            await page2.screenshot(path="docs/images/ai_editor.png", full_page=True)
            print("Captured AI Editor Screenshot")
        except Exception as e:
            print(f"Failed AI Editor: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
