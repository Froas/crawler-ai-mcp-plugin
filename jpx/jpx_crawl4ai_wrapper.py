import asyncio
from typing import List, Optional, AsyncGenerator
from crawl4ai import AsyncWebCrawler
from urllib.parse import urlencode
from jpx_scraper import SessionAwareJPXScraper


async def crawl_jpx_complete_detailed(
        company_count: int = 100,
        market_segments: List[str] = None,
        industries: List[str] = None,
        locations: List[str] = None,
        max_pages: Optional[int] = None,
        delay: float = 1.0
) -> AsyncGenerator[str, None]:
    """Полная crawl4ai версия detailed search"""

    if market_segments is None:
        market_segments = ['prime', 'standard']

    # Используем requests scraper для получения form data
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
            # Добавляем пагинацию
            current_form_data = form_data.copy()
            if page > 0:
                current_form_data.append(('pageOffset', str(page * company_count)))

            post_data_string = urlencode(current_form_data)
            print(f"\n🤖 [CRAWL4AI DETAILED] Страница {page + 1}")
            print(f"🤖 POST данные ({len(post_data_string)} символов)")

            try:
                # Инициализация сессии для первой страницы
                if page == 0:
                    print("🤖 Инициализация сессии...")
                    init_result = await crawler.arun(
                        url="https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do",
                        method="GET"
                    )

                    if not init_result.success:
                        print("❌ Ошибка инициализации")
                        break

                    print("✅ Сессия готова")

                # POST запрос
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
                    print(f"❌ Ошибка на странице {page + 1}")
                    break

                html_content = result.html

                if "件中" not in html_content:
                    print(f"❌ Нет данных на странице {page + 1}")
                    # Сохраняем для отладки
                    with open(f'crawl4ai_debug_detailed_{page + 1}.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    break

                print(f"✅ Успех! Страница {page + 1}, размер: {len(html_content)} символов")

                # Анализ результатов
                if "件中" in html_content:
                    match = re.search(r'Display of (\d+)-(\d+) items/(\d+)', html_content)
                    if match:
                        start, end, total = match.groups()
                        print(f"📊 Показано: {start}-{end} из {total} компаний")
                    else:
                        match = re.search(r'(\d+)件中', html_content)
                        if match:
                            print(f"📊 Найдено: {match.group(1)} компаний")

                # Сохраняем результат
                with open(f'crawl4ai_detailed_success_{page + 1}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"💾 Результат сохранен в crawl4ai_detailed_success_{page + 1}.html")

                yield html_content

                if max_pages and page + 1 >= max_pages:
                    print(f"✅ Достигнут лимит: {max_pages} страниц")
                    break

                page += 1
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"❌ Ошибка на странице {page + 1}: {e}")
                break


# Полный тест обоих методов
async def test_complete_methods():
    print("🚀 ПОЛНОЕ ТЕСТИРОВАНИЕ DETAILED SEARCH")
    print("=" * 80)

    # Тест 1: Requests
    print("\n1️⃣ Тестируем Complete Requests Detailed Search...")
    scraper = SessionAwareJPXScraper()
    html_content = scraper.scrape_detailed(
        company_count=25,
        market_segments=['prime'],
        industries=['information_communication']
    )

    requests_success = "件中" in html_content if html_content else False

    # Тест 2: Crawl4AI
    print("\n2️⃣ Тестируем Complete Crawl4AI Detailed Search...")
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
    print("🏁 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ПОЛНОГО DETAILED SEARCH")
    print("=" * 80)
    print(f"📊 Complete Requests:  {'✅ РАБОТАЕТ' if requests_success else '❌ НЕ РАБОТАЕТ'}")
    print(f"🤖 Complete Crawl4AI:  {'✅ РАБОТАЕТ' if crawl4ai_success else '❌ НЕ РАБОТАЕТ'}")

    if requests_success and crawl4ai_success:
        print("\n🎉 ОБА МЕТОДА ПОЛНОГО DETAILED SEARCH РАБОТАЮТ!")
        print("🎯 Теперь можно получать детальные данные о компаниях JPX")
        print("💡 Поддерживаются фильтры по:")
        print("   - Market segments (Prime, Standard, Growth, etc.)")
        print("   - Industries (IT/Communication, Banking, etc.)")
        print("   - Locations (Tokyo, Osaka, etc.)")
        print("   - Trading units, Fiscal year-end, и многое другое")
    elif requests_success:
        print("\n⚠️ Только Complete Requests работает")
        print("🔧 Используйте requests версию или отладьте crawl4ai")
    else:
        print("\n❌ Ни один метод не работает")
        print("🔍 Проверьте параметры POST запроса")
        print("💡 Сравните с успешным запросом в Insomnia")


# Демонстрация различных фильтров
async def demo_filters():
    print("🎨 ДЕМОНСТРАЦИЯ РАЗЛИЧНЫХ ФИЛЬТРОВ")
    print("=" * 60)

    scraper = SessionAwareJPXScraper()

    # Демо 1: IT компании в Tokyo
    print("\n🏢 IT компании в Tokyo...")
    async for page in crawl_jpx_complete_detailed(
            company_count=20,
            market_segments=['prime'],
            industries=['information_communication'],
            locations=['tokyo'],
            max_pages=1
    ):
        print("✅ Получены IT компании Tokyo")
        break

    # Демо 2: Банки во всех локациях
    print("\n🏦 Банки во всех локациях...")
    async for page in crawl_jpx_complete_detailed(
            company_count=20,
            market_segments=['prime', 'standard'],
            industries=['banks'],
            max_pages=1
    ):
        print("✅ Получены банки")
        break

    # Демо 3: Все Prime компании
    print("\n⭐ Все Prime компании...")
    async for page in crawl_jpx_complete_detailed(
            company_count=50,
            market_segments=['prime'],
            max_pages=1
    ):
        print("✅ Получены Prime компании")
        break

    print("\n🎯 Демонстрация завершена!")


if __name__ == "__main__":
    # Основной тест
    asyncio.run(test_complete_methods())

    # Демонстрация фильтров (раскомментируйте при необходимости)
    # asyncio.run(demo_filters())