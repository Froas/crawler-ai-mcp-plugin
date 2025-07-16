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
            print(f"❌ Ошибка сессии: {e}")
            return False

    def switch_to_quick_search(self):
        """Переключается на Quick Search"""

        if not self.get_session():
            return False

        # Параметры для переключения на Quick Search
        switch_data = [
            ('Switch', 'Switch'),  # КЛЮЧЕВОЙ параметр для переключения
        ]

        target_url = f"{self.submit_url};jsessionid={self.jsessionid}"

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www2.jpx.co.jp',
            'Referer': f"{self.form_url};jsessionid={self.jsessionid}",
        }

        print(f"🔄 Переключаемся на Quick Search...")
        print(f"🔄 URL: {target_url}")

        try:
            response = self.session.post(target_url, data=switch_data, headers=headers)

            print(f"📥 Статус: {response.status_code}")
            print(f"📥 Размер: {len(response.text)} символов")

            # Проверяем, переключились ли мы на Quick Search
            if "Quick search" in response.text and "<strong>" in response.text:
                # Ищем, что сейчас выделено жирным
                if "Quick search</strong>" in response.text:
                    print("✅ Переключились на Quick Search!")
                    return True
                else:
                    print("❌ Все еще на Detailed Search")
                    return False
            else:
                print("⚠️ Не удалось определить текущий режим")
                return False

        except Exception as e:
            print(f"❌ Ошибка переключения: {e}")
            return False

    def test_quick_search_after_switch(self):
        """Тестирует Quick Search после переключения"""

        if not self.switch_to_quick_search():
            print("❌ Не удалось переключиться на Quick Search")
            return ""

        # Теперь используем параметры для Quick Search
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

        print(f"\n🚀 Тестируем Quick Search после переключения...")

        try:
            response = self.session.post(target_url, data=form_data, headers=headers)

            print(f"📥 Статус: {response.status_code}")
            print(f"📥 Размер: {len(response.text)} символов")

            content = response.text

            # Проверяем ошибки
            has_errors = any(error in content for error in [
                "should 1 or more checks", "is not a right date", "Error"
            ])

            # Проверяем успех
            has_success = any(indicator in content for indicator in [
                "Display of", "13010", "KYOKUYO"
            ])

            print(f"❌ Есть ошибки: {has_errors}")
            print(f"✅ Есть успех: {has_success}")

            if has_errors:
                # Показываем ошибку
                import re
                error_match = re.search(r'<span id="cgTabError"[^>]*>(.*?)</span>', content, re.DOTALL)
                if error_match:
                    error_text = error_match.group(1).strip()
                    print(f"❌ Ошибка: {error_text}")

            if has_success and not has_errors:
                print("🎉 QUICK SEARCH РАБОТАЕТ!")
                with open('switch_success.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return content
            else:
                print("❌ Quick Search все еще не работает")
                with open('switch_error.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return ""

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return ""


# Альтернативный подход - прямой Quick Search URL
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
        """Тестирует с параметром Show вместо ListShow"""

        if not self.get_session():
            return ""

        # Пробуем Show вместо ListShow (для Quick Search)
        form_data = [
            ('Show', 'Show'),  # Вместо ListShow
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

        print(f"🧪 Тестируем с параметром Show (Quick Search)...")
        print(f"🧪 Параметров: {len(form_data)}")

        try:
            response = self.session.post(target_url, data=form_data, headers=headers)

            print(f"📥 Статус: {response.status_code}")
            print(f"📥 Размер: {len(response.text)} символов")

            content = response.text

            # Проверки
            has_errors = "should 1 or more checks" in content
            has_companies = any(ind in content for ind in ["Display of", "13010", "KYOKUYO"])

            print(f"❌ Есть ошибки: {has_errors}")
            print(f"✅ Есть компании: {has_companies}")

            if has_companies and not has_errors:
                print("🎉 SHOW ПАРАМЕТР РАБОТАЕТ!")
                with open('show_success.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return content
            else:
                with open('show_error.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                return ""

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return ""


def main():
    print("🔄 ТЕСТИРОВАНИЕ ПЕРЕКЛЮЧЕНИЯ НА QUICK SEARCH")
    print("=" * 70)

    # Тест 1: Переключение через Switch
    print("\n1️⃣ Переключение через Switch параметр...")
    switcher = SwitchToQuickSearch()
    switch_result = switcher.test_quick_search_after_switch()
    switch_success = bool(switch_result)

    # Тест 2: Прямой Quick Search с Show
    print("\n2️⃣ Прямой Quick Search с Show параметром...")
    direct = DirectQuickSearch()
    show_result = direct.test_with_show_parameter()
    show_success = bool(show_result)

    print("\n" + "=" * 70)
    print("🏁 РЕЗУЛЬТАТЫ ПЕРЕКЛЮЧЕНИЯ")
    print("=" * 70)
    print(f"🔄 Switch method:  {'🎉 РАБОТАЕТ!' if switch_success else '❌ НЕ РАБОТАЕТ'}")
    print(f"🧪 Show method:    {'🎉 РАБОТАЕТ!' if show_success else '❌ НЕ РАБОТАЕТ'}")

    if switch_success or show_success:
        print("\n🎊 ОДИН ИЗ МЕТОДОВ РАБОТАЕТ!")
        print("📋 Теперь можно использовать рабочий метод для получения данных")
    else:
        print("\n😕 Нужно попробовать другой подход...")
        print("💡 Возможно, Quick Search имеет другой URL или механизм")


if __name__ == "__main__":
    main()