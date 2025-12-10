from bs4 import BeautifulSoup
import httpx
from app.models import UiModel, UiPage, UiElement


class HtmlAnalysisAgent:
    async def analyze(self, *, url: str | None, html: str | None) -> UiModel:
        if html is None and url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=30.0)
                    response.raise_for_status()  # Проверка 200 OK
                    html = response.text
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Failed to fetch URL: {e.response.status_code}")
            except httpx.TimeoutException:
                raise ValueError(f"Request to {url} timed out")

        if not html or len(html) < 50:
            raise ValueError("HTML is empty or too short")

        soup = BeautifulSoup(html, 'html.parser')
        elements = []

        for tag in soup.find_all(['input', 'button', 'select', 'textarea', 'a']):
            element_type = self._get_element_type(tag)
            name = self._get_element_name(tag)
            locator = self._generate_locator(tag)
            role = self._determine_role(tag)

            if name and locator:
                elements.append(UiElement(
                    type=element_type,
                    name=name,
                    locator=locator,
                    role=role
                ))

        page = UiPage(
            url=url or "about:blank",
            name=soup.title.string if soup.title else "Page",
            elements=elements,
            main_flows=["Main user flow"]
        )

        return UiModel(pages=[page])

    def _get_element_type(self, tag) -> str:
        """Определяем тип элемента"""
        if tag.name == 'input':
            return tag.get('type', 'text')
        if tag.name == 'a':
            return 'link'
        if tag.name == 'textarea':
            return 'text'
        if tag.name in ['button', 'select']:
            return tag.name
        return 'other'

    def _get_element_name(self, tag) -> str:
        return (
                tag.get('aria-label') or
                tag.get('placeholder') or
                tag.get('value') or
                tag.get_text(strip=True) or
                tag.get('id') or
                tag.get('name') or
                f"{tag.name}_element"
        )

    def _generate_locator(self, tag) -> str:
        """Генерируем XPath локатор"""
        # По ID (самый надёжный)
        if tag.get('id'):
            return f"id='{tag['id']}'"

        # По name
        if tag.get('name'):
            return f"//{tag.name}[@name='{tag['name']}']"

        # По тексту (для button/a)
        text = tag.get_text(strip=True)
        if text and tag.name in ['button', 'a']:
            return f"//{tag.name}[contains(text(), '{text[:30]}')]"

        # По placeholder
        if tag.get('placeholder'):
            return f"//{tag.name}[@placeholder='{tag['placeholder']}']"

        # По классу
        if tag.get('class'):
            class_name = ' '.join(tag['class'])
            return f"//{tag.name}[@class='{class_name}']"

        return f"//{tag.name}"

    def _determine_role(self, tag) -> str:
        """Определяем роль элемента"""
        text = tag.get_text(strip=True).lower() if tag.get_text(strip=True) else ""
        tag_type = tag.get('type', '').lower()

        if tag.name == 'button' or tag_type == 'submit':
            if any(word in text for word in ['submit', 'send', 'create', 'save', 'добавить', 'сохранить']):
                return "primary_action"
            return "action"

        if tag.name == 'input':
            if tag_type in ['text', 'email', 'password', 'number']:
                return "input"
            if tag_type in ['checkbox', 'radio']:
                return "selector"

        if tag.name == 'select':
            return "dropdown"

        if tag.name == 'a':
            return "navigation"

        return "other"
