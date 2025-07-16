import requests
from bs4 import BeautifulSoup
import json


def jpx_two_step_request():
    """
    Двухэтапный запрос как в Insomnia
    1. Первый запрос - открывает страницу поиска
    2. Второй запрос - получает результаты
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
        print(f"Запрос 1 - URL: {response1.url}")

        # Сохраняем первый ответ (страница поиска)
        with open('jpx_step1_search_page.html', 'w', encoding='utf-8') as f:
            f.write(response1.text)
        print("Первый ответ сохранен в jpx_step1_search_page.html")

        # ВТОРОЙ ЗАПРОС - получение результатов
        print("\nЗАПРОС 2: Получение результатов...")

        # Используем тот же URL и те же параметры
        response2 = session.post(url, data=form_data)
        response2.raise_for_status()

        print(f"Запрос 2 - Статус: {response2.status_code}")
        print(f"Запрос 2 - URL: {response2.url}")
        print(f"Запрос 2 - Размер ответа: {len(response2.content)} байт")

        # Сохраняем второй ответ (результаты)
        with open('jpx_step2_results.html', 'w', encoding='utf-8') as f:
            f.write(response2.text)
        print("Второй ответ сохранен в jpx_step2_results.html")

        # Парсим результаты
        soup = BeautifulSoup(response2.content, 'html.parser')

        # Проверяем, есть ли данные
        tables = soup.find_all('table')
        print(f"\nНайдено таблиц: {len(tables)}")

        # Ищем таблицы с данными компаний
        company_data = []
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 1:  # Есть данные кроме заголовка
                print(f"Таблица {i + 1}: {len(rows)} строк")

                # Пытаемся найти таблицу с результатами поиска
                # Обычно это таблица с кодами компаний и названиями
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:  # Минимум код и название
                        row_data = []
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            # Также сохраняем ссылки
                            link = cell.find('a')
                            if link and link.get('href'):
                                row_data.append({
                                    'text': text,
                                    'link': link.get('href')
                                })
                            else:
                                row_data.append(text)

                        if any(str(cell).strip() for cell in row_data if isinstance(cell, str)):  # Есть непустые данные
                            company_data.append({
                                'table': i,
                                'row': j,
                                'data': row_data
                            })

        # Проверяем, получили ли мы результаты
        if company_data:
            print(f"\n✅ Найдено записей с данными: {len(company_data)}")

            # Показываем первые несколько записей
            print("\nПример данных:")
            for i, record in enumerate(company_data[:5]):
                print(f"Запись {i + 1}: {record['data']}")
        else:
            print("\n❌ Данные компаний не найдены")

            # Проверяем, что вообще есть в ответе
            title = soup.find('title')
            if title:
                print(f"Заголовок страницы: {title.get_text()}")

            # Ищем любой текст, который может указывать на результаты
            content_divs = soup.find_all(['div', 'p'], class_=True)
            for div in content_divs[:5]:
                text = div.get_text(strip=True)
                if text and len(text) > 10:
                    print(f"Содержимое: {text[:100]}...")

        # Сохраняем структурированные данные
        result = {
            'success': True,
            'method': 'two_step_request',
            'step1_url': response1.url,
            'step2_url': response2.url,
            'step1_status': response1.status_code,
            'step2_status': response2.status_code,
            'tables_count': len(tables),
            'company_records': len(company_data),
            'data': company_data
        }

        with open('jpx_final_data.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("\nФинальные данные сохранены в jpx_final_data.json")

        return result

    except requests.exceptions.RequestException as e:
        error_result = {
            'success': False,
            'error': f"HTTP ошибка: {str(e)}"
        }
        print(f"Ошибка запроса: {e}")
        return error_result
    except Exception as e:
        error_result = {
            'success': False,
            'error': f"Общая ошибка: {str(e)}"
        }
        print(f"Общая ошибка: {e}")
        return error_result


def jpx_simple_request():
    """
    Простой запрос как в Insomnia (оставляем для сравнения)
    """
    # URL с jsessionid (как в Insomnia)
    url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

    # Точно такие же параметры как в Insomnia
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

    # Заголовки как в браузере
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Referer': 'https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do'
    }

    try:
        print("Отправка простого POST запроса...")
        response = requests.post(url, data=form_data, headers=headers, timeout=30)
        response.raise_for_status()

        print(f"Статус ответа: {response.status_code}")
        print(f"Размер ответа: {len(response.content)} байт")

        # Сохраняем raw HTML
        with open('jpx_simple_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("HTML сохранен в jpx_simple_response.html")

        return {'success': True, 'method': 'simple'}

    except Exception as e:
        print(f"Ошибка простого запроса: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    print("=" * 60)
    print("ДВУХЭТАПНЫЙ ЗАПРОС (как в Insomnia)")
    print("=" * 60)
    result = jpx_two_step_request()

    if result.get('success'):
        print(f"\n🎉 УСПЕХ!")
        print(f"📊 Найдено записей: {result.get('company_records', 0)}")
        print(f"📋 Таблиц: {result.get('tables_count', 0)}")
    else:
        print(f"\n❌ ОШИБКА: {result.get('error')}")

    print("\n" + "=" * 60)
    print("ПРОСТОЙ ЗАПРОС (для сравнения)")
    print("=" * 60)
    result2 = jpx_simple_request()

    print(f"\nРезультат простого запроса: {result2.get('success')}")