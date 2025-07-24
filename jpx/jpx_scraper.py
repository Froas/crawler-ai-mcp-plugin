import requests
import asyncio
from typing import List, Optional, AsyncGenerator, Dict
from crawl4ai import AsyncWebCrawler
from urllib.parse import urlencode, urlparse, parse_qs
import re


class SessionAwareJPXScraper:
    def __init__(self):
        self.base_url = "https://www2.jpx.co.jp/tseHpFront/JJK020020Action.do"
        self.form_url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do"
        self.session = requests.Session()
        self.jsessionid = None

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        self.market_segments = {
            'prime': '011',
            'standard': '012',
            'growth': '013'
        }

    def initialize_session(self) -> bool:
        """Initialize session and get JSESSIONID"""
        try:
            print("🔑 Initialize Session")

            # Get the search form
            response = self.session.get(self.form_url)
            response.raise_for_status()

            print(f"✅ Status: {response.status_code}")
            print(f"✅ Size: {len(response.text)} characters")

            # Extract JSESSIONID from cookies
            jsessionid_cookie = None
            for cookie in self.session.cookies:
                if cookie.name == 'JSESSIONID':
                    jsessionid_cookie = cookie.value
                    break

            if jsessionid_cookie:
                self.jsessionid = jsessionid_cookie
                print(f"✅ JSESSIONID obtained: {self.jsessionid[:20]}...")
            else:
                print("⚠️ JSESSIONID not found in cookies")

            # Also check URL redirect with jsessionid
            if ';jsessionid=' in response.url:
                url_jsessionid = response.url.split(';jsessionid=')[1].split('?')[0]
                if url_jsessionid:
                    self.jsessionid = url_jsessionid
                    print(f"✅ JSESSIONID from URL: {self.jsessionid[:20]}...")

            # Save HTML for analysis
            with open('session_form.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("📄 Form saved to session_form.html")

            return True

        except Exception as e:
            print(f"❌ Session initialization error: {e}")
            return False

    def build_session_form_data(self,
                                company_count: int = 50,
                                market_segments: List[str] = None) -> List[tuple]:
        """Build minimal form data"""

        if market_segments is None:
            market_segments = ['prime', 'standard']

        # Minimal parameters
        form_data = [
            ('ListShow', 'ListShow'),
            ('sniMtGmnId', ''),
            ('dspSsuPd', str(company_count)),
            ('dspSsuPdMapOut', '10>10<50>50<100>100<200>200<'),
            ('mgrMiTxtBx', ''),
            ('eqMgrCd', ''),
            ('hnsShzitPd', '+'),  # All locations
            ('hnsShzitPdMapOut',
             '+><01>Hokkaido<02>Aomori<03>Iwate<04>Miyagi<05>Akita<06>Yamagata<07>Fukushima<08>Ibaraki<09>Tochigi<10>Gunma<11>Saitama<12>Chiba<13>Tokyo<14>Kanagawa<15>Niigata<16>Toyama<17>Ishikawa<18>Fukui<19>Yamanashi<20>Nagano<21>Gifu<22>Shizuoka<23>Aichi<24>Mie<25>Shiga<26>Kyoto<27>Osaka<28>Hyogo<29>Nara<30>Wakayama<31>Tottori<32>Shimane<33>Okayama<34>Hiroshima<35>Yamaguchi<36>Tokushima<37>Kagawa<38>Ehime<39>Kochi<40>Fukuoka<41>Saga<42>Nagasaki<43>Kumamoto<44>Oita<45>Miyazaki<46>Kagoshima<47>Okinawa<')
        ]

        # Market segments
        for segment in market_segments:
            if segment in self.market_segments:
                form_data.append(('szkbuChkbx', self.market_segments[segment]))

        form_data.append(('szkbuChkbxMapOut',
                          '011>Prime<012>Standard<013>Growth<008>TOKYO PRO Market<bj1>－<be1>－<111>Prime Foreign Stocks<112>Standard Foreign Stocks<113>Growth Foreign Stocks<bj2>－<be2>－<ETF>ETFs<ETN>ETNs<RET>Real Estate Investment Trusts (REITs)<IFD>Infrastructure Funds<999>Others<'))

        # Other required fields
        form_data.extend([
            ('gyshKbnPd', '+'),  # All industries
            ('gyshKbnPdMapOut',
             '+><0050>Fishery, Agriculture &amp; Forestry<1050>Mining<2050>Construction<3050>Foods<3100>Textiles &amp; Apparels<3150>Pulp &amp; Paper<3200>Chemicals<3250>Pharmaceutical<3300>Oil &amp; Coal Products<3350>Rubber Products<3400>Glass &amp; Ceramics Products<3450>Iron &amp; Steel<3500>Nonferrous Metals<3550>Metal Products<3600>Machinery<3650>Electric Appliances<3700>Transportation Equipment<3750>Precision Instruments<3800>Other Products<4050>Electric Power &amp; Gas<5050>Land Transportation<5100>Marine Transportation<5150>Air Transportation<5200>Warehousing &amp; Harbor Transportation Services<5250>Information &amp; Communication<6050>Wholesale Trade<6100>Retail Trade<7050>Banks<7100>Securities &amp; Commodity Futures<7150>Insurance<7200>Other Financing Business<8050>Real Estate<9050>Services<9999>Nonclassifiable<'),
        ])

        return form_data

    def scrape_with_session(self, **kwargs) -> str:
        """Execute search with proper session"""

        # Initialize session
        if not self.initialize_session():
            return ""

        form_data = self.build_session_form_data(**kwargs)

        # Use URL with jsessionid if available
        target_url = self.base_url
        if self.jsessionid:
            target_url = f"{self.base_url};jsessionid={self.jsessionid}"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www2.jpx.co.jp',
            'Referer': f"{self.form_url};jsessionid={self.jsessionid}" if self.jsessionid else self.form_url,
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        }

        post_data_string = urlencode(form_data)
        print(f"\n🚀 [SESSION SEARCH] POST data ({len(post_data_string)} characters)")
        print(f"🚀 Target URL: {target_url}")
        print(f"🚀 JSESSIONID: {self.jsessionid[:20] if self.jsessionid else 'NONE'}...")
        print(f"🚀 Referer: {headers['Referer']}")

        szkbu_count = post_data_string.count('szkbuChkbx=')
        print(f"🚀 Market segments: {szkbu_count}")

        try:
            response = self.session.post(
                target_url,
                data=form_data,
                headers=headers
            )
            response.raise_for_status()

            print(f"✅ Status: {response.status_code}")
            print(f"✅ Size: {len(response.text)} characters")
            print(f"✅ Final URL: {response.url}")

            if "件中" in response.text:
                print("🎉 COMPANY DATA FOUND!")

                match = re.search(r'Display of (\d+)-(\d+) items/(\d+)', response.text)
                if match:
                    start, end, total = match.groups()
                    print(f"📊 Showing: {start}-{end} of {total} companies")
                else:
                    match = re.search(r'(\d+)件中', response.text)
                    if match:
                        print(f"📊 Found: {match.group(1)} companies")

                with open('session_search_success.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("💾 Result saved to session_search_success.html")

                return response.text
            else:
                print("❌ Data not found")
                with open('session_search_error.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("💾 Error saved to session_search_error.html")

        except Exception as e:
            print(f"❌ Request error: {e}")

        return ""


# Crawl4AI version with session
async def crawl_jpx_with_session(
        company_count: int = 50,
        market_segments: List[str] = None,
        max_pages: Optional[int] = None,
        delay: float = 1.0
) -> AsyncGenerator[str, None]:
    """Crawl4AI version with proper session initialization"""

    if market_segments is None:
        market_segments = ['prime', 'standard']

    # First get session via requests
    scraper = SessionAwareJPXScraper()
    if not scraper.initialize_session():
        print("❌ Failed to initialize session")
        return

    form_data = scraper.build_session_form_data(
        company_count=company_count,
        market_segments=market_segments
    )

    async with AsyncWebCrawler(verbose=True) as crawler:
        page = 0

        while True:
            # Add pagination
            current_form_data = form_data.copy()
            if page > 0:
                current_form_data.append(('pageOffset', str(page * company_count)))

            post_data_string = urlencode(current_form_data)

            # URL with jsessionid
            target_url = scraper.base_url
            if scraper.jsessionid:
                target_url = f"{scraper.base_url};jsessionid={scraper.jsessionid}"

            print(f"\n🤖 [CRAWL4AI SESSION] Page {page + 1}")
            print(f"🤖 Target URL: {target_url}")
            print(f"🤖 JSESSIONID: {scraper.jsessionid[:20] if scraper.jsessionid else 'NONE'}...")

            try:
                # Initialize session for first page
                if page == 0:
                    print("🤖 Initializing crawl4ai session...")
                    init_url = scraper.form_url
                    if scraper.jsessionid:
                        init_url = f"{scraper.form_url};jsessionid={scraper.jsessionid}"

                    init_result = await crawler.arun(
                        url=init_url,
                        method="GET"
                    )

                    if not init_result.success:
                        print("❌ Failed to initialize crawl4ai")
                        break

                    print("✅ Crawl4ai session ready")

                # POST request
                result = await crawler.arun(
                    url=target_url,
                    method="POST",
                    data=post_data_string,
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': 'https://www2.jpx.co.jp',
                        'Referer': f"{scraper.form_url};jsessionid={scraper.jsessionid}" if scraper.jsessionid else scraper.form_url,
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
                    with open(f'crawl4ai_session_debug_{page + 1}.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    break

                print(f"✅ Success! Page {page + 1}, size: {len(html_content)} characters")

                # Analyze results
                if "件中" in html_content:
                    match = re.search(r'Display of (\d+)-(\d+) items/(\d+)', html_content)
                    if match:
                        start, end, total = match.groups()
                        print(f"📊 Showing: {start}-{end} of {total} companies")

                with open(f'crawl4ai_session_success_{page + 1}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)

                yield html_content

                if max_pages and page + 1 >= max_pages:
                    break

                page += 1
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Error on page {page + 1}: {e}")
                break


# Test with proper session
async def test_session_methods():
    print("🔑 TESTING WITH PROPER SESSION")
    print("=" * 70)

    # Test 1: Requests with session
    print("\n1️⃣ Testing Requests with session...")
    scraper = SessionAwareJPXScraper()
    html_content = scraper.scrape_with_session(
        company_count=25,
        market_segments=['prime', 'standard']
    )

    requests_success = "件中" in html_content if html_content else False

    # Test 2: Crawl4AI with session
    print("\n2️⃣ Testing Crawl4AI with session...")
    crawl4ai_success = False

    async for html_page in crawl_jpx_with_session(
            company_count=25,
            market_segments=['prime', 'standard'],
            max_pages=1
    ):
        if "件中" in html_page:
            crawl4ai_success = True
        break

    print("\n" + "=" * 70)
    print("🏁 SESSION RESULTS")
    print("=" * 70)
    print(f"📊 Session Requests:  {'✅ WORKS' if requests_success else '❌ NOT WORKING'}")
    print(f"🤖 Session Crawl4AI:  {'✅ WORKS' if crawl4ai_success else '❌ NOT WORKING'}")

    if requests_success and crawl4ai_success:
        print("\n🎉 BOTH SESSION METHODS WORK!")
        print("🔑 The problem was missing JSESSIONID")
    elif requests_success:
        print("\n⚠️ Only Requests with session works")
        print("🔧 Crawl4AI needs additional debugging")
    else:
        print("\n❌ Both methods still not working")
        print("🔍 Check session_* files for analysis")


if __name__ == "__main__":
    asyncio.run(test_session_methods())