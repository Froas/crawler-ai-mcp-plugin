import asyncio

from crawlee.crawlers import (
    PlaywrightCrawler,
    PlaywrightCrawlingContext,
    PlaywrightPreNavCrawlingContext,
)

TOKYO_DEV_BASE_URL = 'https://www.tokyodev.com'
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
        context.log.info(f'Processing {context.request.url} ...')

        # Extract data from the page using Playwright's API.
        ul = await context.page.query_selector('ul.relative.list-inside')
        lis = await ul.query_selector_all('li')
        data = []

        for li in lis:
            # Get the HTML elements for the title and rank within each post.
            title_el = await li.query_selector('h3 > a')
            title = await title_el.inner_text()
            job_items = await li.query_selector_all('div[data-collapsable-list-target="item"]')
            jobs = []
            for job in job_items:
                job_title_el = await job.query_selector('h4 > a')
                job_title = await job_title_el.inner_text()
                job_link = await job_title_el.get_attribute('href')
                job_tags = []
                job_tags_elem = await job.query_selector_all('div > a')
                for tag in job_tags_elem:
                    tag = await tag.inner_text()
                    job_tags.append(tag)

                job = {
                    'title': job_title,
                    'tags': job_tags,
                    'link': TOKYO_DEV_BASE_URL + job_link
                }
                jobs.append(job)
            data.append({'title': title, 'jobs': jobs})

        # Push the extracted data to the default dataset. In local configuration,
        # the data will be stored as JSON files in ./storage/datasets/default.
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
    await crawler.run([TOKYO_DEV_BASE_URL + '/jobs/backend'])


if __name__ == '__main__':
    asyncio.run(main())