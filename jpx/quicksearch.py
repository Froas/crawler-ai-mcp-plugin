def main():
    """
    Пример использования
    """
    scraper = JPXScraper()

import requests


from bs4 import BeautifulSoup
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import json


class JPXScraper:
    def __init__(self):
        self.base_url = "https://www2.jpx.co.jp"
        self.search_url = "/tseHpFront/JJK020010Action.do"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def scrape_with_requests(self, search_params=None):
        """
        Скрапинг данных с использованием requests + BeautifulSoup
        """
        if search_params is None:
            search_params = {
                'dspSsuPd': '500',
                'szkbuChkbxMapOut': '011>Prime<012>Standard<013>Growth<008>TOKYO',
                'ListShow': 'ListShow',
                'dspSsuPdMapOut': '10>10<50>50<100>100<200>200<',
                'szkbuChkbx': '011'
            }

        try:
            # Шаг 1: Получение страницы поиска
            print("Шаг 1: Получение страницы поиска...")
            search_response = self.session.get(self.base_url + self.search_url)
            search_response.raise_for_status()

            # Парсим HTML страницы поиска
            soup = BeautifulSoup(search_response.content, 'html.parser')

            # Ищем форму и получаем все скрытые поля
            form = soup.find('form')
            if not form:
                return {"success": False, "error": "Форма не найдена"}

            # Собираем все данные формы
            form_data = {}

            # Добавляем скрытые поля
            for hidden_input in form.find_all('input', {'type': 'hidden'}):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    form_data[name] = value

            # Добавляем параметры поиска
            form_data.update(search_params)

            # Шаг 2: Отправка формы для получения результатов
            print("Шаг 2: Отправка формы...")

            # Устанавливаем Referer
            self.session.headers['Referer'] = self.base_url + self.search_url

            # Отправляем POST-запрос
            results_response = self.session.post(
                self.base_url + self.search_url,
                data=form_data
            )
            results_response.raise_for_status()

            # Парсим результаты
            results_soup = BeautifulSoup(results_response.content, 'html.parser')

            # Извлекаем данные из таблицы
            results = self._parse_table_data(results_soup)

            return {
                "success": True,
                "data": results,
                "timestamp": datetime.now().isoformat(),
                "method": "requests",
                "total_records": len(results)
            }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"HTTP ошибка: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Общая ошибка: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def scrape_with_selenium(self, search_params=None, headless=True, debug=False):
        """
        Скрапинг данных с использованием Selenium
        """
        if search_params is None:
            # Исправленные параметры поиска на основе реальной структуры формы
            search_params = {
                'dspSsuPd': '200',  # Доступные значения: 10, 50, 100, 200
                'szkbuChkbx': ['011', '012', '013'],  # Prime, Standard, Growth
                'mgrMiTxtBx': '',  # Company name (пустое)
                'eqMgrCd': '',  # Code (пустое)
                'jjHisiKbnChkbx': False  # Delisted companies checkbox
            }

        # Настройка Chrome WebDriver
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Шаг 1: Открытие страницы поиска
            print("Шаг 1: Открытие страницы поиска...")
            driver.get(self.base_url + self.search_url)

            # Ждем загрузки страницы
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "JJK020010Form"))
            )

            if debug:
                # Сохраняем скриншот для отладки
                driver.save_screenshot("debug_page_loaded.png")
                print("Скриншот сохранен: debug_page_loaded.png")

                # Выводим информацию о форме
                self._debug_form_info(driver)

            # Заполняем форму с правильными параметрами
            self._fill_form_selenium_corrected(driver, search_params)

            # Шаг 2: Отправка формы через JavaScript (как на сайте)
            print("Шаг 2: Отправка формы...")

            try:
                # Включаем отключенные поля перед отправкой
                driver.execute_script("""
                    // Включаем отключенные поля
                    document.querySelector('input[name="ListShow"]').disabled = false;
                    document.querySelector('input[name="Show"]').disabled = false;
                    document.querySelector('input[name="Switch"]').disabled = false;
                """)

                # Отправляем форму через JavaScript как на сайте
                driver.execute_script("""
                    var form = document.forms['JJK020010Form'];
                    var listShowInput = form.ListShow;
                    submitPage(form, listShowInput);
                """)

                # Ждем загрузки результатов или изменения страницы
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "table.tableStyle01, table")) > 1 or
                              "result" in d.current_url.lower() or
                              len(d.find_elements(By.CSS_SELECTOR, "tr")) > 10
                )

            except Exception as submit_error:
                print(f"Ошибка при отправке через JavaScript: {submit_error}")

                # Альтернативный способ - найти и нажать кнопку поиска
                try:
                    search_button = driver.find_element(By.CSS_SELECTOR, "input[name='searchButton']")
                    driver.execute_script("arguments[0].click();", search_button)

                    WebDriverWait(driver, 15).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table")) > 1
                    )
                except:
                    print("Не удалось отправить форму, пробуем получить данные с текущей страницы...")

            if debug:
                driver.save_screenshot("debug_after_submit.png")
                print("Скриншот после отправки: debug_after_submit.png")

            # Получаем HTML страницы результатов
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Извлекаем данные из таблицы
            results = self._parse_table_data(soup)

            return {
                "success": True,
                "data": results,
                "timestamp": datetime.now().isoformat(),
                "method": "selenium",
                "total_records": len(results),
                "current_url": driver.current_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Selenium ошибка: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            if driver:
                driver.quit()

    def _fill_form_selenium_corrected(self, driver, search_params):
        """
        Заполнение формы с правильными параметрами
        """
        try:
            # 1. Количество отображаемых компаний
            if 'dspSsuPd' in search_params:
                dsp_select = Select(driver.find_element(By.NAME, "dspSsuPd"))
                value = str(search_params['dspSsuPd'])
                if value in ['10', '50', '100', '200']:
                    dsp_select.select_by_value(value)
                    print(f"Выбрано количество компаний: {value}")
                else:
                    print(f"Недопустимое значение для dspSsuPd: {value}, используется значение по умолчанию")

            # 2. Название компании
            if 'mgrMiTxtBx' in search_params and search_params['mgrMiTxtBx']:
                company_input = driver.find_element(By.NAME, "mgrMiTxtBx")
                company_input.clear()
                company_input.send_keys(search_params['mgrMiTxtBx'])
                print(f"Введено название компании: {search_params['mgrMiTxtBx']}")

            # 3. Код компании
            if 'eqMgrCd' in search_params and search_params['eqMgrCd']:
                code_input = driver.find_element(By.NAME, "eqMgrCd")
                code_input.clear()
                code_input.send_keys(search_params['eqMgrCd'])
                print(f"Введен код компании: {search_params['eqMgrCd']}")

            # 4. Сегменты рынка (чекбоксы)
            if 'szkbuChkbx' in search_params:
                # Сначала снимаем все галочки
                checkboxes = driver.find_elements(By.NAME, "szkbuChkbx")
                for cb in checkboxes:
                    if cb.is_selected():
                        cb.click()

                # Затем отмечаем нужные
                market_segments = search_params['szkbuChkbx']
                if isinstance(market_segments, str):
                    market_segments = [market_segments]

                for segment in market_segments:
                    try:
                        checkbox = driver.find_element(By.CSS_SELECTOR, f"input[name='szkbuChkbx'][value='{segment}']")
                        if not checkbox.is_selected():
                            checkbox.click()
                            print(f"Выбран сегмент рынка: {segment}")
                    except Exception as e:
                        print(f"Не удалось выбрать сегмент {segment}: {e}")

            # 5. Чекбокс delisted companies
            if 'jjHisiKbnChkbx' in search_params:
                delisted_cb = driver.find_element(By.NAME, "jjHisiKbnChkbx")
                current_state = delisted_cb.is_selected()
                desired_state = bool(search_params['jjHisiKbnChkbx'])

                if current_state != desired_state:
                    delisted_cb.click()
                    print(f"Delisted companies checkbox: {desired_state}")

        except Exception as e:
            print(f"Ошибка при заполнении формы: {e}")

    def _debug_form_info(self, driver):
        """
        Отладочная функция для анализа структуры формы
        """
        try:
            print("\n=== ОТЛАДОЧНАЯ ИНФОРМАЦИЯ О ФОРМЕ ===")

            # Найти все формы
            forms = driver.find_elements(By.TAG_NAME, "form")
            print(f"Найдено форм: {len(forms)}")

            for i, form in enumerate(forms):
                print(f"\n--- Форма {i + 1} ---")
                print(f"Action: {form.get_attribute('action')}")
                print(f"Method: {form.get_attribute('method')}")

                # Найти все поля ввода
                inputs = form.find_elements(By.TAG_NAME, "input")
                selects = form.find_elements(By.TAG_NAME, "select")
                textareas = form.find_elements(By.TAG_NAME, "textarea")

                print(f"Input полей: {len(inputs)}")
                print(f"Select полей: {len(selects)}")
                print(f"Textarea полей: {len(textareas)}")

                # Детали input полей
                for j, inp in enumerate(inputs[:10]):  # Показываем только первые 10
                    name = inp.get_attribute('name')
                    inp_type = inp.get_attribute('type')
                    value = inp.get_attribute('value')
                    print(f"  Input {j + 1}: name='{name}', type='{inp_type}', value='{value}'")

                # Детали select полей
                for j, sel in enumerate(selects[:5]):  # Показываем только первые 5
                    name = sel.get_attribute('name')
                    options = sel.find_elements(By.TAG_NAME, "option")
                    print(f"  Select {j + 1}: name='{name}', options={len(options)}")
                    for k, opt in enumerate(options[:3]):  # Первые 3 опции
                        opt_value = opt.get_attribute('value')
                        opt_text = opt.text
                        print(f"    Option {k + 1}: value='{opt_value}', text='{opt_text}'")

            print("=== КОНЕЦ ОТЛАДОЧНОЙ ИНФОРМАЦИИ ===\n")

        except Exception as e:
            print(f"Ошибка в отладке формы: {e}")

    def _fill_form_selenium(self, driver, search_params):
        """
        Заполнение формы с помощью Selenium (улучшенная версия)
        """
        for field_name, field_value in search_params.items():
            try:
                # Пробуем найти поле по имени
                elements = driver.find_elements(By.NAME, field_name)
                if not elements:
                    print(f"Поле {field_name} не найдено")
                    continue

                element = elements[0]

                # Проверяем, видимо ли поле
                if not element.is_displayed():
                    print(f"Поле {field_name} не видимо")
                    continue

                # Определяем тип элемента и заполняем соответствующим образом
                tag_name = element.tag_name.lower()
                element_type = element.get_attribute('type')

                if tag_name == 'select':
                    try:
                        select = Select(element)
                        # Пробуем выбрать по значению
                        select.select_by_value(str(field_value))
                        print(f"Поле {field_name} заполнено значением: {field_value}")
                    except Exception as e:
                        print(f"Не удалось выбрать значение {field_value} в select {field_name}: {e}")
                        # Пробуем выбрать по тексту
                        try:
                            select.select_by_visible_text(str(field_value))
                            print(f"Поле {field_name} заполнено по тексту: {field_value}")
                        except:
                            print(f"Не удалось заполнить select {field_name}")

                elif element_type == 'checkbox':
                    current_state = element.is_selected()
                    desired_state = str(field_value).lower() in ['true', '1', 'on', 'checked']
                    if current_state != desired_state:
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Checkbox {field_name} изменен на: {desired_state}")

                elif element_type == 'radio':
                    if str(field_value).lower() in ['true', '1', 'on']:
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Radio {field_name} выбран")

                elif element_type in ['text', 'number', 'email', 'password'] or element_type is None:
                    try:
                        element.clear()
                        element.send_keys(str(field_value))
                        print(f"Поле {field_name} заполнено: {field_value}")
                    except Exception as e:
                        print(f"Не удалось заполнить текстовое поле {field_name}: {e}")
                else:
                    print(f"Неизвестный тип поля {field_name}: {element_type}")

            except Exception as e:
                print(f"Общая ошибка при заполнении поля {field_name}: {e}")

    def _parse_table_data(self, soup):
        """
        Парсинг данных из таблицы результатов
        """
        results = []

        # Ищем все таблицы на странице
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:  # Пропускаем таблицы без данных
                continue

            # Получаем заголовки
            headers = []
            header_row = rows[0]
            for th in header_row.find_all(['th', 'td']):
                headers.append(th.get_text(strip=True))

            # Если заголовки пустые, используем индексы
            if not any(headers):
                headers = [f'column_{i}' for i in range(len(header_row.find_all(['th', 'td'])))]

            # Парсим данные
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) == 0:
                    continue

                row_data = {}
                for i, cell in enumerate(cells):
                    header = headers[i] if i < len(headers) else f'column_{i}'
                    cell_text = cell.get_text(strip=True)

                    # Извлекаем ссылки, если есть
                    link = cell.find('a')
                    if link and link.get('href'):
                        row_data[f'{header}_link'] = link.get('href')

                    row_data[header] = cell_text

                if any(row_data.values()):  # Добавляем только непустые строки
                    results.append(row_data)

        return results

    def save_to_csv(self, data, filename='jpx_data.csv'):
        """
        Сохранение данных в CSV файл
        """
        if data.get('success') and data.get('data'):
            df = pd.DataFrame(data['data'])
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Данные сохранены в {filename}")
        else:
            print("Нет данных для сохранения")

    def save_to_json(self, data, filename='jpx_data.json'):
        """
        Сохранение данных в JSON файл
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Данные сохранены в {filename}")


def main():
    """
    Пример использования
    """
    scraper = JPXScraper()

    # Правильные параметры поиска на основе структуры формы
    search_params_requests = {
        'dspSsuPd': '200',  # Количество записей
        'szkbuChkbx': '011',  # Prime market
        'mgrMiTxtBx': '',  # Company name (пустое)
        'eqMgrCd': '',  # Code (пустое)
        'jjHisiKbnChkbx': '',  # Delisted companies (пустое = не отмечено)
        # Скрытые поля будут добавлены автоматически
    }

    # Параметры для Selenium
    search_params_selenium = {
        'dspSsuPd': '200',
        'szkbuChkbx': ['011', '012', '013'],  # Prime, Standard, Growth
        'mgrMiTxtBx': '',
        'eqMgrCd': '',
        'jjHisiKbnChkbx': False
    }

    print("=== Скрапинг с помощью requests ===")
    result_requests = scraper.scrape_with_requests(search_params_requests)
    print(f"Результат requests: {result_requests.get('success')}")
    if result_requests.get('success'):
        print(f"Найдено записей: {len(result_requests['data'])}")
        scraper.save_to_csv(result_requests, 'jpx_requests.csv')
        scraper.save_to_json(result_requests, 'jpx_requests.json')

        # Показываем первые несколько записей
        if result_requests['data']:
            print("\nПример данных:")
            for i, record in enumerate(result_requests['data'][:3]):
                print(f"Запись {i + 1}: {record}")
    else:
        print(f"Ошибка: {result_requests.get('error')}")

    print("\n=== Скрапинг с помощью Selenium (с отладкой) ===")
    result_selenium = scraper.scrape_with_selenium(search_params_selenium, headless=False, debug=True)
    print(f"Результат selenium: {result_selenium.get('success')}")
    if result_selenium.get('success'):
        print(f"Найдено записей: {len(result_selenium['data'])}")
        scraper.save_to_csv(result_selenium, 'jpx_selenium.csv')
        scraper.save_to_json(result_selenium, 'jpx_selenium.json')

        # Показываем первые несколько записей
        if result_selenium['data']:
            print("\nПример данных:")
            for i, record in enumerate(result_selenium['data'][:3]):
                print(f"Запись {i + 1}: {record}")
    else:
        print(f"Ошибка: {result_selenium.get('error')}")


# Дополнительная функция для быстрого тестирования
def quick_test():
    """
    Быстрый тест только requests
    """
    scraper = JPXScraper()

    # Простой запрос всех Prime компаний
    result = scraper.scrape_with_requests({
        'dspSsuPd': '200',
        'szkbuChkbx': '011'  # Только Prime
    })

    if result['success']:
        print(f"✅ Успешно получено {len(result['data'])} записей")

        # Анализируем структуру данных
        if result['data']:
            first_record = result['data'][0]
            print(f"Структура записи: {list(first_record.keys())}")
            print(f"Пример записи: {first_record}")

        return result
    else:
        print(f"❌ Ошибка: {result['error']}")
        return None


if __name__ == "__main__":
    # Раскомментируйте нужную функцию:

    # Полный тест обеих версий
    main()

    # Или быстрый тест только requests
    # quick_test()