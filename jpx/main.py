import requests
from bs4 import BeautifulSoup
import json
import time
import re


def jpx_two_step_request():
    """
    Original working function (single page)
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })

    # Form-data parameters exactly as in Insomnia
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
        # FIRST REQUEST - open search page
        print("REQUEST 1: Opening search page...")
        url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

        response1 = session.post(url, data=form_data)
        response1.raise_for_status()

        print(f"Request 1 - Status: {response1.status_code}")

        # SECOND REQUEST - get results
        print("\nREQUEST 2: Getting results...")
        response2 = session.post(url, data=form_data)
        response2.raise_for_status()

        print(f"Request 2 - Status: {response2.status_code}")
        print(f"Request 2 - Response size: {len(response2.content)} bytes")

        # Parse results
        soup = BeautifulSoup(response2.content, 'html.parser')
        enhanced_data = parse_companies_from_soup(soup)

        print(f"\n✅ Found companies: {len(enhanced_data)}")

        # Save result
        result = {
            'success': True,
            'method': 'two_step_request',
            'companies_count': len(enhanced_data),
            'companies': enhanced_data
        }

        return result

    except Exception as e:
        print(f"Error: {e}")
        return {'success': False, 'error': str(e)}


def jpx_with_pagination(max_pages=None, delay=1, search_params=None):
    """
    Version with pagination based on working code
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
            print(f"📄 PAGE {current_page}")
            if total_pages:
                print(f"📊 Progress: {current_page}/{total_pages}")
            if total_items:
                print(f"🎯 Total companies: {total_items}")
            print(f"{'=' * 60}")

            # Prepare parameters for current page
            form_data = search_params.copy()

            # FIRST REQUEST
            print(f"REQUEST 1: Initializing page {current_page}...")
            url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid=00B11CD09F0EE52A255F89C8F3D3F8A21"

            response1 = session.post(url, data=form_data)
            response1.raise_for_status()

            # SECOND REQUEST
            print(f"REQUEST 2: Getting data for page {current_page}...")

            # For pages after the first one, use different logic
            if current_page > 1:
                # Parse first response to get results form
                soup_temp = BeautifulSoup(response1.content, 'html.parser')

                # Look for JJK020030Form (results form with pagination)
                form_030 = soup_temp.find('form', attrs={'name': 'JJK020030Form'})

                if form_030:
                    print(f"Found JJK020030Form, using for page {current_page}")

                    # Collect all hidden fields from the form
                    pagination_form_data = {}
                    hidden_inputs = form_030.find_all('input', {'type': 'hidden'})

                    for hidden in hidden_inputs:
                        name = hidden.get('name')
                        value = hidden.get('value', '')
                        if name:
                            pagination_form_data[name] = value

                    # Add pagination parameters
                    pagination_form_data.update({
                        'Transition': 'Transition',
                        'pageNo': str(current_page),
                        'currentPage': str(current_page)
                    })

                    # Use results URL
                    url_results = "https://www2.jpx.co.jp/tseHpFront/JJK020030Action.do"
                    response2 = session.post(url_results, data=pagination_form_data)
                else:
                    # Fallback: use original form
                    print(f"JJK020030Form not found, using original form")
                    response2 = session.post(url, data=form_data)
            else:
                # First page: standard second request
                response2 = session.post(url, data=form_data)

            response2.raise_for_status()
            print(f"Request 2 - Status: {response2.status_code}, Size: {len(response2.content)} bytes")

            # Save HTML of each page
            with open(f'jpx_page_{current_page}.html', 'w', encoding='utf-8') as f:
                f.write(response2.text)

            # Parse companies from current page
            soup = BeautifulSoup(response2.content, 'html.parser')
            page_companies = parse_companies_from_soup(soup)

            print(f"📊 Found companies on page {current_page}: {len(page_companies)}")

            # Add page number to each company
            for company in page_companies:
                company['page'] = current_page

            # Add to overall list
            all_companies.extend(page_companies)

            # Update statistics
            update_statistics(page_companies, all_statistics)

            # Get pagination information
            pagination_info = extract_pagination_info(soup)

            if pagination_info:
                total_items = pagination_info.get('total_items')
                total_pages = pagination_info.get('total_pages')
                has_next = pagination_info.get('has_next_page', False)

                print(f"\n📖 Pagination:")
                print(f"  Current page: {pagination_info.get('current_page')}")
                print(f"  Total pages: {total_pages}")
                print(f"  Total items: {total_items}")
                print(f"  Has next: {has_next}")

                # Check continuation conditions
                if not has_next or (total_pages and current_page >= total_pages):
                    print("🏁 Reached last page")
                    break

                if max_pages and current_page >= max_pages:
                    print(f"🛑 Reached limit: {max_pages} pages")
                    break

                if len(page_companies) == 0:
                    print("🛑 No companies on page")
                    break

                # Move to next page
                current_page += 1

                if delay > 0:
                    print(f"⏱️ Delay {delay} sec...")
                    time.sleep(delay)

            else:
                print("📖 Pagination not found")
                if len(page_companies) == 0:
                    print("🛑 No companies and no pagination")
                    break
                else:
                    print("📄 Possibly single page")
                    break

        # Final results
        print(f"\n🎉 COMPLETED!")
        print(f"📊 Pages processed: {current_page}")
        print(f"🏢 Total companies: {len(all_companies)}")

        # Show statistics
        show_final_statistics(all_statistics)

        # Save results
        result = save_results(all_companies, all_statistics, current_page, total_items)

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
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
    Parse companies from soup (exactly like in working code)
    """
    enhanced_data = []

    # Look for all hidden fields with company data
    hidden_inputs = soup.find_all('input', {'type': 'hidden'})
    company_records = {}

    for hidden in hidden_inputs:
        name = hidden.get('name', '')
        value = hidden.get('value', '')

        # Parse fields in format ccJjCrpSelKekkLst_st[N].field
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

    # Parse visible data from table
    tables = soup.find_all('table')
    company_data = []

    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:  # Minimum: code, name, segment, industry
                code_cell = cells[0]
                code_text = code_cell.get_text(strip=True)

                if code_text.isdigit() and len(code_text) == 5:  # Company code
                    company_info = {
                        'code': code_text,
                        'name': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                        'market_segment': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                        'industry': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                        'fiscal_year_end': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                        'alerts': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                    }

                    # Look for links
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

    # Combine data from hidden fields with visible data
    for company in company_data:
        code = company['code']
        enhanced_company = company.copy()

        # Add data from hidden fields if found
        for record in company_records.values():
            if record.get('eqMgrCd') == code:
                enhanced_company['hidden_fields'] = record
                break

        enhanced_data.append(enhanced_company)

    # If main parsing didn't yield results, use only hidden fields
    if not enhanced_data and company_records:
        for index, record in sorted(company_records.items()):
            if 'eqMgrCd' in record:  # Has company code
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
    Extract pagination information from JPX
    """
    pagination_info = {
        'current_page': 1,
        'total_pages': 1,
        'total_items': 0,
        'items_per_page': 10,
        'has_next_page': False,
        'has_prev_page': False
    }

    # Look for div with class pagingmenu
    paging_menu = soup.find('div', class_='pagingmenu')

    if paging_menu:
        # Extract item count information "Display of 1-10 items/1622"
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

        # Look for current page by class "current"
        current_element = paging_menu.find('b', class_='current')
        if current_element:
            try:
                pagination_info['current_page'] = int(current_element.get_text().strip())
            except ValueError:
                pass

        # Check for "Next" button
        next_div = paging_menu.find('div', class_='next_e')
        if next_div and next_div.find('a'):
            pagination_info['has_next_page'] = True

        # If current page is greater than 1, there's a previous page
        if pagination_info['current_page'] > 1:
            pagination_info['has_prev_page'] = True

    return pagination_info


def update_statistics(companies, all_statistics):
    """
    Update overall statistics
    """
    for company in companies:
        segment = company.get('market_segment', 'Unknown')
        industry = company.get('industry', 'Unknown')

        all_statistics['segments'][segment] = all_statistics['segments'].get(segment, 0) + 1
        all_statistics['industries'][industry] = all_statistics['industries'].get(industry, 0) + 1


def show_final_statistics(all_statistics):
    """
    Show final statistics
    """
    if all_statistics['segments']:
        print(f"\n📈 Statistics by segments:")
        for segment, count in sorted(all_statistics['segments'].items()):
            print(f"  {segment}: {count}")

    if all_statistics['industries']:
        print(f"\n🏭 Top 10 industries:")
        top_industries = sorted(all_statistics['industries'].items(), key=lambda x: x[1], reverse=True)[:10]
        for industry, count in top_industries:
            print(f"  {industry}: {count}")


def save_results(all_companies, all_statistics, pages_processed, total_items):
    """
    Save results to files
    """
    # Full data
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
    print(f"\n💾 Full data: jpx_all_companies.json")

    # Simplified data
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
    print(f"💾 Simplified data: jpx_all_companies_simple.json")

    return result


if __name__ == "__main__":
    print("🚀 JPX SCRAPER (Based on working code)")
    print("=" * 60)

    mode = input(
        "\nSelect mode:\n1. Single page (fast)\n2. All pages\n3. Limited number of pages\nYour choice (1-3): ").strip()

    if mode == "1":
        print("\n📄 MODE: Single page")
        result = jpx_two_step_request()

        if result.get('success'):
            print(f"\n🎉 SUCCESS! Found companies: {result.get('companies_count', 0)}")
        else:
            print(f"\n❌ ERROR: {result.get('error')}")

    elif mode == "2":
        print("\n📚 MODE: All pages")
        delay = input("Delay between requests in seconds (default 1): ").strip()
        delay = float(delay) if delay.replace('.', '').isdigit() else 1.0

        print(f"⚠️ This may take a long time!")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm == 'y':
            result = jpx_with_pagination(max_pages=None, delay=delay)

            if result.get('success'):
                print(f"\n🎉 SUCCESS! Companies: {result.get('total_companies', 0)}")
            else:
                print(f"\n⚠️ PARTIAL RESULT: {result.get('companies_collected', 0)} companies")

    elif mode == "3":
        print("\n📑 MODE: Limited number of pages")

        max_pages = input("Maximum pages: ").strip()
        max_pages = int(max_pages) if max_pages.isdigit() else 3

        delay = input("Delay in seconds (default 1): ").strip()
        delay = float(delay) if delay.replace('.', '').isdigit() else 1.0

        result = jpx_with_pagination(max_pages=max_pages, delay=delay)

        if result.get('success'):
            print(f"\n🎉 SUCCESS! Companies: {result.get('total_companies', 0)}")
        else:
            print(f"\n⚠️ PARTIAL RESULT: {result.get('companies_collected', 0)} companies")

    else:
        print("❌ Invalid choice")

    print(f"\n✅ Done!")