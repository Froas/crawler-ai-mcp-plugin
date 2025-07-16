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

        # Заголовки из успешного запроса
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
        """Инициализирует сессию и получает JSESSIONID"""
        try:
            print("🔑 Инициализация сессии...")

            # Получаем форму поиска
            response = self.session.get(self.form_url)
            response.raise_for_status()

            print(f"✅ Статус: {response.status_code}")
            print(f"✅ Размер: {len(response.text)} символов")

            # Извлекаем JSESSIONID из cookies
            jsessionid_cookie = None
            for cookie in self.session.cookies:
                if cookie.name == 'JSESSIONID':
                    jsessionid_cookie = cookie.value
                    break

            if jsessionid_cookie:
                self.jsessionid = jsessionid_cookie
                print(f"✅ JSESSIONID получен: {self.jsessionid[:20]}...")
            else:
                print("⚠️ JSESSIONID не найден в cookies")

            # Также проверяем URL redirect с jsessionid
            if ';jsessionid=' in response.url:
                url_jsessionid = response.url.split(';jsessionid=')[1].split('?')[0]
                if url_jsessionid:
                    self.jsessionid = url_jsessionid
                    print(f"✅ JSESSIONID из URL: {self.jsessionid[:20]}...")

            # Сохраняем HTML для анализа
            with open('session_form.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("📄 Форма сохранена в session_form.html")

            return True

        except Exception as e:
            print(f"❌ Ошибка инициализации сессии: {e}")
            return False

    def build_session_form_data(self,
                                company_count: int = 50,
                                market_segments: List[str] = None) -> List[tuple]:
        """Строит минимальные данные формы"""

        if market_segments is None:
            market_segments = ['prime', 'standard']

        # Минимальные параметры
        form_data = [
            ('ListShow', 'ListShow'),
            ('sniMtGmnId', ''),
            ('dspSsuPd', str(company_count)),
            ('dspSsuPdMapOut', '10>10<50>50<100>100<200>200<'),
            ('mgrMiTxtBx', ''),
            ('eqMgrCd', ''),
            ('hnsShzitPd', '+'),  # Все локации
            ('hnsShzitPdMapOut',
             '+><01>Hokkaido<02>Aomori<03>Iwate<04>Miyagi<05>Akita<06>Yamagata<07>Fukushima<08>Ibaraki<09>Tochigi<10>Gunma<11>Saitama<12>Chiba<13>Tokyo<14>Kanagawa<15>Niigata<16>Toyama<17>Ishikawa<18>Fukui<19>Yamanashi<20>Nagano<21>Gifu<22>Shizuoka<23>Aichi<24>Mie<25>Shiga<26>Kyoto<27>Osaka<28>Hyogo<29>Nara<30>Wakayama<31>Tottori<32>Shimane<33>Okayama<34>Hiroshima<35>Yamaguchi<36>Tokushima<37>Kagawa<38>Ehime<39>Kochi<40>Fukuoka<41>Saga<42>Nagasaki<43>Kumamoto<44>Oita<45>Miyazaki<46>Kagoshima<47>Okinawa<')
        ]

        # Market segments
        for segment in market_segments:
            if segment in self.market_segments:
                form_data.append(('szkbuChkbx', self.market_segments[segment]))

        form_data.append(('szkbuChkbxMapOut',
                          '011>Prime<012>Standard<013>Growth<008>TOKYO PRO Market<bj1>－<be1>－<111>Prime Foreign Stocks<112>Standard Foreign Stocks<113>Growth Foreign Stocks<bj2>－<be2>－<ETF>ETFs<ETN>ETNs<RET>Real Estate Investment Trusts (REITs)<IFD>Infrastructure Funds<999>Others<'))

        # Остальные обязательные поля
        form_data.extend([
            ('gyshKbnPd', '+'),  # Все индустрии
            ('gyshKbnPdMapOut',
             '+><0050>Fishery, Agriculture &amp; Forestry<1050>Mining<2050>Construction<3050>Foods<3100>Textiles &amp; Apparels<3150>Pulp &amp; Paper<3200>Chemicals<3250>Pharmaceutical<3300>Oil &amp; Coal Products<3350>Rubber Products<3400>Glass &amp; Ceramics Products<3450>Iron &amp; Steel<3500>Nonferrous Metals<3550>Metal Products<3600>Machinery<3650>Electric Appliances<3700>Transportation Equipment<3750>Precision Instruments<3800>Other Products<4050>Electric Power &amp; Gas<5050>Land Transportation<5100>Marine Transportation<5150>Air Transportation<5200>Warehousing &amp; Harbor Transportation Services<5250>Information &amp; Communication<6050>Wholesale Trade<6100>Retail Trade<7050>Banks<7100>Securities &amp; Commodity Futures<7150>Insurance<7200>Other Financing Business<8050>Real Estate<9050>Services<9999>Nonclassifiable<'),
        ])

        return form_data

    def scrape_with_session(self, **kwargs) -> str:
        """Выполняет поиск с правильной сессией"""

        # Инициализируем сессию
        if not self.initialize_session():
            return ""

        form_data = self.build_session_form_data(**kwargs)

        # Используем URL с jsessionid если он есть
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
        print(f"\n🚀 [SESSION SEARCH] POST данные ({len(post_data_string)} символов)")
        print(f"🚀 Target URL: {target_url}")
        print(f"🚀 JSESSIONID: {self.jsessionid[:20] if self.jsessionid else 'НЕТ'}...")
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

            print(f"✅ Статус: {response.status_code}")
            print(f"✅ Размер: {len(response.text)} символов")
            print(f"✅ Final URL: {response.url}")

            if "件中" in response.text:
                print("🎉 НАЙДЕНЫ ДАННЫЕ О КОМПАНИЯХ!")

                match = re.search(r'Display of (\d+)-(\d+) items/(\d+)', response.text)
                if match:
                    start, end, total = match.groups()
                    print(f"📊 Показано: {start}-{end} из {total} компаний")
                else:
                    match = re.search(r'(\d+)件中', response.text)
                    if match:
                        print(f"📊 Найдено: {match.group(1)} компаний")

                with open('session_search_success.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("💾 Результат сохранен в session_search_success.html")

                return response.text
            else:
                print("❌ Данные не найдены")
                with open('session_search_error.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print("💾 Ошибка сохранена в session_search_error.html")

        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")

        return ""


# Crawl4AI версия с сессией
async def crawl_jpx_with_session(
        company_count: int = 50,
        market_segments: List[str] = None,
        max_pages: Optional[int] = None,
        delay: float = 1.0
) -> AsyncGenerator[str, None]:
    """Crawl4AI версия с правильной инициализацией сессии"""

    if market_segments is None:
        market_segments = ['prime', 'standard']

    # Сначала получаем сессию через requests
    scraper = SessionAwareJPXScraper()
    if not scraper.initialize_session():
        print("❌ Не удалось инициализировать сессию")
        return

    form_data = scraper.build_session_form_data(
        company_count=company_count,
        market_segments=market_segments
    )

    async with AsyncWebCrawler(verbose=True) as crawler:
        page = 0

        while True:
            # Добавляем пагинацию
            current_form_data = form_data.copy()
            if page > 0:
                current_form_data.append(('pageOffset', str(page * company_count)))

            post_data_string = urlencode(current_form_data)

            # URL с jsessionid
            target_url = scraper.base_url
            if scraper.jsessionid:
                target_url = f"{scraper.base_url};jsessionid={scraper.jsessionid}"

            print(f"\n🤖 [CRAWL4AI SESSION] Страница {page + 1}")
            print(f"🤖 Target URL: {target_url}")
            print(f"🤖 JSESSIONID: {scraper.jsessionid[:20] if scraper.jsessionid else 'НЕТ'}...")

            try:
                # Инициализация сессии для первой страницы
                if page == 0:
                    print("🤖 Инициализация crawl4ai сессии...")
                    init_url = scraper.form_url
                    if scraper.jsessionid:
                        init_url = f"{scraper.form_url};jsessionid={scraper.jsessionid}"

                    init_result = await crawler.arun(
                        url=init_url,
                        method="GET"
                    )

                    if not init_result.success:
                        print("❌ Ошибка инициализации crawl4ai")
                        break

                    print("✅ Crawl4ai сессия готова")

                # POST запрос
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
                    print(f"❌ Ошибка на странице {page + 1}")
                    break

                html_content = result.html

                if "件中" not in html_content:
                    print(f"❌ Нет данных на странице {page + 1}")
                    with open(f'crawl4ai_session_debug_{page + 1}.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    break

                print(f"✅ Успех! Страница {page + 1}, размер: {len(html_content)} символов")

                # Анализ результатов
                if "件中" in html_content:
                    match = re.search(r'Display of (\d+)-(\d+) items/(\d+)', html_content)
                    if match:
                        start, end, total = match.groups()
                        print(f"📊 Показано: {start}-{end} из {total} компаний")

                with open(f'crawl4ai_session_success_{page + 1}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)

                yield html_content

                if max_pages and page + 1 >= max_pages:
                    break

                page += 1
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Ошибка на странице {page + 1}: {e}")
                break


# Тест с правильной сессией
async def test_session_methods():
    print("🔑 ТЕСТИРОВАНИЕ С ПРАВИЛЬНОЙ СЕССИЕЙ")
    print("=" * 70)

    # Тест 1: Requests с сессией
    print("\n1️⃣ Тестируем Requests с сессией...")
    scraper = SessionAwareJPXScraper()
    html_content = scraper.scrape_with_session(
        company_count=25,
        market_segments=['prime', 'standard']
    )

    requests_success = "件中" in html_content if html_content else False

    # Тест 2: Crawl4AI с сессией
    print("\n2️⃣ Тестируем Crawl4AI с сессией...")
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
    print("🏁 РЕЗУЛЬТАТЫ С СЕССИЕЙ")
    print("=" * 70)
    print(f"📊 Session Requests:  {'✅ РАБОТАЕТ' if requests_success else '❌ НЕ РАБОТАЕТ'}")
    print(f"🤖 Session Crawl4AI:  {'✅ РАБОТАЕТ' if crawl4ai_success else '❌ НЕ РАБОТАЕТ'}")

    if requests_success and crawl4ai_success:
        print("\n🎉 ОБА МЕТОДА С СЕССИЕЙ РАБОТАЮТ!")
        print("🔑 Проблема была в отсутствии JSESSIONID")
    elif requests_success:
        print("\n⚠️ Только Requests с сессией работает")
        print("🔧 Crawl4AI нужно дополнительно отладить")
    else:
        print("\n❌ Оба метода все еще не работают")
        print("🔍 Проверьте файлы session_* для анализа")


if __name__ == "__main__":
    asyncio.run(test_session_methods())