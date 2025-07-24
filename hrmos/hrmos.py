import asyncio
import time
from datetime import timedelta
from crawlee.crawlers import (
    PlaywrightCrawler,
    PlaywrightCrawlingContext,
    PlaywrightPreNavCrawlingContext,
)


async def scrap(context, data):
    try:

        await context.page.wait_for_selector('.MjjYud', timeout=8000)
        all_pages = await context.page.query_selector_all('.MjjYud')

        context.log.info(f'Found {len(all_pages)} results on current page')

        if len(all_pages) > 0:
            for page in all_pages:
                try:
                    header_el = await page.query_selector('h3')
                    link_el = await page.query_selector('a')

                    if header_el and link_el:
                        header = await header_el.text_content()
                        link = await link_el.get_attribute('href')

                        if header and link:
                            print(f"Found: {header[:50]}... -> {link}")
                            data.append({
                                "header": header.strip(),
                                "link": link
                            })
                except Exception as e:
                    context.log.warning(f'Error extracting data from result: {e}')
                    continue

    except Exception as e:
        context.log.error(f'Error in scrap function: {e}')

    return data


async def main() -> None:
    URL = 'https://www.google.com/search?q=site%3Ahrmos.co%2Fpages&oq=site%3Ahrmos.co%2Fpages&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTIGCAEQRRg60gEHNzU1ajBqN6gCALACAA&sourceid=chrome&ie=UTF-8'

    crawler = PlaywrightCrawler(
        max_requests_per_crawl=1,
        headless=False,
        browser_type='chromium',
        request_handler_timeout=timedelta(minutes=5),
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url} ...')


        context.page.set_default_timeout(30000)
        context.page.set_default_navigation_timeout(60000)


        data = []
        page_count = 0
        max_pages = 100

        while page_count < max_pages:
            try:
                page_count += 1
                context.log.info(f'Processing page {page_count}')


                await scrap(context, data)


                next_button = await context.page.query_selector('.LLNLxf')

                if next_button is None:
                    context.log.info("No next button found - reached end")
                    break


                is_disabled = await next_button.get_attribute('aria-disabled')
                if is_disabled == 'true':
                    context.log.info("Next button is disabled - reached end")
                    break

                context.log.info(f'Clicking next button for page {page_count + 1}')


                await next_button.click()


                retry_count = 0
                max_retries = 3

                while retry_count < max_retries:
                    try:

                        await context.page.wait_for_load_state('networkidle', timeout=10000)
                        await context.page.wait_for_selector('.MjjYud', timeout=10000)
                        break
                    except Exception as wait_error:
                        retry_count += 1
                        context.log.warning(f'Retry {retry_count}/{max_retries} - Wait error: {wait_error}')
                        if retry_count < max_retries:
                            await asyncio.sleep(2)
                        else:
                            raise wait_error


                await asyncio.sleep(2)


                if page_count % 5 == 0:
                    context.log.info(f'Saving {len(data)} items (page {page_count})')
                    await context.push_data(data.copy())

            except Exception as e:
                context.log.error(f'⚠️ Error on page {page_count}: {e}')


                try:

                    current_url = context.page.url
                    context.log.info(f'Current URL: {current_url}')


                    if 'google.com/search' in current_url:
                        await asyncio.sleep(3)
                        continue
                    else:
                        context.log.error('Lost Google search page, stopping')
                        break

                except Exception as recovery_error:
                    context.log.error(f'Recovery failed: {recovery_error}')
                    break


        if data:
            context.log.info(f'Final save: {len(data)} total items from {page_count} pages')
            await context.push_data(data)


            print(f"\n=== SCRAPING COMPLETED ===")
            print(f"Total pages processed: {page_count}")
            print(f"Total items collected: {len(data)}")
            print(f"=========================\n")


    await crawler.run([URL])


if __name__ == '__main__':
    asyncio.run(main())