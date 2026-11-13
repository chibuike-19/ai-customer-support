import asyncio
import logging

from app.config import settings
from app.gmail import Gmail
from app.pipeline import handle_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("poller")


async def poll_once() -> int:
    gmail = Gmail()
    message_ids = gmail.list_new_message_ids()
    for message_id in message_ids:
        try:
            await handle_message(gmail, message_id)
        except Exception:
            # One bad email must not stop the loop.
            logger.exception("Failed to process %s", message_id)
    return len(message_ids)


async def run() -> None:
    logger.info("Polling every %s seconds", settings.poll_interval_seconds)
    while True:
        try:
            count = await poll_once()
            if count:
                logger.info("Handled %s new messages", count)
        except Exception:
            logger.exception("Poll failed")
        await asyncio.sleep(settings.poll_interval_seconds)


def main() -> None:
    # One event loop for the poller's whole life. The model client is cached across calls,
    # so starting a new loop per email (asyncio.run per message) breaks it.
    asyncio.run(run())


if __name__ == "__main__":
    main()