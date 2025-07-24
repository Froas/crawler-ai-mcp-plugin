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
        Scraping data using requests + BeautifulSoup
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
            # Step 1: Get the search page
            print("Step 1: Getting search page...")
            search_response = self.session.get(self.base_url + self.search_url)
            search_response.raise_for_status()

            # Parse the search page HTML
            soup = BeautifulSoup(search_response.content, 'html.parser')

            # Find the form and get all hidden fields
            form = soup.find('form')
            if not form:
                return {"success": False, "error": "Form not found"}

            # Collect all form data
            form_data = {}

            # Add hidden fields
            for hidden_input in form.find_all('input', {'type': 'hidden'}):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    form_data[name] = value

            # Add search parameters
            form_data.update(search_params)

            # Step 2: Submit form to get results
            print("Step 2: Submitting form...")

            # Set Referer
            self.session.headers['Referer'] = self.base_url + self.search_url

            # Send POST request
            results_response = self.session.post(
                self.base_url + self.search_url,
                data=form_data
            )
            results_response.raise_for_status()

            # Parse results
            results_soup = BeautifulSoup(results_response.content, 'html.parser')

            # Extract data from table
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
                "error": f"HTTP error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"General error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def scrape_with_selenium(self, search_params=None, headless=True, debug=False):
        """
        Scraping data using Selenium
        """
        if search_params is None:
            # Corrected search parameters based on actual form structure
            search_params = {
                'dspSsuPd': '200',  # Available values: 10, 50, 100, 200
                'szkbuChkbx': ['011', '012', '013'],  # Prime, Standard, Growth
                'mgrMiTxtBx': '',  # Company name (empty)
                'eqMgrCd': '',  # Code (empty)
                'jjHisiKbnChkbx': False  # Delisted companies checkbox
            }

        # Chrome WebDriver setup
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

            # Step 1: Open search page
            print("Step 1: Opening search page...")
            driver.get(self.base_url + self.search_url)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "JJK020010Form"))
            )

            if debug:
                # Save screenshot for debugging
                driver.save_screenshot("debug_page_loaded.png")
                print("Screenshot saved: debug_page_loaded.png")

                # Output form information
                self._debug_form_info(driver)

            # Fill form with correct parameters
            self._fill_form_selenium_corrected(driver, search_params)

            # Step 2: Submit form via JavaScript (as on the website)
            print("Step 2: Submitting form...")

            try:
                # Enable disabled fields before submission
                driver.execute_script("""
                    // Enable disabled fields
                    document.querySelector('input[name="ListShow"]').disabled = false;
                    document.querySelector('input[name="Show"]').disabled = false;
                    document.querySelector('input[name="Switch"]').disabled = false;
                """)

                # Submit form via JavaScript as on the website
                driver.execute_script("""
                    var form = document.forms['JJK020010Form'];
                    var listShowInput = form.ListShow;
                    submitPage(form, listShowInput);
                """)

                # Wait for results to load or page to change
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "table.tableStyle01, table")) > 1 or
                              "result" in d.current_url.lower() or
                              len(d.find_elements(By.CSS_SELECTOR, "tr")) > 10
                )

            except Exception as submit_error:
                print(f"Error submitting via JavaScript: {submit_error}")

                # Alternative method - find and click search button
                try:
                    search_button = driver.find_element(By.CSS_SELECTOR, "input[name='searchButton']")
                    driver.execute_script("arguments[0].click();", search_button)

                    WebDriverWait(driver, 15).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table")) > 1
                    )
                except:
                    print("Failed to submit form, trying to get data from current page...")

            if debug:
                driver.save_screenshot("debug_after_submit.png")
                print("Screenshot after submission: debug_after_submit.png")

            # Get HTML of results page
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Extract data from table
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
                "error": f"Selenium error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            if driver:
                driver.quit()

    def _fill_form_selenium_corrected(self, driver, search_params):
        """
        Fill form with correct parameters
        """
        try:
            # 1. Number of companies to display
            if 'dspSsuPd' in search_params:
                dsp_select = Select(driver.find_element(By.NAME, "dspSsuPd"))
                value = str(search_params['dspSsuPd'])
                if value in ['10', '50', '100', '200']:
                    dsp_select.select_by_value(value)
                    print(f"Selected number of companies: {value}")
                else:
                    print(f"Invalid value for dspSsuPd: {value}, using default value")

            # 2. Company name
            if 'mgrMiTxtBx' in search_params and search_params['mgrMiTxtBx']:
                company_input = driver.find_element(By.NAME, "mgrMiTxtBx")
                company_input.clear()
                company_input.send_keys(search_params['mgrMiTxtBx'])
                print(f"Entered company name: {search_params['mgrMiTxtBx']}")

            # 3. Company code
            if 'eqMgrCd' in search_params and search_params['eqMgrCd']:
                code_input = driver.find_element(By.NAME, "eqMgrCd")
                code_input.clear()
                code_input.send_keys(search_params['eqMgrCd'])
                print(f"Entered company code: {search_params['eqMgrCd']}")

            # 4. Market segments (checkboxes)
            if 'szkbuChkbx' in search_params:
                # First uncheck all checkboxes
                checkboxes = driver.find_elements(By.NAME, "szkbuChkbx")
                for cb in checkboxes:
                    if cb.is_selected():
                        cb.click()

                # Then check the required ones
                market_segments = search_params['szkbuChkbx']
                if isinstance(market_segments, str):
                    market_segments = [market_segments]

                for segment in market_segments:
                    try:
                        checkbox = driver.find_element(By.CSS_SELECTOR, f"input[name='szkbuChkbx'][value='{segment}']")
                        if not checkbox.is_selected():
                            checkbox.click()
                            print(f"Selected market segment: {segment}")
                    except Exception as e:
                        print(f"Failed to select segment {segment}: {e}")

            # 5. Delisted companies checkbox
            if 'jjHisiKbnChkbx' in search_params:
                delisted_cb = driver.find_element(By.NAME, "jjHisiKbnChkbx")
                current_state = delisted_cb.is_selected()
                desired_state = bool(search_params['jjHisiKbnChkbx'])

                if current_state != desired_state:
                    delisted_cb.click()
                    print(f"Delisted companies checkbox: {desired_state}")

        except Exception as e:
            print(f"Error filling form: {e}")

    def _debug_form_info(self, driver):
        """
        Debug function to analyze form structure
        """
        try:
            print("\n=== FORM DEBUG INFORMATION ===")

            # Find all forms
            forms = driver.find_elements(By.TAG_NAME, "form")
            print(f"Forms found: {len(forms)}")

            for i, form in enumerate(forms):
                print(f"\n--- Form {i + 1} ---")
                print(f"Action: {form.get_attribute('action')}")
                print(f"Method: {form.get_attribute('method')}")

                # Find all input fields
                inputs = form.find_elements(By.TAG_NAME, "input")
                selects = form.find_elements(By.TAG_NAME, "select")
                textareas = form.find_elements(By.TAG_NAME, "textarea")

                print(f"Input fields: {len(inputs)}")
                print(f"Select fields: {len(selects)}")
                print(f"Textarea fields: {len(textareas)}")

                # Input field details
                for j, inp in enumerate(inputs[:10]):  # Show only first 10
                    name = inp.get_attribute('name')
                    inp_type = inp.get_attribute('type')
                    value = inp.get_attribute('value')
                    print(f"  Input {j + 1}: name='{name}', type='{inp_type}', value='{value}'")

                # Select field details
                for j, sel in enumerate(selects[:5]):  # Show only first 5
                    name = sel.get_attribute('name')
                    options = sel.find_elements(By.TAG_NAME, "option")
                    print(f"  Select {j + 1}: name='{name}', options={len(options)}")
                    for k, opt in enumerate(options[:3]):  # First 3 options
                        opt_value = opt.get_attribute('value')
                        opt_text = opt.text
                        print(f"    Option {k + 1}: value='{opt_value}', text='{opt_text}'")

            print("=== END DEBUG INFORMATION ===\n")

        except Exception as e:
            print(f"Error in form debugging: {e}")

    def _fill_form_selenium(self, driver, search_params):
        """
        Fill form using Selenium (improved version)
        """
        for field_name, field_value in search_params.items():
            try:
                # Try to find field by name
                elements = driver.find_elements(By.NAME, field_name)
                if not elements:
                    print(f"Field {field_name} not found")
                    continue

                element = elements[0]

                # Check if field is visible
                if not element.is_displayed():
                    print(f"Field {field_name} is not visible")
                    continue

                # Determine element type and fill accordingly
                tag_name = element.tag_name.lower()
                element_type = element.get_attribute('type')

                if tag_name == 'select':
                    try:
                        select = Select(element)
                        # Try to select by value
                        select.select_by_value(str(field_value))
                        print(f"Field {field_name} filled with value: {field_value}")
                    except Exception as e:
                        print(f"Failed to select value {field_value} in select {field_name}: {e}")
                        # Try to select by text
                        try:
                            select.select_by_visible_text(str(field_value))
                            print(f"Field {field_name} filled by text: {field_value}")
                        except:
                            print(f"Failed to fill select {field_name}")

                elif element_type == 'checkbox':
                    current_state = element.is_selected()
                    desired_state = str(field_value).lower() in ['true', '1', 'on', 'checked']
                    if current_state != desired_state:
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Checkbox {field_name} changed to: {desired_state}")

                elif element_type == 'radio':
                    if str(field_value).lower() in ['true', '1', 'on']:
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Radio {field_name} selected")

                elif element_type in ['text', 'number', 'email', 'password'] or element_type is None:
                    try:
                        element.clear()
                        element.send_keys(str(field_value))
                        print(f"Field {field_name} filled: {field_value}")
                    except Exception as e:
                        print(f"Failed to fill text field {field_name}: {e}")
                else:
                    print(f"Unknown field type {field_name}: {element_type}")

            except Exception as e:
                print(f"General error filling field {field_name}: {e}")

    def _parse_table_data(self, soup):
        """
        Parse data from results table
        """
        results = []

        # Find all tables on the page
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:  # Skip tables without data
                continue

            # Get headers
            headers = []
            header_row = rows[0]
            for th in header_row.find_all(['th', 'td']):
                headers.append(th.get_text(strip=True))

            # If headers are empty, use indices
            if not any(headers):
                headers = [f'column_{i}' for i in range(len(header_row.find_all(['th', 'td'])))]

            # Parse data
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) == 0:
                    continue

                row_data = {}
                for i, cell in enumerate(cells):
                    header = headers[i] if i < len(headers) else f'column_{i}'
                    cell_text = cell.get_text(strip=True)

                    # Extract links if present
                    link = cell.find('a')
                    if link and link.get('href'):
                        row_data[f'{header}_link'] = link.get('href')

                    row_data[header] = cell_text

                if any(row_data.values()):  # Add only non-empty rows
                    results.append(row_data)

        return results

    def save_to_csv(self, data, filename='jpx_data.csv'):
        """
        Save data to CSV file
        """
        if data.get('success') and data.get('data'):
            df = pd.DataFrame(data['data'])
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Data saved to {filename}")
        else:
            print("No data to save")

    def save_to_json(self, data, filename='jpx_data.json'):
        """
        Save data to JSON file
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")


def main():
    """
    Usage example
    """
    scraper = JPXScraper()

    # Correct search parameters based on form structure
    search_params_requests = {
        'dspSsuPd': '200',  # Number of records
        'szkbuChkbx': '011',  # Prime market
        'mgrMiTxtBx': '',  # Company name (empty)
        'eqMgrCd': '',  # Code (empty)
        'jjHisiKbnChkbx': '',  # Delisted companies (empty = unchecked)
        # Hidden fields will be added automatically
    }

    # Parameters for Selenium
    search_params_selenium = {
        'dspSsuPd': '200',
        'szkbuChkbx': ['011', '012', '013'],  # Prime, Standard, Growth
        'mgrMiTxtBx': '',
        'eqMgrCd': '',
        'jjHisiKbnChkbx': False
    }

    print("=== Scraping with requests ===")
    result_requests = scraper.scrape_with_requests(search_params_requests)
    print(f"Requests result: {result_requests.get('success')}")
    if result_requests.get('success'):
        print(f"Records found: {len(result_requests['data'])}")
        scraper.save_to_csv(result_requests, 'jpx_requests.csv')
        scraper.save_to_json(result_requests, 'jpx_requests.json')

        # Show first few records
        if result_requests['data']:
            print("\nSample data:")
            for i, record in enumerate(result_requests['data'][:3]):
                print(f"Record {i + 1}: {record}")
    else:
        print(f"Error: {result_requests.get('error')}")

    print("\n=== Scraping with Selenium (with debugging) ===")
    result_selenium = scraper.scrape_with_selenium(search_params_selenium, headless=False, debug=True)
    print(f"Selenium result: {result_selenium.get('success')}")
    if result_selenium.get('success'):
        print(f"Records found: {len(result_selenium['data'])}")
        scraper.save_to_csv(result_selenium, 'jpx_selenium.csv')
        scraper.save_to_json(result_selenium, 'jpx_selenium.json')

        # Show first few records
        if result_selenium['data']:
            print("\nSample data:")
            for i, record in enumerate(result_selenium['data'][:3]):
                print(f"Record {i + 1}: {record}")
    else:
        print(f"Error: {result_selenium.get('error')}")


# Additional function for quick testing
def quick_test():
    """
    Quick test using requests only
    """
    scraper = JPXScraper()

    # Simple request for all Prime companies
    result = scraper.scrape_with_requests({
        'dspSsuPd': '200',
        'szkbuChkbx': '011'  # Prime only
    })

    if result['success']:
        print(f"✅ Successfully retrieved {len(result['data'])} records")

        # Analyze data structure
        if result['data']:
            first_record = result['data'][0]
            print(f"Record structure: {list(first_record.keys())}")
            print(f"Sample record: {first_record}")

        return result
    else:
        print(f"❌ Error: {result['error']}")
        return None


if __name__ == "__main__":
    # Uncomment the function you need:

    # Full test of both versions
    main()

    # Or quick test using requests only
    # quick_test()