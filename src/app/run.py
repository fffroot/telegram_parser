import asyncio
from src.main import main
import logging


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler(),
                        logging.FileHandler('./bot.log')
                    ])

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        logger.info("Starting bot in polling mode...")
        asyncio.run(main())
    except Exception as e:
        logger.error(e)



