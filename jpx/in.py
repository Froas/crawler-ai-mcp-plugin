import requests
from bs4 import BeautifulSoup
import json


def jpx_two_step_request():
    """
    Two-step request approach (as in Insomnia)
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })

    # Form data with same parameters as in Insomnia
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
        # Step 1: Open page
        print("Request 1: Open page...")
        url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

        response1 = session.post(url, data=form_data)
        response1.raise_for_status()

        print(f"Request 1 - Status: {response1.status_code}")
        print(f"Request 1 - URL: {response1.url}")

        with open('jpx_step1_search_page.html', 'w', encoding='utf-8') as f:
            f.write(response1.text)
        print("Saved first step to jpx_step1_search_page.html")

        # Step 2: Get results
        print("\nRequest 2: Getting results...")

        response2 = session.post(url, data=form_data)
        response2.raise_for_status()

        print(f"Request 2 - Status: {response2.status_code}")
        print(f"Request 2 - URL: {response2.url}")
        print(f"Request 2 - Size: {len(response2.content)} bytes")

        # Save HTML response
        with open('jpx_step2_results.html', 'w', encoding='utf-8') as f:
            f.write(response2.text)
        print("Saved to jpx_step2_results.html")

        # Parse HTML content
        soup = BeautifulSoup(response2.content, 'html.parser')

        # Find all tables
        tables = soup.find_all('table')
        print(f"\nFound tables: {len(tables)}")

        # Extract company data
        company_data = []
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 1:
                print(f"Table {i + 1}: {len(rows)} rows")

                # Process each row
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:  # Minimum code and name
                        row_data = []
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            # Also save links
                            link = cell.find('a')
                            if link and link.get('href'):
                                row_data.append({
                                    'text': text,
                                    'link': link.get('href')
                                })
                            else:
                                row_data.append(text)

                        if any(str(cell).strip() for cell in row_data if isinstance(cell, str)):  # Has non-empty data
                            company_data.append({
                                'table': i,
                                'row': j,
                                'data': row_data
                            })

        # Check if we got results
        if company_data:
            print(f"\n✅ Found data records: {len(company_data)}")

            # Show first few records
            print("\nSample data:")
            for i, record in enumerate(company_data[:5]):
                print(f"Record {i + 1}: {record['data']}")
        else:
            print("\n❌ Company data not found")

            # Check what's in the response
            title = soup.find('title')
            if title:
                print(f"Page title: {title.get_text()}")

            # Look for any text that might indicate results
            content_divs = soup.find_all(['div', 'p'], class_=True)
            for div in content_divs[:5]:
                text = div.get_text(strip=True)
                if text and len(text) > 10:
                    print(f"Content: {text[:100]}...")

        # Save structured data
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
        print("\nFinal data saved to jpx_final_data.json")

        return result

    except requests.exceptions.RequestException as e:
        error_result = {
            'success': False,
            'error': f"HTTP error: {str(e)}"
        }
        print(f"Request error: {e}")
        return error_result
    except Exception as e:
        error_result = {
            'success': False,
            'error': f"General error: {str(e)}"
        }
        print(f"General error: {e}")
        return error_result


def jpx_simple_request():
    """
    Simple request as in Insomnia (keeping for comparison)
    """
    # URL with jsessionid (as in Insomnia)
    url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

    # Exact same parameters as in Insomnia
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

    # Headers as in browser
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
        print("Sending simple POST request...")
        response = requests.post(url, data=form_data, headers=headers, timeout=30)
        response.raise_for_status()

        print(f"Response status: {response.status_code}")
        print(f"Response size: {len(response.content)} bytes")

        # Save raw HTML
        with open('jpx_simple_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("HTML saved to jpx_simple_response.html")

        return {'success': True, 'method': 'simple'}

    except Exception as e:
        print(f"Simple request error: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    print("=" * 60)
    print("TWO-STEP REQUEST (as in Insomnia)")
    print("=" * 60)
    result = jpx_two_step_request()

    if result.get('success'):
        print(f"\n🎉 SUCCESS!")
        print(f"📊 Records found: {result.get('company_records', 0)}")
        print(f"📋 Tables: {result.get('tables_count', 0)}")
    else:
        print(f"\n❌ ERROR: {result.get('error')}")

    print("\n" + "=" * 60)
    print("SIMPLE REQUEST (for comparison)")
    print("=" * 60)
    result2 = jpx_simple_request()

    print(f"\nSimple request result: {result2.get('success')}")