import requests
from bs4 import BeautifulSoup
import json
import time
import re


def jpx_two_step_request():
    """
    Оригинальная рабочая функция (одна страница)
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })

    # Параметры form-data точно как в Insomnia
    form_data = {
        'dspSsuPd': '500',
        'szkbuChkbxMapOut': '011>Prime<012>Standard<013>Growth<008>TOKYO',
        'ListShow': 'ListShow',
        'sniMtGmnId': '',
        'dspSsuPdMapOut': '10>10<50>50<100>100<200>200<',
        'mgrMiTxtBx': '',
        'eqMgrCd': '',
        'szkbuChkbx': '011'
    }

    try:
        # ПЕРВЫЙ ЗАПРОС - открытие страницы поиска
        print("ЗАПРОС 1: Открытие страницы поиска...")
        url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

        response1 = session.post(url, data=form_data)
        response1.raise_for_status()

        print(f"Запрос 1 - Статус: {response1.status_code}")

        # ВТОРОЙ ЗАПРОС - получение результатов
        print("\nЗАПРОС 2: Получение результатов...")
        response2 = session.post(url, data=form_data)
        response2.raise_for_status()

        print(f"Запрос 2 - Статус: {response2.status_code}")
        print(f"Запрос 2 - Размер ответа: {len(response2.content)} байт")

        # Парсим результаты
        soup = BeautifulSoup(response2.content, 'html.parser')
        enhanced_data = parse_companies_from_soup(soup)

        print(f"\n✅ Найдено компаний: {len(enhanced_data)}")

        # Сохраняем результат
        result = {
            'success': True,
            'method': 'two_step_request',
            'companies_count': len(enhanced_data),
            'companies': enhanced_data
        }

        return result

    except Exception as e:
        print(f"Ошибка: {e}")
        return {'success': False, 'error': str(e)}


def jpx_with_pagination(max_pages=None, delay=1, search_params=None):
    """
    Версия с pagination на основе рабочего кода
    """
    if search_params is None:
        search_params = {
            'dspSsuPd': '500',
            'szkbuChkbxMapOut': '011>Prime<012>Standard<013>Growth<008>TOKYO',
            'ListShow': 'ListShow',
            'sniMtGmnId': '',
            'dspSsuPdMapOut': '10>10<50>50<100>100<200>200<',
            'mgrMiTxtBx': '',
            'eqMgrCd': '',
            'szkbuChkbx': '011'
        }

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })

    all_companies = []
    all_statistics = {'segments': {}, 'industries': {}}
    current_page = 1
    total_items = None
    total_pages = None

    try:
        while True:
            print(f"\n{'=' * 60}")
            print(f"📄 СТРАНИЦА {current_page}")
            if total_pages:
                print(f"📊 Прогресс: {current_page}/{total_pages}")
            if total_items:
                print(f"🎯 Всего компаний: {total_items}")
            print(f"{'=' * 60}")

            # Готовим параметры для текущей страницы
            form_data = search_params.copy()

            # ПЕРВЫЙ ЗАПРОС
            print(f"ЗАПРОС 1: Инициализация страницы {current_page}...")
            url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

            response1 = session.post(url, data=form_data)
            response1.raise_for_status()

            # ВТОРОЙ ЗАПРОС
            print(f"ЗАПРОС 2: Получение данных страницы {current_page}...")

            # Для страниц после первой используем другую логику
            if current_page > 1:
                # Парсим первый ответ для получения формы результатов
                soup_temp = BeautifulSoup(response1.content, 'html.parser')

                # Ищем форму JJK020030Form (форма результатов с пагинацией)
                form_030 = soup_temp.find('form', attrs={'name': 'JJK020030Form'})

                if form_030:
                    print(f"Найдена форма JJK020030Form, используем для страницы {current_page}")

                    # Собираем все скрытые поля из формы
                    pagination_form_data = {}
                    hidden_inputs = form_030.find_all('input', {'type': 'hidden'})

                    for hidden in hidden_inputs:
                        name = hidden.get('name')
                        value = hidden.get('value', '')
                        if name:
                            pagination_form_data[name] = value

                    # Добавляем параметры для пагинации
                    pagination_form_data.update({
                        'Transition': 'Transition',
                        'pageNo': str(current_page),
                        'currentPage': str(current_page)
                    })

                    # Используем URL для результатов
                    url_results = "https://www2.jpx.co.jp/tseHpFront/JJK020030Action.do"
                    response2 = session.post(url_results, data=pagination_form_data)
                else:
                    # Fallback: используем оригинальную форму
                    print(f"Форма JJK020030Form не найдена, используем оригинальную")
                    response2 = session.post(url, data=form_data)
            else:
                # Первая страница: стандартный второй запрос
                response2 = session.post(url, data=form_data)

            response2.raise_for_status()
            print(f"Запрос 2 - Статус: {response2.status_code}, Размер: {len(response2.content)} байт")

            # Сохраняем HTML каждой страницы
            with open(f'jpx_page_{current_page}.html', 'w', encoding='utf-8') as f:
                f.write(response2.text)

            # Парсим компании с текущей страницы
            soup = BeautifulSoup(response2.content, 'html.parser')
            page_companies = parse_companies_from_soup(soup)

            print(f"📊 Найдено компаний на странице {current_page}: {len(page_companies)}")

            # Добавляем номер страницы к каждой компании
            for company in page_companies:
                company['page'] = current_page

            # Добавляем в общий список
            all_companies.extend(page_companies)

            # Обновляем статистику
            update_statistics(page_companies, all_statistics)

            # Получаем информацию о пагинации
            pagination_info = extract_pagination_info(soup)

            if pagination_info:
                total_items = pagination_info.get('total_items')
                total_pages = pagination_info.get('total_pages')
                has_next = pagination_info.get('has_next_page', False)

                print(f"\n📖 Пагинация:")
                print(f"  Текущая страница: {pagination_info.get('current_page')}")
                print(f"  Всего страниц: {total_pages}")
                print(f"  Всего элементов: {total_items}")
                print(f"  Есть следующая: {has_next}")

                # Проверяем условия продолжения
                if not has_next or (total_pages and current_page >= total_pages):
                    print("🏁 Достигнута последняя страница")
                    break

                if max_pages and current_page >= max_pages:
                    print(f"🛑 Достигнут лимит: {max_pages} страниц")
                    break

                if len(page_companies) == 0:
                    print("🛑 Нет компаний на странице")
                    break

                # Переходим к следующей странице
                current_page += 1

                if delay > 0:
                    print(f"⏱️ Задержка {delay} сек...")
                    time.sleep(delay)

            else:
                print("📖 Пагинация не найдена")
                if len(page_companies) == 0:
                    print("🛑 Нет компаний и пагинации")
                    break
                else:
                    print("📄 Возможно, единственная страница")
                    break

        # Финальные результаты
        print(f"\n🎉 ЗАВЕРШЕНО!")
        print(f"📊 Обработано страниц: {current_page}")
        print(f"🏢 Всего компаний: {len(all_companies)}")

        # Показываем статистику
        show_final_statistics(all_statistics)

        # Сохраняем результаты
        result = save_results(all_companies, all_statistics, current_page, total_items)

        return result

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'error': str(e),
            'partial_data': True,
            'companies_collected': len(all_companies),
            'companies': all_companies
        }


def parse_companies_from_soup(soup):
    """
    Парсит компании из soup (точно как в рабочем коде)
    """
    enhanced_data = []

    # Ищем все скрытые поля с данными компаний
    hidden_inputs = soup.find_all('input', {'type': 'hidden'})
    company_records = {}

    for hidden in hidden_inputs:
        name = hidden.get('name', '')
        value = hidden.get('value', '')

        # Парсим поля формата ccJjCrpSelKekkLst_st[N].field
        if 'ccJjCrpSelKekkLst_st[' in name and '].' in name:
            try:
                start = name.find('[') + 1
                end = name.find(']')
                index = int(name[start:end])

                field_start = name.find('.') + 1
                field_name = name[field_start:]

                if index not in company_records:
                    company_records[index] = {}

                company_records[index][field_name] = value
            except (ValueError, IndexError):
                continue

    # Парсим видимые данные из таблицы
    tables = soup.find_all('table')
    company_data = []

    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Пропускаем заголовок
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:  # Минимум код, название, сегмент, индустрия
                code_cell = cells[0]
                code_text = code_cell.get_text(strip=True)

                if code_text.isdigit() and len(code_text) == 5:  # Код компании
                    company_info = {
                        'code': code_text,
                        'name': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                        'market_segment': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                        'industry': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                        'fiscal_year_end': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                        'alerts': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                    }

                    # Ищем ссылки
                    links = {}
                    for i, cell in enumerate(cells):
                        link = cell.find('a')
                        if link and link.get('href'):
                            if 'stock_detail' in link.get('href'):
                                links['stock_prices_url'] = link.get('href')
                            elif 'javascript:' not in link.get('href'):
                                links[f'link_{i}'] = link.get('href')

                    if links:
                        company_info['links'] = links

                    company_data.append(company_info)

    # Объединяем данные из скрытых полей с видимыми данными
    for company in company_data:
        code = company['code']
        enhanced_company = company.copy()

        # Добавляем данные из скрытых полей если найдены
        for record in company_records.values():
            if record.get('eqMgrCd') == code:
                enhanced_company['hidden_fields'] = record
                break

        enhanced_data.append(enhanced_company)

    # Если основной парсинг не дал результатов, используем только скрытые поля
    if not enhanced_data and company_records:
        for index, record in sorted(company_records.items()):
            if 'eqMgrCd' in record:  # Есть код компании
                company_info = {
                    'index': index,
                    'code': record.get('eqMgrCd', ''),
                    'name': record.get('eqMgrNm', ''),
                    'market_segment': record.get('szkbuNm', ''),
                    'industry': record.get('gyshDspNm', ''),
                    'fiscal_year_end': record.get('dspYuKssnKi', ''),
                    'hidden_fields': record
                }
                enhanced_data.append(company_info)

    return enhanced_data


def extract_pagination_info(soup):
    """
    Извлекает информацию о пагинации из JPX
    """
    pagination_info = {
        'current_page': 1,
        'total_pages': 1,
        'total_items': 0,
        'items_per_page': 10,
        'has_next_page': False,
        'has_prev_page': False
    }

    # Ищем div с классом pagingmenu
    paging_menu = soup.find('div', class_='pagingmenu')

    if paging_menu:
        # Извлекаем информацию о количестве элементов "Display of 1-10 items/1622"
        left_div = paging_menu.find('div', class_='left')
        if left_div:
            text = left_div.get_text()
            items_match = re.search(r'(\d+)-(\d+)\s+items?/(\d+)', text)
            if items_match:
                start_item = int(items_match.group(1))
                end_item = int(items_match.group(2))
                total_items = int(items_match.group(3))

                pagination_info['total_items'] = total_items
                pagination_info['items_per_page'] = end_item - start_item + 1
                pagination_info['current_page'] = (start_item - 1) // pagination_info['items_per_page'] + 1
                pagination_info['total_pages'] = (total_items + pagination_info['items_per_page'] - 1) // \
                                                 pagination_info['items_per_page']

        # Ищем текущую страницу по классу "current"
        current_element = paging_menu.find('b', class_='current')
        if current_element:
            try:
                pagination_info['current_page'] = int(current_element.get_text().strip())
            except ValueError:
                pass

        # Проверяем наличие кнопки "Next"
        next_div = paging_menu.find('div', class_='next_e')
        if next_div and next_div.find('a'):
            pagination_info['has_next_page'] = True

        # Если текущая страница больше 1, то есть предыдущая
        if pagination_info['current_page'] > 1:
            pagination_info['has_prev_page'] = True

    return pagination_info


def update_statistics(companies, all_statistics):
    """
    Обновляет общую статистику
    """
    for company in companies:
        segment = company.get('market_segment', 'Unknown')
        industry = company.get('industry', 'Unknown')

        all_statistics['segments'][segment] = all_statistics['segments'].get(segment, 0) + 1
        all_statistics['industries'][industry] = all_statistics['industries'].get(industry, 0) + 1


def show_final_statistics(all_statistics):
    """
    Показывает финальную статистику
    """
    if all_statistics['segments']:
        print(f"\n📈 Статистика по сегментам:")
        for segment, count in sorted(all_statistics['segments'].items()):
            print(f"  {segment}: {count}")

    if all_statistics['industries']:
        print(f"\n🏭 Топ-10 индустрий:")
        top_industries = sorted(all_statistics['industries'].items(), key=lambda x: x[1], reverse=True)[:10]
        for industry, count in top_industries:
            print(f"  {industry}: {count}")


def save_results(all_companies, all_statistics, pages_processed, total_items):
    """
    Сохраняет результаты в файлы
    """
    # Полные данные
    result = {
        'success': True,
        'method': 'jpx_pagination_scraping',
        'pages_processed': pages_processed,
        'total_companies': len(all_companies),
        'expected_total_items': total_items,
        'statistics': {
            'segments': all_statistics['segments'],
            'industries': dict(sorted(all_statistics['industries'].items(), key=lambda x: x[1], reverse=True))
        },
        'companies': all_companies
    }

    with open('jpx_all_companies.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Полные данные: jpx_all_companies.json")

    # Упрощенные данные
    simple_result = {
        'total_companies': len(all_companies),
        'expected_total': total_items,
        'pages_processed': pages_processed,
        'companies': [
            {
                'code': company.get('code'),
                'name': company.get('name'),
                'market_segment': company.get('market_segment'),
                'industry': company.get('industry'),
                'fiscal_year_end': company.get('fiscal_year_end'),
                'page': company.get('page'),
                'stock_prices_url': company.get('links', {}).get('stock_prices_url', '') if company.get('links') else ''
            }
            for company in all_companies
        ]
    }

    with open('jpx_all_companies_simple.json', 'w', encoding='utf-8') as f:
        json.dump(simple_result, f, ensure_ascii=False, indent=2)
    print(f"💾 Упрощенные данные: jpx_all_companies_simple.json")

    return result


if __name__ == "__main__":
    print("🚀 JPX SCRAPER (На основе рабочего кода)")
    print("=" * 60)

    mode = input(
        "\nВыберите режим:\n1. Одна страница (быстро)\n2. Все страницы\n3. Ограниченное количество страниц\nВаш выбор (1-3): ").strip()

    if mode == "1":
        print("\n📄 РЕЖИМ: Одна страница")
        result = jpx_two_step_request()

        if result.get('success'):
            print(f"\n🎉 УСПЕХ! Найдено компаний: {result.get('companies_count', 0)}")
        else:
            print(f"\n❌ ОШИБКА: {result.get('error')}")

    elif mode == "2":
        print("\n📚 РЕЖИМ: Все страницы")
        delay = input("Задержка между запросами в секундах (по умолчанию 1): ").strip()
        delay = float(delay) if delay.replace('.', '').isdigit() else 1.0

        print(f"⚠️ Это может занять много времени!")
        confirm = input("Продолжить? (y/n): ").strip().lower()

        if confirm == 'y':
            result = jpx_with_pagination(max_pages=None, delay=delay)

            if result.get('success'):
                print(f"\n🎉 УСПЕХ! Компаний: {result.get('total_companies', 0)}")
            else:
                print(f"\n⚠️ ЧАСТИЧНЫЙ РЕЗУЛЬТАТ: {result.get('companies_collected', 0)} компаний")

    elif mode == "3":
        print("\n📑 РЕЖИМ: Ограниченное количество")

        max_pages = input("Максимум страниц: ").strip()
        max_pages = int(max_pages) if max_pages.isdigit() else 3

        delay = input("Задержка в секундах (по умолчанию 1): ").strip()
        delay = float(delay) if delay.replace('.', '').isdigit() else 1.0

        result = jpx_with_pagination(max_pages=max_pages, delay=delay)

        if result.get('success'):
            print(f"\n🎉 УСПЕХ! Компаний: {result.get('total_companies', 0)}")
        else:
            print(f"\n⚠️ ЧАСТИЧНЫЙ РЕЗУЛЬТАТ: {result.get('companies_collected', 0)} компаний")

    else:
        print("❌ Неверный выбор")

    print(f"\n✅ Готово!")