import requests
from urllib.parse import urlencode


class SwitchToQuickSearch:
    def __init__(self):
        self.form_url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do"
        self.submit_url = "https://www2.jpx.co.jp/tseHpFront/JJK020020Action.do"
        self.session = requests.Session()
        self.jsessionid = None

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })

    def get_session(self):
        try:
            response = self.session.get(self.form_url)
            for cookie in self.session.cookies:
                if cookie.name == 'JSESSIONID':
                    self.jsessionid = cookie.value
                    break
            print(f"✅ JSESSIONID: {self.jsessionid}")
            return True
        except Exception as e:
            print(f"❌ Session error: {e}")
            return False

    def switch_to_quick_search(self):
        """Switches to Quick Search mode"""

        if not self.get_session():
            return False

        # Parameters for switching to Quick Search
        switch_data = [
            ('Switch', 'Switch'),  # KEY parameter for switching
        ]

        target_url = f"{self.submit_url};jsessionid={self.jsessionid}"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www2.jpx.co.jp',
            'Referer': f"{self.form_url};jsessionid={self.jsessionid}",
        }

        print(f"🔄 Switching to Quick Search...")
        print(f"🔄 URL: {target_url}")

        try:
            response = self.session.post(target_url, data=switch_data, headers=headers)

            print(f"📥 Status: {response.status_code}")
            print(f"📥 Size: {len(response.text)} characters")

            # Check if we switched to Quick Search
            if "Quick search" in response.text and "<strong>" in response.text:
                # Look for what's currently highlighted in bold
                if "Quick search</strong>" in response.text:
                    print("✅ Switched to Quick Search!")
                    return True
                else:
                    print("❌ Still on Detailed Search")
                    return False
            else:
                print("⚠️ Could not determine current mode")
                return False

        except Exception as e:
            print(f"❌ Switch error: {e}")
            return False

    def test_quick_search_after_switch(self):
        """Tests Quick Search after switching"""

        if not self.switch_to_quick_search():
            print("❌ Failed to switch to Quick Search")
            return ""

        # Now use parameters for Quick Search
        form_data = [
            ('dspSsuPd', '100'),
            ('szkbuChkbxMapOut',
             '011>Prime<012>Standard<013>Growth<008>TOKYO PRO Market<bj1>－<be1>－<111>Prime Foreign Stocks<112>Standard Foreign Stocks<113>Growth Foreign Stocks<bj2>－<be2>－<ETF>ETFs<ETN>ETNs<RET>Real Estate Investment Trusts (REITs)<IFD>Infrastructure Funds<999>Others<'),
            ('ListShow', 'ListShow'),
            ('sniMtGmnId', ''),
            ('dspSsuPdMapOut', '10>10<50>50<100>100<200>200<'),
            ('mgrMiTxtBx', ''),
            ('eqMgrCd', ''),
            ('szkbuChkbx', '011'),
        ]

        target_url = f"{self.submit_url};jsessionid={self.jsessionid}"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www2.jpx.co.jp',
            'Referer': f"{self.form_url};jsessionid={self.jsessionid}",
        }

        print(f"\n🚀 Testing Quick Search after switching...")

        try:
            response = self.session.post(target_url, data=form_data, headers=headers)

            print(f"📥 Status: {response.status_code}")
            print(f"📥 Size: {len(response.text)} characters")

            content = response.text

            # Check for errors
            has_errors = any(error in content for error in [
                "should 1 or more checks", "is not a right date", "Error"
            ])

            # Check for success
            has_success = any(indicator in content for indicator in [
                "Display of", "13010", "KYOKUYO"
            ])

            print(f"❌ Has errors: {has_errors}")
            print(f"✅ Has success: {has_success}")

            if has_errors:
                # Show error
                import re
                error_match = re.search(r'<span id="cgTabError"[^>]*>(.*?)</span>', content, re.DOTALL)
                if error_match:
                    error_text = error_match.group(1).strip()
                    print(f"❌ Error: {error_text}")

            if has_success and not has_errors:
                print("🎉 QUICK SEARCH WORKS!")
                with open('switch_success.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return content
            else:
                print("❌ Quick Search still not working")
                with open('switch_error.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return ""

        except Exception as e:
            print(f"❌ Error: {e}")
            return ""


# Alternative approach - direct Quick Search URL
class DirectQuickSearch:
    def __init__(self):
        self.form_url = "https://www2.jpx.co.jp/tseHpFront/JJK020010Action.do"
        self.submit_url = "https://www2.jpx.co.jp/tseHpFront/JJK020020Action.do"
        self.session = requests.Session()
        self.jsessionid = None

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def get_session(self):
        try:
            response = self.session.get(self.form_url)
            for cookie in self.session.cookies:
                if cookie.name == 'JSESSIONID':
                    self.jsessionid = cookie.value
                    break
            return True
        except:
            return False

    def test_with_show_parameter(self):
        """Tests with Show parameter instead of ListShow"""

        if not self.get_session():
            return ""

        # Try Show instead of ListShow (for Quick Search)
        form_data = [
            ('Show', 'Show'),  # Instead of ListShow
            ('dspSsuPd', '50'),
            ('szkbuChkbx', '011'),  # Prime
            ('mgrMiTxtBx', ''),
            ('eqMgrCd', ''),
        ]

        target_url = f"{self.submit_url};jsessionid={self.jsessionid}"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www2.jpx.co.jp',
            'Referer': f"{self.form_url};jsessionid={self.jsessionid}",
        }

        print(f"🧪 Testing with Show parameter (Quick Search)...")
        print(f"🧪 Parameters: {len(form_data)}")

        try:
            response = self.session.post(target_url, data=form_data, headers=headers)

            print(f"📥 Status: {response.status_code}")
            print(f"📥 Size: {len(response.text)} characters")

            content = response.text

            # Checks
            has_errors = "should 1 or more checks" in content
            has_companies = any(ind in content for ind in ["Display of", "13010", "KYOKUYO"])

            print(f"❌ Has errors: {has_errors}")
            print(f"✅ Has companies: {has_companies}")

            if has_companies and not has_errors:
                print("🎉 SHOW PARAMETER WORKS!")
                with open('show_success.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return content
            else:
                with open('show_error.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return ""

        except Exception as e:
            print(f"❌ Error: {e}")
            return ""


def main():
    print("🔄 TESTING QUICK SEARCH SWITCHING")
    print("=" * 70)

    # Test 1: Switching via Switch parameter
    print("\n1️⃣ Switching via Switch parameter...")
    switcher = SwitchToQuickSearch()
    switch_result = switcher.test_quick_search_after_switch()
    switch_success = bool(switch_result)

    # Test 2: Direct Quick Search with Show
    print("\n2️⃣ Direct Quick Search with Show parameter...")
    direct = DirectQuickSearch()
    show_result = direct.test_with_show_parameter()
    show_success = bool(show_result)

    print("\n" + "=" * 70)
    print("🏁 SWITCHING RESULTS")
    print("=" * 70)
    print(f"🔄 Switch method:  {'🎉 WORKS!' if switch_success else '❌ NOT WORKING'}")
    print(f"🧪 Show method:    {'🎉 WORKS!' if show_success else '❌ NOT WORKING'}")

    if switch_success or show_success:
        print("\n🎊 ONE OF THE METHODS WORKS!")
        print("📋 Now you can use the working method to get data")
    else:
        print("\n😕 Need to try a different approach...")
        print("💡 Maybe Quick Search has a different URL or mechanism")


if __name__ == "__main__":
    main()