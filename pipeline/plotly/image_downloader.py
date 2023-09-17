import aiohttp
import aiofiles
import asyncio

CONCURRENT_REQUESTS_PER_HOST = 5  # Adjust as needed
CONNECTION_POOL_LIMIT = 100  # Adjust as needed

semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS_PER_HOST)

async def download_image(session, url, filename):
    async with semaphore:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(filename, mode='wb') as f:
                    await f.write(await response.read())
            else:
                print(f"Failed to download {url}. Status code: {response.status}")

async def main(urls):
    conn = aiohttp.TCPConnector(limit_per_host=CONNECTION_POOL_LIMIT)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = []
        for index, url in enumerate(urls):
            filename = f"image_{index}.jpg"  # You can modify this to match the file type
            tasks.append(download_image(session, url, filename))
        await asyncio.gather(*tasks)

# List of image URLs to download
image_urls = [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg",
    # Add more URLs as needed
]

asyncio.run(main(image_urls))
