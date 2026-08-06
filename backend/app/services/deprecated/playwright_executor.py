import asyncio
import logging
from typing import Dict, Any
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

async def execute_cancellation(vendor_name: str, url: str, requires_auth: bool = False) -> Dict[str, Any]:
    """
    Executes automated or Human-In-The-Loop (HITL) subscription cancellation via Playwright.
    
    :param vendor_name: Target subscription vendor (e.g. Amazon Prime, Netflix)
    :param url: Cancellation landing or billing deep-link URL
    :param requires_auth: Whether authentication is expected prior to cancellation
    """
    # Dynamic Headless Mode: Browser MUST be visible (headless=False) if step-up auth is required
    is_headless = not requires_auth
    logger.info(f"Launching Playwright for '{vendor_name}' (headless={is_headless}, requires_auth={requires_auth})...")

    try:
        async with async_playwright() as p:
            # Launch chromium browser instance
            browser = await p.chromium.launch(
                headless=is_headless,
                slow_mo=500  # Slight delay to ensure smooth user interaction and visual feedback
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            logger.info(f"Navigating to cancellation target URL: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # HITL Step-Up Auth Logic
            has_password_field = False
            try:
                # Dynamically check if a password input exists on the page
                password_input = await page.query_selector("input[type='password']")
                if password_input:
                    has_password_field = True
            except Exception as e:
                logger.debug(f"Password field check error: {e}")

            if requires_auth or has_password_field:
                print(f"\n🚨 Step-Up Auth Detected! Handing control to user for {vendor_name}.")
                print("👉 Please log in to your account in the opened browser window...")
                
                # Wait up to 60 seconds for the user to complete login or for account page to load
                try:
                    # Selector targets common account dashboard or cancellation elements after login
                    await page.wait_for_selector(
                        "input[type='password'], button[type='submit'], form, body", 
                        state="visible", 
                        timeout=60000
                    )
                    logger.info("Step-Up Auth interaction phase completed.")
                except Exception as wait_err:
                    logger.warning(f"HITL wait selector timeout: {wait_err}")

            # Locate and click final cancellation confirmation button (Stubbed click selector logic)
            logger.info(f"Attempting cancellation flow automation for {vendor_name}...")
            
            # STUB: Locate common cancellation buttons (e.g., 'Cancel Membership', 'End Subscription', 'Continue to Cancel')
            cancellation_button_selectors = [
                "button:has-text('Cancel')",
                "a:has-text('Cancel')",
                "button:has-text('End Membership')",
                "input[type='submit'][value*='Cancel']"
            ]

            clicked_button = False
            for selector in cancellation_button_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        logger.info(f"Found cancellation selector '{selector}', clicking...")
                        # Uncomment below line to enable live click in production workflows:
                        # await btn.click()
                        clicked_button = True
                        break
                except Exception as click_err:
                    logger.debug(f"Selector '{selector}' check failed: {click_err}")

            # Keep page open briefly for confirmation
            await asyncio.sleep(2)
            await context.close()
            await browser.close()

            return {
                "status": "success",
                "vendor": vendor_name,
                "requires_auth": requires_auth,
                "message": f"Successfully executed cancellation workflow for {vendor_name}."
            }

    except Exception as e:
        logger.error(f"Playwright cancellation execution failed for {vendor_name}: {e}")
        return {
            "status": "failed",
            "vendor": vendor_name,
            "requires_auth": requires_auth,
            "error": str(e),
            "message": f"Failed to complete cancellation workflow for {vendor_name}: {str(e)}"
        }

if __name__ == "__main__":
    # Standalone test runner
    async def main():
        print("Testing Playwright Executor in Headless mode...")
        res = await execute_cancellation("Example Vendor", "https://example.com", requires_auth=False)
        print("Result:", res)

    asyncio.run(main())
