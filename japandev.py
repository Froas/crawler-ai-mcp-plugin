import asyncio

from crawlee.crawlers import (
    PlaywrightCrawler,
    PlaywrightCrawlingContext,
    PlaywrightPreNavCrawlingContext,
)

JAPAN_DEV_BASE_URL = 'https://www.japandev.com'
async def main() -> None:
    crawler = PlaywrightCrawler(
        # Limit the crawl to max requests. Remove or increase it for crawling all links.
        max_requests_per_crawl=10,

        headless=False,
        # Browser types supported by Playwright.
        browser_type='chromium',
    )

    # Define the default request handler, which will be called for every request.
    # The handler receives a context parameter, providing various properties and
    # helper methods. Here are a few key ones we use for demonstration:
    # - request: an instance of the Request class containing details such as the URL
    #   being crawled and the HTTP method used.
    # - page: Playwright's Page object, which allows interaction with the web page
    #   (see https://playwright.dev/python/docs/api/class-page for more details).
    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        data = []
        await context.push_data(data)
        print(data)

        # Find a link to the next page and enqueue it if it exists.
        await context.enqueue_links(selector='.morelink')

    # Define a hook that will be called each time before navigating to a new URL.
    # The hook receives a context parameter, providing access to the request and
    # browser page among other things. In this example, we log the URL being
    # navigated to.
    @crawler.pre_navigation_hook
    async def log_navigation_url(context: PlaywrightPreNavCrawlingContext) -> None:
        context.log.info(f'Navigating to {context.request.url} ...')

    # Run the crawler with the initial list of URLs.
    await crawler.run([JAPAN_DEV_BASE_URL])


if __name__ == '__main__':
    print("started Japan dev scratch")
    asyncio.run(main())