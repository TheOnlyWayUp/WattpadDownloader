import asyncio
from datetime import datetime
import aiohttp
from rich import print


PORT: int = 8086
DOWNLOAD_URL = (
    f"http://localhost:{PORT}/download/314175600?om=1&download_images=true&mode=story"
)


async def fetch(task_id: int, session: aiohttp.ClientSession):
    print("started", task_id)

    start = datetime.now()
    async with session.get(DOWNLOAD_URL) as response:
        print(task_id, response.status)
    end = datetime.now()

    print("time taken", (end - start).total_seconds())


async def main():
    session = aiohttp.ClientSession()

    await asyncio.gather(*[fetch(i, session) for i in range(30)])


if __name__ == "__main__":
    asyncio.run(main())
