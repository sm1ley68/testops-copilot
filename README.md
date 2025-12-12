# TestOps Copilot Backend

**AI-powered test automation backend для QA инженеров**

Backend сервис для автоматической генерации тест-кейсов и автотестов с использованием Cloud.ru Evolution Foundation Model. Создаёт pytest/Playwright код в формате Allure TestOps as Code.

---

## 🎯 Возможности

### 1. UI Test Generation
- Парсинг HTML/URL с BeautifulSoup
- Генерация ручных тест-кейсов (Allure TestOps as Code)
- E2E автотесты с Playwright и pytest
- Минимум 15 тест-кейсов на основе UI-модели

### 2. API Test Generation
- Парсинг OpenAPI/Swagger спецификаций
- Автоматическая генерация pytest тестов для каждого эндпоинта
- CRUD операции, авторизация, обработка ошибок
- httpx клиент с @allure декораторами

### 3. Coverage Analysis
- Анализ дубликатов тестов
- Определение пробелов в покрытии
- Рекомендации по оптимизации тест-сьюта

### 4. Chat Agent
- QA-ассистент для вопросов о тестировании
- Best practices и примеры кода
- Интеграция с LLM для развёрнутых ответов

---

## 🏗️ Архитектура

### Tech Stack
- **Python 3.10+**
- **FastAPI** — REST API framework
- **httpx** — HTTP клиент для API запросов
- **BeautifulSoup4** — HTML/XML парсинг
- **Cloud.ru Evolution** — LLM (openai/gpt-oss-120b)
- **Docker** — контейнеризация

### Multi-Agent System

```
CoordinatorAgent (оркестратор)
    ├── HtmlAnalysisAgent (парсинг UI)
    ├── ApiParsingAgent (парсинг Swagger)
    ├── AutomationAgent (генерация pytest)
    ├── CoverageAgent (анализ покрытия)
    └── ChatAgent (QA-ассистент)
           ↓
    Cloud.ru Evolution LLM
           ↓
    Output: Chat / Manual Tests / Pytest Code
```

---

## Быстрый старт

### Требования
- **Docker** 20+
- **Docker Compose** v2+
- **Git**

### Установка

```bash
# 1. Клонируем репозиторий
git clone https://github.com/yourusername/testops-copilot-backend.git
cd testops-copilot-backend

# 2. Создаём .env файл
cp .env.example .env

# 3. Настраиваем переменные окружения
nano .env
```

### Переменные окружения (.env)

```env
CLOUDRU_API_URL=https://foundation-models.api.cloud.ru/v1  
CLOUDRU_API_TOKEN=ZDgwZTUxYTktNDk4ZS00YzdkLTliMWUtZmNjYWYzMWU5MjFj.66922e205378b47afb254c17da717d51  
  
GITLAB_URL=https://gitlab.com  
GITLAB_TOKEN=gitlab_token_here  
  
APP_ENV=dev  
LOG_LEVEL=INFO
```

### Запуск через Docker

```bash
# Запуск backend
docker compose up -d

# Проверка логов
docker compose logs -f backend

# Остановка
docker compose down
```

### Локальный запуск (для разработки)

```bash
# Создаём виртуальное окружение
python3.10 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📡 API Endpoints

### Base URL
```
http://localhost:8000
```

### 1. UI Test Generation

**POST** `/generation/allure-code/ui`

Генерирует ручные тест-кейсы из HTML/URL

**Request:**
```json
{
  "url": "https://example.com/login",
  "html_content": "<html>...</html>",
  "requirements_text": "Проверить форму логина"
}
```

**Response:**
```json
{
  "test_suite": {
    "name": "Login Form Tests",
    "cases": [...]
  },
  "allure_code": "import allure\n\n@allure.title(...)..."
}
```

---

### 2. API Test Generation

**POST** `/generation/automation/api`

Генерирует pytest тесты из Swagger/OpenAPI

**Request:**
```json
{
  "swagger_url": "https://petstore.swagger.io/v2/swagger.json",
  "swagger_json": "{...}"
}
```

**Response:**
```json
{
  "pytest_code": "import pytest\nimport httpx\n\n@pytest.fixture...",
  "test_count": 20
}
```

---

### 3. E2E Test Generation

**POST** `/generation/automation/e2e`

Генерирует Playwright E2E тесты

**Request:**
```json
{
  "url": "https://example.com",
  "html_content": "<html>...</html>",
  "requirements_text": "E2E тесты для регистрации"
}
```

**Response:**
```json
{
  "pytest_code": "import pytest\nfrom playwright.async_api import async_playwright...",
  "test_count": 15
}
```

---

### 4. Coverage Analysis

**POST** `/optimization/analyze`

Анализирует покрытие тестов

**Request:**
```json
{
  "test_files": [
    {"name": "test_api.py", "content": "..."},
    {"name": "test_ui.py", "content": "..."}
  ]
}
```

**Response:**
```json
{
  "duplicates": [...],
  "coverage_gaps": [...],
  "recommendations": [...]
}
```

---

### 5. Chat Agent

**POST** `/chat`

QA-ассистент для вопросов о тестировании

**Request:**
```json
{
  "message": "Как писать pytest фикстуры?",
  "history": []
}
```

**Response:**
```json
{
  "reply": "Pytest фикстуры создаются с помощью декоратора @pytest.fixture...",
  "code_examples": [...]
}
```

---

## 📂 Структура проекта

```
testops-copilot-backend/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── allure_code_generator.py      # Генератор Allure тестов
│   │   ├── automation_agent.py           # Генератор Playwright/pytest
│   │   ├── coordinator.py                # Главный оркестратор
│   │   ├── coverage_agent.py             # Анализ покрытия
│   │   ├── html_agent.py                 # Парсинг HTML
│   │   ├── requirements_agent.py         # Обработка требований
│   │   └── validation_agent.py           # Валидация кода
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py                       # Chat endpoint
│   │   ├── generation.py                 # UI/API/E2E генерация
│   │   ├── optimization.py               # Coverage анализ
│   │   ├── requirements.py               # Обработка требований
│   │   └── validation.py                 # Валидация
│   ├── __init__.py
│   ├── config.py                         # Конфигурация
│   ├── llm_client.py                     # Cloud.ru Evolution клиент
│   ├── main.py                           # FastAPI приложение
│   └── models.py                         # Pydantic модели
├── Dockerfile                            # Docker образ
├── docker-compose.yml                    # Docker Compose конфигурация
├── requirements.txt                      # Python зависимости                
├── .gitignore                            # Git игнор файлы
└── README.md                             # Этот файл

```

---

## 🧪 Тестирование

```bash
# Запуск unit-тестов
pytest tests/ -v

# С покрытием
pytest tests/ --cov=app --cov-report=html

# Проверка типов
mypy app/

# Линтер
flake8 app/
```

---

## 🔧 Разработка

### Форматирование кода

```bash
# Black formatter
black app/

# isort для импортов
isort app/
```

### Добавление нового агента

1. Создайте файл в `app/agents/your_agent.py`
2. Наследуйтесь от базового класса `Agent`
3. Реализуйте методы `process()` и `generate()`
4. Зарегистрируйте в `CoordinatorAgent`

**Пример:**

```python
# app/agents/your_agent.py

from app.agents.base import Agent
from app.llm_client import get_llm_client

class YourAgent(Agent):
    async def process(self, input_data: dict) -> dict:
        # Ваша логика обработки
        result = await self.generate_with_llm(input_data)
        return result

    async def generate_with_llm(self, data: dict) -> dict:
        with get_llm_client() as client:
            response = client.post(
                "/chat/completions",
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": "You are expert..."},
                        {"role": "user", "content": str(data)}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 8000
                }
            )
        return response.json()
```

---

