from bs4 import BeautifulSoup as BS
import logging
import httpx
import sys


class Parser:
    def __init__(self, timeout: int = 10, headers: dict[str, str] = None):
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        # Проверяем доступность lxml
        try:
            import lxml
            self.parser = 'lxml'
        except ImportError:
            self.logger.warning("lxml не установлен, использую html.parser")
            self.parser = 'html.parser'

    def fetch_page(self, url: str) -> BS | None:
        """
        Загрузка страницы и создание объекта BeautifulSoup.

        :param url: URL страницы
        :return: объект BeautifulSoup или None при ошибке
        """
        try:
            response = httpx.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True
            )
            response.raise_for_status()  # Проверяем HTTP статус

            soup = BS(response.text, self.parser)
            self.logger.info(f"Страница загружена: {url}")
            return soup

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP ошибка {e.response.status_code} для {url}: {e}")
        except httpx.TimeoutException as e:
            self.logger.error(f"Таймаут при загрузке {url}: {e}")
        except httpx.RequestError as e:
            self.logger.error(f"Ошибка запроса к {url}: {e}")
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка при загрузке {url}: {e}")

        return None

    def extract_by_selector(self, soup: BS, selector: str, attr: str = None) -> list:
        """
        Извлечение данных по CSS‑селектору.

        :param soup: объект BeautifulSoup
        :param selector: CSS‑селектор (например, 'div.content', 'a[href]')
        :param attr: имя атрибута для извлечения (если нужно, например 'href', 'src')
        :return: список значений (текстов или атрибутов)
        """
        results = []

        try:
            if not soup:
                self.logger.warning("Передан пустой soup объект")
                return results

            elements = soup.select(selector)
            self.logger.info(f"Найдено элементов по селектору '{selector}': {len(elements)}")

            for elem in elements:
                if attr:
                    value = elem.get(attr, '').strip()
                    if value:  # Добавляем только непустые значения
                        results.append(value)
                else:
                    text = elem.get_text(strip=True)
                    if text:  # Добавляем только непустой текст
                        results.append(text)

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге селектора '{selector}': {e}")

        return results

    def extract_multiple(self, soup: BS, selectors: dict[str, str | dict[str, str]]) -> dict:
        """
        Извлечение данных по нескольким селекторам.

        :param soup: объект BeautifulSoup
        :param selectors: словарь селекторов, где ключ — имя поля,
                         значение — селектор или словарь {'selector': ..., 'attr': ...}
        :return: словарь с результатами
        """
        results = {}

        if not soup:
            self.logger.error("Нельзя парсить None soup")
            return results

        try:
            for field_name, selector_info in selectors.items():
                if isinstance(selector_info, str):
                    results[field_name] = self.extract_by_selector(soup, selector_info)
                elif isinstance(selector_info, dict):
                    selector = selector_info.get('selector')
                    attr = selector_info.get('attr')
                    if selector:
                        results[field_name] = self.extract_by_selector(soup, selector, attr)
                    else:
                        self.logger.warning(f"Нет селектора для поля '{field_name}'")
                else:
                    self.logger.warning(f"Некорректный формат селектора для поля '{field_name}'")

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге селекторов: {e}")

        return results

    def main_parse(self, url: str, selectors: dict[str, str | dict[str, str]]) -> dict:
        """
        Основной метод: загрузка страницы и парсинг по селекторам.

        :param url: URL страницы
        :param selectors: словарь селекторов (см. extract_multiple)
        :return: словарь с результатами или пустой словарь при ошибке
        """
        soup = self.fetch_page(url)

        if not soup:
            self.logger.error(f"Не удалось загрузить страницу: {url}")
            return {}

        return self.extract_multiple(soup, selectors)


# Тестирование
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = Parser(timeout=10)
    selectors = {
            'titles': 'h1, h2',  # все заголовки h1 и h2
            'links': {
                'selector': 'a[href]',
                'attr': 'href'  # извлекаем только атрибут href
            },
            'images': {
                'selector': 'img[src]',
                'attr': 'src'
            },
            'paragraphs': 'p'  # текст всех параграфов
        }

    result = parser.main_parse("https://havana57.ru/category/elektronnye-sigarety-i-aksessuary/", selectors)

    if result:
        print("\n" + "=" * 50)
        print("РЕЗУЛЬТАТЫ ПАРСИНГА:")
        print("=" * 50)

        for key, values in result.items():
            print(f"\n{key.upper()} ({len(values)}):")
            for i, value in enumerate(values[:5], 1):  # Показываем первые 5
                print(f"  {i}. {value[:100]}{'...' if len(value) > 100 else ''}")
            if len(values) > 5:
                print(f"  ... и еще {len(values) - 5} элементов")
    else:
        print("❌ Не удалось получить результаты парсинга")