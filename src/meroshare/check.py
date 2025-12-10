import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import Config
from src.meroshare.browser import BrowserManager
from src.meroshare.login import MeroShareLogin

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    try:
        config = Config()
        with BrowserManager(headless=False) as browser:
            login = MeroShareLogin(browser, config)
            logger.info("Logging into MeroShare...")
            if not login.login():
                logger.error("Failed to login to MeroShare")
                return False
            logger.info("Logged in to MeroShare")

            # Navigate to ASBA
            asba_link = browser.page.wait_for_selector('a[href="#/asba"]', timeout=5000)
            if asba_link:
                asba_link.click()
                browser.page.wait_for_load_state("networkidle")
                logger.info("ASBA link clicked")
            else:
                logger.warning("ASBA link not found")
                return False
            browser.page.wait_for_timeout(1000)
            
            
            # Check if there is an IPO
            no_records = browser.page.query_selector(
                "app-no-records-found .fallback-title-message"
            )
            if no_records:
                text=no_records.inner_text().strip()
                if "No Record" in text:
                    logger.info("No IPO available currently")
                else:
                    logger.info("IPO(s) available currently")
                return True
            else:
                logger.info("IPO(s) available! Check the 'Apply for Issue' section")
               

    except Exception as e:
        logger.error(f"Failed to check MeroShare: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
