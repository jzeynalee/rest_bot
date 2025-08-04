
import asyncio
from core.initialization import load_configuration
from modules.rest_client import RestPollingClient
from utils.logger import setup_logger

async def run_bot() -> None:
    """
    Entrypoint coroutine for the REST polling bot.

    Loads the configuration, configures a dedicated logger and kicks off the
    polling loop.  A logger is explicitly created here to ensure that both
    console and file handlers are attached before any asynchronous work
    begins.  The RestPollingClient will inherit this logger and therefore
    write progress information to the terminal and the `logs/bot.log` file.
    """
    # Load environment configuration (.env)
    config = load_configuration()

    # Create a named logger for the bot.  This uses defaults from
    # `utils.logger` (rotating file + console output) and avoids
    # duplicate handlers if called repeatedly.  The logger name helps to
    # separate logs from different subsystems.
    logger = setup_logger("RestBot", to_console=True)

    # Instantiate the polling client with the explicit logger.  If
    # additional components are passed in they will inherit this logger too.
    polling_client = RestPollingClient(config, logger=logger)

    # Run until cancelled or an unhandled exception occurs.
    await polling_client.run()

def main():
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"❌ Bot terminated due to error: {e}")

if __name__ == "__main__":
    main()
