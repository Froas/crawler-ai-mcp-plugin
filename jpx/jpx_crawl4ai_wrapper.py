import asyncio
from typing import List, Optional, AsyncGenerator
from crawl4ai import AsyncWebCrawler
from urllib.parse import urlencode
from jpx_scraper import SessionAwareJPXScraper
import re


async def crawl_jpx_complete_detailed(
        company_count: int = 100,
        market_segments: List[str] = None,
        industries: List[str] = None,
        locations: List[str] = None,
        max_pages: Optional[int] = None,
        delay: float = 1.0
) -> AsyncGenerator[str, None]:
    """Complete crawl4ai version of detailed search"""

    if market_segments is None:
        market_segments = ['prime', 'standard']

    # Use requests scraper to get form data
    scraper = SessionAwareJPXScraper()
    form_data = scraper.build_detailed_form_data(
        company_count=company_count,
        market_segments=market_segments,
        industries=industries,
        locations=locations
    )

    async with AsyncWebCrawler(verbose=True) as crawler:
        page = 0

        while True:
            # Add pagination
            current_form_data = form_data.copy()
            if page > 0:
                current_form_data.append(('pageOffset', str(page * company_count)))

            post_data_string = urlencode(current_form_data)
            print(f"\n🤖 [CRAWL4AI DETAILED] Page {page + 1}")
            print(f"🤖 POST data ({len(post_data_string)} characters)")

            try:
                # Initialize session for first page
                if page == 0:
                    print("🤖 Initializing session...")
                    init_result = await crawler.arun(
                        url="https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do",
                        method="GET"
                    )

                    if not init_result.success:
                        print("❌ Initialization error")
                        break

                    print("✅ Session ready")

                # POST request
                result = await crawler.arun(
                    url="https://www2.jpx.co.jp/tseHpFront/JJK020020Action.do",
                    method="POST",
                    data=post_data_string,
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': 'https://www2.jpx.co.jp',
                        'Referer': 'https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do',
                        'Cache-Control': 'max-age=0',
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )

                if not result.success:
                    print(f"❌ Error on page {page + 1}")
                    break

                html_content = result.html

                if "件中" not in html_content:
                    print(f"❌ No data on page {page + 1}")
                    # Save for debugging
                    with open(f'crawl4ai_debug_detailed_{page + 1}.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    break

                print(f"✅ Success! Page {page + 1}, size: {len(html_content)} characters")

                # Analyze results
                if "件中" in html_content:
                    match = re.search(r'Display of (\d+)-(\d+) items/(\d+)', html_content)
                    if match:
                        start, end, total = match.groups()
                        print(f"📊 Showing: {start}-{end} of {total} companies")
                    else:
                        match = re.search(r'(\d+)件中', html_content)
                        if match:
                            print(f"📊 Found: {match.group(1)} companies")

                # Save result
                with open(f'crawl4ai_detailed_success_{page + 1}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"💾 Result saved to crawl4ai_detailed_success_{page + 1}.html")

                yield html_content

                if max_pages and page + 1 >= max_pages:
                    print(f"✅ Reached limit: {max_pages} pages")
                    break

                page += 1
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Error on page {page + 1}: {e}")
                break


# Complete test of both methods
async def test_complete_methods():
    print("🚀 COMPLETE DETAILED SEARCH TESTING")
    print("=" * 80)

    # Test 1: Requests
    print("\n1️⃣ Testing Complete Requests Detailed Search...")
    scraper = SessionAwareJPXScraper()
    html_content = scraper.scrape_detailed(
        company_count=25,
        market_segments=['prime'],
        industries=['information_communication']
    )

    requests_success = "件中" in html_content if html_content else False

    # Test 2: Crawl4AI
    print("\n2️⃣ Testing Complete Crawl4AI Detailed Search...")
    crawl4ai_success = False
    page_count = 0

    async for html_page in crawl_jpx_complete_detailed(
            company_count=25,
            market_segments=['prime'],
            industries=['information_communication'],
            max_pages=1
    ):
        page_count += 1
        if "件中" in html_page:
            crawl4ai_success = True
        break

    print("\n" + "=" * 80)
    print("🏁 FINAL RESULTS OF COMPLETE DETAILED SEARCH")
    print("=" * 80)
    print(f"📊 Complete Requests:  {'✅ WORKS' if requests_success else '❌ NOT WORKING'}")
    print(f"🤖 Complete Crawl4AI:  {'✅ WORKS' if crawl4ai_success else '❌ NOT WORKING'}")

    if requests_success and crawl4ai_success:
        print("\n🎉 BOTH COMPLETE DETAILED SEARCH METHODS WORK!")
        print("🎯 Now you can get detailed data about JPX companies")
        print("💡 Supported filters include:")
        print("   - Market segments (Prime, Standard, Growth, etc.)")
        print("   - Industries (IT/Communication, Banking, etc.)")
        print("   - Locations (Tokyo, Osaka, etc.)")
        print("   - Trading units, Fiscal year-end, and much more")
    elif requests_success:
        print("\n⚠️ Only Complete Requests works")
        print("🔧 Use requests version or debug crawl4ai")
    else:
        print("\n❌ Neither method works")
        print("🔍 Check POST request parameters")
        print("💡 Compare with successful request in Insomnia")


# Demonstration of various filters
async def demo_filters():
    print("🎨 DEMONSTRATION OF VARIOUS FILTERS")
    print("=" * 60)

    scraper = SessionAwareJPXScraper()

    # Demo 1: IT companies in Tokyo
    print("\n🏢 IT companies in Tokyo...")
    async for page in crawl_jpx_complete_detailed(
            company_count=20,
            market_segments=['prime'],
            industries=['information_communication'],
            locations=['tokyo'],
            max_pages=1
    ):
        print("✅ Retrieved IT companies in Tokyo")
        break

    # Demo 2: Banks in all locations
    print("\n🏦 Banks in all locations...")
    async for page in crawl_jpx_complete_detailed(
            company_count=20,
            market_segments=['prime', 'standard'],
            industries=['banks'],
            max_pages=1
    ):
        print("✅ Retrieved banks")
        break

    # Demo 3: All Prime companies
    print("\n⭐ All Prime companies...")
    async for page in crawl_jpx_complete_detailed(
            company_count=50,
            market_segments=['prime'],
            max_pages=1
    ):
        print("✅ Retrieved Prime companies")
        break

    print("\n🎯 Demonstration completed!")


if __name__ == "__main__":
    # Main test
    asyncio.run(test_complete_methods())

    # Filter demonstration (uncomment if needed)
    # asyncio.run(demo_filters())