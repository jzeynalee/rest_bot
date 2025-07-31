
import asyncio
from core.initialization import load_configuration
from modules.rest_client import RestPollingClient

async def run_bot() -> None:
    config = load_configuration()
    polling_client = RestPollingClient(config)
    await polling_client.run()

def main():
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"❌ Bot terminated due to error: {e}")

if __name__ == "__main__":
    main()
