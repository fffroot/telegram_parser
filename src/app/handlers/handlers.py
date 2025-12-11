import logging
import json
from typing import Dict, Any

from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.app.keyboards.keyboard import main_menu_keyboard
from src.core.scraper.bs4_scraper import Parser

router = Router()
logger = logging.getLogger(__name__)


class ParseSteps(StatesGroup):
    WAITING_FOR_URL = State()
    WAITING_FOR_SELECTOR_NAME = State()
    WAITING_FOR_SELECTOR_VALUE = State()
    WAITING_FOR_SELECTOR_ATTR = State()
    CONFIRM_SELECTORS = State()


# Хранилище селекторов для каждого пользователя
user_selectors: Dict[int, Dict[str, Any]] = {}


@router.message(Command('start'))
async def start_cmd(message: Message):
    await message.answer(
        'Привет! Я — бот-парсер сайтов.\n'
        'Я помогу тебе быстро извлечь нужную информацию с любой веб-страницы.\n'
        'Чтобы начать парсинг, воспользуйся командой /parse или выбери ее в меню команд ниже.\n'
        'Если нужна помощь или пример использования, набери /help.\n',
        reply_markup=main_menu_keyboard()
    )


@router.message(Command('help'))
async def get_help(message: Message):
    await message.answer(
        '📚 Инструкция по использованию:\n\n'
        '1. **Начните с команды /parse**\n'
        '2. **Отправьте URL сайта** (например: https://example.com)\n'
        '3. **Добавьте селекторы** - я буду спрашивать:\n'
        '   • Название поля (например: "titles", "prices")\n'
        '   • CSS-селектор (например: "h1", ".price", "#main")\n'
        '   • Атрибут (если нужен, например: "href", "src")\n\n'
        '🔹 **Пример простого селектора:**\n'
        '   Название: "headers"\n'
        '   Селектор: "h2"\n\n'
        '🔹 **Пример селектора с атрибутом:**\n'
        '   Название: "links"\n'
        '   Селектор: "a"\n'
        '   Атрибут: "href"\n\n'
        'Когда закончите - отправьте "готово"'
    )


@router.message(Command('parse'))
async def get_parse(message: Message, state: FSMContext):
    """Начало процесса парсинга"""
    user_id = message.from_user.id

    # Сбрасываем предыдущие селекторы пользователя
    if user_id in user_selectors:
        user_selectors[user_id] = {}

    await message.answer(
        "🔧 Давайте настроим парсинг!\n\n"
        "Шаг 1: Введите URL сайта (например: https://example.com):"
    )

    await state.set_state(ParseSteps.WAITING_FOR_URL)


@router.message(ParseSteps.WAITING_FOR_URL, F.text)
async def process_url(message: Message, state: FSMContext):
    """Обработка URL"""
    user_url = message.text.strip()

    # Простая валидация URL
    if not user_url.startswith(('http://', 'https://')):
        user_url = 'https://' + user_url

    await state.update_data(url=user_url)

    # Инициализируем селекторы для пользователя
    user_id = message.from_user.id
    user_selectors[user_id] = {}

    await message.answer(
        f"✅ URL сохранен: {user_url}\n\n"
        "Шаг 2: Введите название для первого поля данных\n"
        "(например: 'headers', 'prices', 'links'):"
    )
    await state.set_state(ParseSteps.WAITING_FOR_SELECTOR_NAME)


@router.message(ParseSteps.WAITING_FOR_SELECTOR_NAME, F.text)
async def process_selector_name(message: Message, state: FSMContext):
    """Обработка названия селектора"""
    selector_name = message.text.strip()

    # Сохраняем текущее название селектора
    await state.update_data(current_selector=selector_name)

    await message.answer(
        f"✅ Название поля: '{selector_name}'\n\n"
        "Шаг 3: Введите CSS-селектор для этого поля\n"
        "Примеры:\n"
        "• h1, h2 - заголовки\n"
        "• .price - элементы с классом price\n"
        "• a[href] - ссылки\n"
        "• #main-content - элемент с id\n\n"
        "Или отправьте 'атрибут' если нужно извлечь атрибут:"
    )
    await state.set_state(ParseSteps.WAITING_FOR_SELECTOR_VALUE)


@router.message(ParseSteps.WAITING_FOR_SELECTOR_VALUE, F.text)
async def process_selector_value(message: Message, state: FSMContext):
    """Обработка значения селектора"""
    selector_value = message.text.strip().lower()
    user_id = message.from_user.id
    data = await state.get_data()
    selector_name = data.get('current_selector')

    if selector_value == 'атрибут':
        # Пользователь хочет добавить атрибут
        await message.answer(
            "Введите CSS-селектор для поиска элементов\n"
            "(например: 'a', 'img', '.image'):"
        )
        await state.update_data(selector_type='attr')
        return

    # Сохраняем простой селектор (без атрибута)
    user_selectors[user_id][selector_name] = selector_value

    await ask_for_next_selector(message, state)


@router.message(ParseSteps.WAITING_FOR_SELECTOR_VALUE)
async def process_selector_for_attr(message: Message, state: FSMContext):
    """Обработка селектора для атрибута"""
    selector_value = message.text.strip()
    await state.update_data(selector_value=selector_value)

    await message.answer(
        f"✅ Селектор: {selector_value}\n\n"
        "Введите название атрибута для извлечения\n"
        "(например: 'href', 'src', 'data-id', 'title'):"
    )
    await state.set_state(ParseSteps.WAITING_FOR_SELECTOR_ATTR)


@router.message(ParseSteps.WAITING_FOR_SELECTOR_ATTR, F.text)
async def process_selector_attr(message: Message, state: FSMContext):
    """Обработка атрибута селектора"""
    attr_name = message.text.strip()
    user_id = message.from_user.id
    data = await state.get_data()
    selector_name = data.get('current_selector')
    selector_value = data.get('selector_value')

    # Сохраняем селектор с атрибутом
    user_selectors[user_id][selector_name] = {
        'selector': selector_value,
        'attr': attr_name
    }

    await ask_for_next_selector(message, state)


async def ask_for_next_selector(message: Message, state: FSMContext):
    """Спросить о следующем селекторе"""
    user_id = message.from_user.id
    current_selectors = user_selectors.get(user_id, {})

    # Форматируем текущие селекторы для отображения
    selectors_text = format_selectors(current_selectors)

    await message.answer(
        f"📋 Текущие селекторы:\n{selectors_text}\n\n"
        "Что дальше?\n"
        "• Введите название следующего поля\n"
        "• Или отправьте 'готово' для запуска парсинга\n"
        "• Или отправьте 'очистить' чтобы начать заново"
    )
    await state.set_state(ParseSteps.CONFIRM_SELECTORS)


def format_selectors(selectors: Dict[str, Any]) -> str:
    """Форматирование селекторов для отображения"""
    if not selectors:
        return "Пока нет селекторов"

    lines = []
    for name, value in selectors.items():
        if isinstance(value, dict):
            lines.append(f"• {name}: {value['selector']} (атрибут: {value.get('attr', 'нет')})")
        else:
            lines.append(f"• {name}: {value}")

    return "\n".join(lines)


@router.message(ParseSteps.CONFIRM_SELECTORS, F.text.lower() == 'готово')
async def finish_selectors(message: Message, state: FSMContext):
    """Завершение настройки селекторов и запуск парсинга"""
    user_id = message.from_user.id
    data = await state.get_data()
    url = data.get('url')
    selectors = user_selectors.get(user_id, {})

    if not selectors:
        await message.answer(
            "❌ Вы не добавили ни одного селектора!\n"
            "Пожалуйста, введите название поля для данных:"
        )
        await state.set_state(ParseSteps.WAITING_FOR_SELECTOR_NAME)
        return

    await state.clear()

    await message.answer(
        f"🚀 Начинаю парсинг...\n\n"
        f"🌐 URL: {url}\n"
        f"🔧 Селекторы:\n{format_selectors(selectors)}\n\n"
        f"⏳ Пожалуйста, подождите..."
    )

    try:
        # Используем ваш синхронный парсер
        parser = Parser(timeout=30)
        results = parser.main_parse(url, selectors)

        if results:
            # Форматируем результаты
            result_text = format_results(results)
            await message.answer(f"✅ Парсинг завершен!\n\n{result_text}")
        else:
            await message.answer(
                "❌ Не удалось получить данные.\n"
                "Возможные причины:\n"
                "• Сайт заблокировал доступ\n"
                "• Неверные селекторы\n"
                "• На странице нет элементов по вашим селекторам"
            )

    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}", exc_info=True)
        await message.answer(
            f"❌ Произошла ошибка при парсинге:\n{str(e)[:300]}"
        )


@router.message(ParseSteps.CONFIRM_SELECTORS, F.text.lower() == 'очистить')
async def clear_selectors(message: Message, state: FSMContext):
    """Очистка селекторов и начало заново"""
    user_id = message.from_user.id
    user_selectors[user_id] = {}

    await message.answer(
        "🗑️ Все селекторы очищены!\n\n"
        "Введите название для первого поля данных:"
    )
    await state.set_state(ParseSteps.WAITING_FOR_SELECTOR_NAME)


@router.message(ParseSteps.CONFIRM_SELECTORS, F.text)
async def add_next_selector(message: Message, state: FSMContext):
    """Добавление следующего селектора"""
    selector_name = message.text.strip()
    await state.update_data(current_selector=selector_name)

    await message.answer(
        f"✅ Название поля: '{selector_name}'\n\n"
        "Введите CSS-селектор для этого поля\n"
        "Или отправьте 'атрибут' если нужно извлечь атрибут:"
    )
    await state.set_state(ParseSteps.WAITING_FOR_SELECTOR_VALUE)


def format_results(results: Dict[str, list]) -> str:
    """Форматирование результатов парсинга для Telegram"""
    if not results:
        return "❌ Нет данных"

    lines = ["📊 РЕЗУЛЬТАТЫ ПАРСИНГА:", ""]

    for field_name, items in results.items():
        if items:
            lines.append(f"🔹 {field_name.upper()} (найдено: {len(items)}):")

            # Показываем первые 5 элементов каждого поля
            for i, item in enumerate(items[:5], 1):
                item_str = str(item)
                # Обрезаем слишком длинные значения
                if len(item_str) > 100:
                    item_str = item_str[:97] + "..."
                lines.append(f"  {i}. {item_str}")

            if len(items) > 5:
                lines.append(f"  ... и еще {len(items) - 5} элементов")

            lines.append("")

    result_text = "\n".join(lines)

    # Telegram ограничение на длину сообщения
    if len(result_text) > 4000:
        result_text = result_text[:3990] + "\n\n... (сообщение обрезано, слишком много данных)"

    return result_text


@router.message(Command('quick_parse'))
async def quick_parse_command(message: Message):
    """Быстрый парсинг с шаблонными селекторами"""
    # Пример быстрого парсинга с готовыми селекторами
    example_selectors = {
        'headers': 'h1, h2, h3',
        'links': {'selector': 'a[href]', 'attr': 'href'},
        'paragraphs': 'p'
    }

    await message.answer(
        "⚡ Быстрый парсинг\n\n"
        "Используйте команду так:\n"
        "/quick_parse https://example.com\n\n"
        "Будут использованы стандартные селекторы:\n"
        f"{format_selectors(example_selectors)}"
    )


@router.message(Command('example'))
async def show_examples(message: Message):
    """Показать примеры селекторов"""
    examples = """
🔸 **Примеры CSS-селекторов:**
• `h1` - все заголовки первого уровня
• `.title` - все элементы с классом title
• `#main` - элемент с id="main"
• `a[href]` - все ссылки
• `div.product img` - изображения внутри div с классом product

🔸 **Примеры селекторов с атрибутами:**
• Для извлечения ссылок:
  Название: links
  Селектор: a
  Атрибут: href

• Для извлечения изображений:
  Название: images
  Селектор: img
  Атрибут: src

• Для извлечения данных:
  Название: prices
  Селектор: .price
  Атрибут: data-value
"""
    await message.answer(examples)