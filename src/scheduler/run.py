import sys
import time
import schedule
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.meroshare.check import main as check_ipos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def run_ipo_check():
    """Run IPO check and handle errors."""
    try:
        logger.info("=" * 60)
        logger.info("Starting scheduled IPO check...")
        logger.info("=" * 60)
        check_ipos()
        logger.info("IPO check completed")
    except Exception as e:
        logger.error(f"Error in scheduled IPO check: {e}", exc_info=True)


def main():
    """Main scheduler function."""
    logger.info("IPO Scheduler started")
    logger.info("Scheduling IPO checks...")
    
    # Schedule IPO checks - adjust times as needed
    # Check every day at 9:00 AM and 2:00 PM (Nepal time)
    schedule.every().day.at("09:00").do(run_ipo_check)
    schedule.every().day.at("14:00").do(run_ipo_check)
    
    # You can also schedule for specific days:
    # schedule.every().monday.at("09:00").do(run_ipo_check)
    # schedule.every().tuesday.at("09:00").do(run_ipo_check)
    # etc.
    
    # Or check every X hours:
    # schedule.every(6).hours.do(run_ipo_check)
    
    logger.info("Scheduler configured. Waiting for scheduled times...")
    logger.info("Next run times:")
    for job in schedule.jobs:
        logger.info(f"  - {job.next_run}")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)

