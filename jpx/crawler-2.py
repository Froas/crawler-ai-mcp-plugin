import asyncio
import json
import re
from datetime import datetime
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from crawlee import Request


class JPXScraperSimple:
    """
    Simple JPX scraper using BeautifulSoupCrawler
    """

    def __init__(self, max_pages=None, delay=1):
        self.max_pages = max_pages
        self.delay = delay
        self.all_companies = []
        self.all_statistics = {'segments': {}, 'industries': {}}
        self.current_page = 1
        self.total_items = None
        self.total_pages = None
        self.session_id = "00B11CD09F0EE52A255F89C8F3D3F8A21"

        # Default search parameters
        self.search_params = {
            'dspSsuPd': '500',
            'szkbuChkbxMapOut': '011>Prime<012>Standard<013>Growth<008>TOKYO',
            'ListShow': 'ListShow',
            'sniMtGmnId': '',
            'dspSsuPdMapOut': '10>10<50>50<100>100<200>200<',
            'mgrMiTxtBx': '',
            'eqMgrCd': '',
            'szkbuChkbx': '011'
        }

        # Initialize BeautifulSoup crawler - much simpler!
        self.crawler = BeautifulSoupCrawler(
            max_requests_per_crawl=1000,
            max_request_retries=3,
            # Removed use_extended_unique_key as it's not supported
        )

    async def setup_handlers(self):
        """Setup request handlers"""

        @self.crawler.router.handler('SEARCH_PAGE')
        async def handle_search_page(context: BeautifulSoupCrawlingContext) -> None:
            """Handle FIRST POST request - loads search page (no parsing needed)"""
            context.log.info("🚀 FIRST POST REQUEST: Search page loaded")
            context.log.info(f"First request URL: {context.request.url}")
            context.log.info(f"First request status: successful")

            # Now make SECOND POST request to the SAME URL with SAME parameters
            # This is exactly like the working requests code
            same_url = f"https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid={self.session_id}"

            import uuid
            unique_id = str(uuid.uuid4())

            # SECOND request - SAME URL, SAME parameters, but this one will return actual results
            second_request = Request.from_url(
                url=same_url,  # SAME URL as first request
                method="POST",  # SAME method
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': same_url,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'X-Second-Request': unique_id  # Mark as second request
                },
                payload=self._encode_form_data(self.search_params).encode('utf-8'),  # SAME payload
                label="SECOND_REQUEST",  # Different label to distinguish
                unique_key=f"second_post_request_{unique_id}"
            )

            context.log.info(f"📤 Enqueueing SECOND POST request to SAME URL")
            context.log.info(f"Second request unique_key: second_post_request_{unique_id}")
            await context.add_requests([second_request])

        @self.crawler.router.handler('SECOND_REQUEST')
        async def handle_second_request(context: BeautifulSoupCrawlingContext) -> None:
            """Handle SECOND POST request - this one has the actual results"""
            context.log.info("🎉 SECOND POST REQUEST: Getting actual results!")
            context.log.info(f"Second request URL: {context.request.url}")
            context.log.info(f"📄 Processing page {self.current_page}")

            # NOW we have the actual results page - BeautifulSoup already parsed!
            soup = context.soup
            context.log.info(f"✅ BeautifulSoup object ready with results")

            # Parse companies using our existing function
            page_companies = self._parse_companies_from_soup(soup)

            context.log.info(f"📊 Found {len(page_companies)} companies on page {self.current_page}")

            # If no companies found, let's debug
            if len(page_companies) == 0:
                tables = soup.find_all('table')
                context.log.info(f"🔍 Debug: Found {len(tables)} tables")
                hidden_inputs = soup.find_all('input', {'type': 'hidden'})
                context.log.info(f"🔍 Debug: Found {len(hidden_inputs)} hidden inputs")

                # Check for company records in hidden fields
                company_records = 0
                for hidden in hidden_inputs:
                    name = hidden.get('name', '')
                    if 'ccJjCrpSelKekkLst_st[' in name:
                        company_records += 1
                context.log.info(f"🔍 Debug: Found {company_records} company hidden fields")

            # Add metadata to companies
            for company in page_companies:
                company['page'] = self.current_page
                company['scraped_at'] = datetime.now().isoformat()

            # Push to Crawlee dataset
            if page_companies:
                await context.push_data(page_companies)
                context.log.info(f"💾 Pushed {len(page_companies)} companies to dataset")

            # Add to our list
            self.all_companies.extend(page_companies)
            self.update_statistics(page_companies, self.all_statistics)  # Fix: use self.update_statistics

            # Save HTML
            await self._save_page_html(str(soup), self.current_page)

            # Check pagination
            pagination_info = self.extract_pagination_info(soup)  # Fix: use self.extract_pagination_info

            if pagination_info:
                self.total_items = pagination_info.get('total_items')
                self.total_pages = pagination_info.get('total_pages')
                has_next = pagination_info.get('has_next_page', False)

                context.log.info(
                    f"📖 Pagination: page {pagination_info.get('current_page')}/{self.total_pages}, items: {self.total_items}, has_next: {has_next}")

                # Check if we should continue
                if self._should_continue_pagination(has_next, len(page_companies)):
                    await self._enqueue_next_page(context, soup)
                else:
                    context.log.info("🏁 Finished scraping")
                    await self._save_final_results()
            else:
                context.log.info("📖 No pagination found - single page")
                await self._save_final_results()

        @self.crawler.router.handler('RESULTS_PAGE')  # Keep this for backward compatibility
        async def handle_results_page(context: BeautifulSoupCrawlingContext) -> None:
            """Redirect to second request handler"""
            await handle_second_request(context)

        @self.crawler.router.handler('PAGINATION_PAGE')
        async def handle_pagination_page(context: BeautifulSoupCrawlingContext) -> None:
            """Handle pagination pages - exactly like working code"""
            context.log.info(f"🔄 PAGINATION: Processing page {self.current_page}")

            # For pagination, we need to process the current response first
            # to get the form data, then make another request
            soup = context.soup

            # Look for JJK020030Form (results form with pagination)
            form_030 = soup.find('form', attrs={'name': 'JJK020030Form'})

            if form_030:
                context.log.info(f"Found JJK020030Form for page {self.current_page}")

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
                    'pageNo': str(self.current_page),
                    'currentPage': str(self.current_page)
                })

                # Use results URL for pagination
                url_results = "https://www2.jpx.co.jp/tseHpFront/JJK020030Action.do"

                import uuid
                unique_id = str(uuid.uuid4())

                request = Request.from_url(
                    url=url_results,
                    method="POST",
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': url_results,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    },
                    payload=self._encode_form_data(pagination_form_data).encode('utf-8'),
                    label="SECOND_REQUEST",  # Reuse second request handler
                    unique_key=f"pagination_results_{self.current_page}_{unique_id}"
                )

                await context.add_requests([request])
            else:
                # Fallback: use original form (like working code)
                context.log.info(f"JJK020030Form not found, using original form")

                url = f"https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid={self.session_id}"

                import uuid
                unique_id = str(uuid.uuid4())

                request = Request.from_url(
                    url=url,
                    method="POST",
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': url,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    },
                    payload=self._encode_form_data(self.search_params).encode('utf-8'),
                    label="SECOND_REQUEST",
                    unique_key=f"fallback_results_{self.current_page}_{unique_id}"
                )

                await context.add_requests([request])

    def update_statistics(self, companies, all_statistics):
        """
        Update overall statistics (exactly like working code)
        """
        for company in companies:
            segment = company.get('market_segment', 'Unknown')
            industry = company.get('industry', 'Unknown')

            all_statistics['segments'][segment] = all_statistics['segments'].get(segment, 0) + 1
            all_statistics['industries'][industry] = all_statistics['industries'].get(industry, 0) + 1

    def show_final_statistics(self, all_statistics):
        """
        Show final statistics (exactly like working code)
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

    def save_results(self, all_companies, all_statistics, pages_processed, total_items):
        """
        Save results to files (exactly like working code)
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
                    'stock_prices_url': company.get('links', {}).get('stock_prices_url', '') if company.get(
                        'links') else ''
                }
                for company in all_companies
            ]
        }

        with open('jpx_all_companies_simple.json', 'w', encoding='utf-8') as f:
            json.dump(simple_result, f, ensure_ascii=False, indent=2)
        print(f"💾 Simplified data: jpx_all_companies_simple.json")

        return result

    def extract_pagination_info(self, soup):
        """
        Extract pagination information from JPX (exactly like working code)
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

    def _should_continue_pagination(self, has_next: bool, companies_count: int) -> bool:
        """Check if we should continue to next page"""
        if not has_next:
            print("🏁 Reached last page")
            return False

        if self.max_pages and self.current_page >= self.max_pages:
            print(f"🛑 Reached limit: {self.max_pages} pages")
            return False

        if companies_count == 0:
            print("🛑 No companies on page")
            return False

        if self.total_pages and self.current_page >= self.total_pages:
            print("🏁 Reached last page by total count")
            return False

        return True

    async def _enqueue_next_page(self, context: BeautifulSoupCrawlingContext, soup) -> None:
        """Enqueue next page request"""
        self.current_page += 1
        print(f"⏱️ Moving to page {self.current_page}")

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Look for pagination form
        form_030 = soup.find('form', attrs={'name': 'JJK020030Form'})

        if form_030:
            print(f"Found JJK020030Form for page {self.current_page}")

            # Collect hidden fields
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
                'pageNo': str(self.current_page),
                'currentPage': str(self.current_page)
            })

            url_results = "https://www2.jpx.co.jp/tseHpFront/JJK020030Action.do"

            request = Request.from_url(
                url=url_results,
                method="POST",
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': url_results,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                payload=self._encode_form_data(pagination_form_data).encode('utf-8'),
                label="PAGINATION_PAGE",
                unique_key=f"pagination_{self.current_page}_{datetime.now().timestamp()}"
            )

            await context.add_requests([request])
        else:
            print(f"JJK020030Form not found, using fallback")
            # Fallback to original form
            url = f"https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid={self.session_id}"

            request = Request.from_url(
                url=url,
                method="POST",
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': url,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                payload=self._encode_form_data(self.search_params).encode('utf-8'),
                label="RESULTS_PAGE",
                unique_key=f"fallback_{self.current_page}_{datetime.now().timestamp()}"
            )

            await context.add_requests([request])

    def _parse_companies_from_soup(self, soup) -> list:
        """Parse companies from BeautifulSoup (same logic as working code)"""
        enhanced_data = []

        # Look for hidden fields with company data
        hidden_inputs = soup.find_all('input', {'type': 'hidden'})
        company_records = {}

        for hidden in hidden_inputs:
            name = hidden.get('name', '')
            value = hidden.get('value', '')

            # Parse fields ccJjCrpSelKekkLst_st[N].field
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

        # Parse visible data from tables
        tables = soup.find_all('table')
        company_data = []

        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
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

        # Combine visible and hidden data
        for company in company_data:
            code = company['code']
            enhanced_company = company.copy()

            # Add hidden fields if found
            for record in company_records.values():
                if record.get('eqMgrCd') == code:
                    enhanced_company['hidden_fields'] = record
                    break

            enhanced_data.append(enhanced_company)

        # If no visible data, use hidden fields only
        if not enhanced_data and company_records:
            for index, record in sorted(company_records.items()):
                if 'eqMgrCd' in record:
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

    def _extract_pagination_info(self, soup) -> dict:
        """Extract pagination info from BeautifulSoup"""
        pagination_info = {
            'current_page': 1,
            'total_pages': 1,
            'total_items': 0,
            'items_per_page': 10,
            'has_next_page': False,
            'has_prev_page': False
        }

        paging_menu = soup.find('div', class_='pagingmenu')

        if paging_menu:
            # Extract "Display of 1-10 items/1622"
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

            # Current page
            current_element = paging_menu.find('b', class_='current')
            if current_element:
                try:
                    pagination_info['current_page'] = int(current_element.get_text().strip())
                except ValueError:
                    pass

            # Next button
            next_div = paging_menu.find('div', class_='next_e')
            if next_div and next_div.find('a'):
                pagination_info['has_next_page'] = True

            # Previous page
            if pagination_info['current_page'] > 1:
                pagination_info['has_prev_page'] = True

        return pagination_info

    def _update_statistics(self, companies: list) -> None:
        """Update statistics (wrapper for compatibility)"""
        return self.update_statistics(companies, self.all_statistics)

    def _extract_pagination_info(self, soup) -> dict:
        """Extract pagination info (wrapper for compatibility)"""
        return self.extract_pagination_info(soup)

    def _encode_form_data(self, data: dict) -> str:
        """Encode form data"""
        from urllib.parse import urlencode
        return urlencode(data)

    async def _save_page_html(self, html: str, page_num: int) -> None:
        """Save page HTML"""
        filename = f'jpx_page_{page_num}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"💾 Saved: {filename}")

async def _save_final_results(self) -> None:
    """Save final results"""
    print(f"\n🎉 COMPLETED!")
    print(f"📊 Pages processed: {self.current_page}")
    print(f"🏢 Total companies: {len(self.all_companies)}")

    # Show statistics
    self.show_final_statistics(self.all_statistics)

    # Save results using the working code function
    result = self.save_results(self.all_companies, self.all_statistics, self.current_page, self.total_items)

    # Also save in Crawlee format
    crawlee_result = {
        'success': True,
        'method': 'beautifulsoup_crawler',
        'pages_processed': self.current_page,
        'total_companies': len(self.all_companies),
        'expected_total_items': self.total_items,
        'scraped_at': datetime.now().isoformat(),
        'statistics': {
            'segments': self.all_statistics['segments'],
            'industries': dict(sorted(self.all_statistics['industries'].items(), key=lambda x: x[1], reverse=True))
        },
        'companies': self.all_companies
    }

    with open('jpx_beautifulsoup_results.json', 'w', encoding='utf-8') as f:
        json.dump(crawlee_result, f, ensure_ascii=False, indent=2)
    print(f"💾 Crawlee format: jpx_beautifulsoup_results.json")

def _show_final_statistics(self) -> None:
    """Show final statistics"""
    if self.all_statistics['segments']:
        print(f"\n📈 Statistics by segments:")
        for segment, count in sorted(self.all_statistics['segments'].items()):
            print(f"  {segment}: {count}")

    if self.all_statistics['industries']:
        print(f"\n🏭 Top 10 industries:")
        top_industries = sorted(self.all_statistics['industries'].items(), key=lambda x: x[1], reverse=True)[:10]
        for industry, count in top_industries:
            print(f"  {industry}: {count}")


async def scrape_single_page(self) -> dict:
    """Scrape single page"""
    print("📄 MODE: Single page (BeautifulSoup)")
    self.max_pages = 1

    await self.setup_handlers()

    initial_url = f"https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid={self.session_id}"

    import uuid
    unique_id = str(uuid.uuid4())

    initial_request = Request.from_url(
        url=initial_url,
        method='POST',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Initial-Request': unique_id
        },
        payload=self._encode_form_data(self.search_params).encode('utf-8'),
        label='SEARCH_PAGE',
        unique_key=f"search_page_first_request_{unique_id}"
    )

    print(f"🚀 Starting crawler with unique_key: search_page_first_request_{unique_id}")
    await self.crawler.run([initial_request])

    return {'success': True, 'companies_count': len(self.all_companies)}


async def scrape_all_pages(self) -> dict:
    """Scrape all pages"""
    print("📚 MODE: All pages (BeautifulSoup)")

    await self.setup_handlers()

    initial_url = f"https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do;jsessionid={self.session_id}"

    import uuid
    unique_id = str(uuid.uuid4())

    initial_request = Request.from_url(
        url=initial_url,
        method='POST',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Initial-Request': unique_id
        },
        payload=self._encode_form_data(self.search_params).encode('utf-8'),
        label='SEARCH_PAGE',
        unique_key=f"search_page_all_pages_{unique_id}"
    )

    await self.crawler.run([initial_request])

    return {'success': True, 'total_companies': len(self.all_companies)}


async def main():
    """Main function"""
    print("🚀 JPX SCRAPER WITH BEAUTIFULSOUP CRAWLER")
    print("=" * 60)

    mode = input(
        "\nSelect mode:\n1. Single page (fast)\n2. All pages\n3. Limited number of pages\nYour choice (1-3): ").strip()

    if mode == "1":
        scraper = JPXScraperSimple(max_pages=1)
        result = await scraper.scrape_single_page()

        if result.get('success'):
            print(f"\n🎉 SUCCESS! Found companies: {result.get('companies_count', 0)}")
        else:
            print(f"\n❌ ERROR: {result.get('error')}")

    elif mode == "2":
        delay = input("Delay between requests in seconds (default 1): ").strip()
        delay = float(delay) if delay.replace('.', '').isdigit() else 1.0

        print(f"⚠️ This may take a long time!")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm == 'y':
            scraper = JPXScraperSimple(max_pages=None, delay=delay)
            result = await scraper.scrape_all_pages()

            if result.get('success'):
                print(f"\n🎉 SUCCESS! Companies: {result.get('total_companies', 0)}")
            else:
                print(f"\n⚠️ ERROR: {result.get('error')}")

    elif mode == "3":
        max_pages = input("Maximum pages: ").strip()
        max_pages = int(max_pages) if max_pages.isdigit() else 3

        delay = input("Delay in seconds (default 1): ").strip()
        delay = float(delay) if delay.replace('.', '').isdigit() else 1.0

        scraper = JPXScraperSimple(max_pages=max_pages, delay=delay)
        result = await scraper.scrape_all_pages()

        if result.get('success'):
            print(f"\n🎉 SUCCESS! Companies: {result.get('total_companies', 0)}")
        else:
            print(f"\n⚠️ ERROR: {result.get('error')}")

    else:
        print("❌ Invalid choice")

    print(f"\n✅ Done!")


if __name__ == "__main__":
    print("Started JPX BeautifulSoup scraper")
    asyncio.run(main())