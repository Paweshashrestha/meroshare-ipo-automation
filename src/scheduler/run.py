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
    finally:
        schedule.clear()


def main():
    """Main scheduler function."""
    logger.info("IPO Scheduler started (laptop, today 10:00 Nepal time only)")
    schedule.every().day.at("10:00").do(run_ipo_check)

    logger.info("Next run: 10:00 Nepal time (run once, then exit)")
    for job in schedule.jobs:
        logger.info(f"  - {job.next_run}")

    while True:
        schedule.run_pending()
        if schedule.jobs:
            time.sleep(60)
        else:
            logger.info("Job completed. Exiting.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)

