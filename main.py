import asyncio
from datetime import timedelta

from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext, BasicCrawler


async def main() -> None:
    crawler = BeautifulSoupCrawler(
        # Limit the crawl to max requests. Remove or increase it for crawling all links.
        max_request_retries=1,

        request_handler_timeout=timedelta(seconds=30),
        max_requests_per_crawl=10,
    )

    # Define the default request handler, which will be called for every request.
    @crawler.router.default_handler
    async def request_handler(context: BeautifulSoupCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url} ...')
        context.request.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
        context.request.headers["Accept-Language"] = "en-US,en;q=0.9"
        
        # Extract data from the page.
        ul = context.soup.find('ul', class_='relative list-inside')
        lis =[ li.get_text(strip=True)
               for li in ul.find_all('li', recursive=False)] if ul else []
        data = {
            'url': context.request.url,
            'title': context.soup.title.string if context.soup.title else None,
            'lis': lis
        }

        # Push the extracted data to the default dataset.
        await context.push_data(data)

        # Enqueue all links found on the page.
        await context.enqueue_links()

    # Run the crawler with the initial list of URLs.
    await crawler.run(['https://www.tokyodev.com/jobs/backend'])

if __name__ == '__main__':
    asyncio.run(main())