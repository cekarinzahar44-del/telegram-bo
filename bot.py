import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
import aiohttp  # для работы с Google Таблицами (опционально)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- Переменные окружения (обязательно добавить в Bothost) ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
PAYMENT_TOKEN = os.environ.get('PAYMENT_TOKEN')        # для платежей (тестовый от PayMaster)
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))          # твой Telegram ID (узнай у @userinfobot)

if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN! Добавьте его в переменные окружения.")
if not PAYMENT_TOKEN:
    logging.warning("PAYMENT_TOKEN не указан – платежи работать не будут.")
if not ADMIN_ID:
    logging.warning("ADMIN_ID не указан – админ-панель недоступна.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Глобальные данные (в реальном проекте лучше использовать БД) ---
users = set()                    # множество user_id (для статистики и рассылки)
orders = []                      # список заказов (для админки)

# --- Состояния FSM ---
class QuestionState(StatesGroup):
    waiting = State()

class OrderState(StatesGroup):
    name = State()
    phone = State()
    comment = State()

# --- Товары (для каталога и платежей) ---
products = {
    "gaming_pc": {
        "id": "gaming_pc",
        "title": "Игровой ПК \"Gamer Pro\"",
        "description": "Топовый компьютер для игр и работы на максимальных настройках.",
        "price": 1500000,          # в копейках (15000.00 ₽)
        "emoji": "🎮",
        "photo": "https://via.placeholder.com/300"
    },
    "laptop": {
        "id": "laptop",
        "title": "Ноутбук \"WorkMaster X\"",
        "description": "Мощный и легкий ноутбук для любых задач.",
        "price": 800000,           # 8000.00 ₽
        "emoji": "💻",
        "photo": "https://via.placeholder.com/300"
    },
}

# --- Клавиатуры ---
def main_keyboard(user_id=None):
    """Главное меню (для обычных пользователей и админа)"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Задать вопрос"))
    kb.add(KeyboardButton("🛍️ Каталог"), KeyboardButton("📞 Контакты"))
    kb.add(KeyboardButton("✍️ Оставить заявку"))
    # Если пользователь – админ, добавляем спец. кнопки
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("👑 Админ-панель"))
    return kb

def back_keyboard():
    """Кнопка возврата в главное меню"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 В главное меню"))
    return kb

def admin_keyboard():
    """Клавиатура для админ-панели"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📊 Статистика"))
    kb.add(KeyboardButton("📢 Сделать рассылку"))
    kb.add(KeyboardButton("🏠 В главное меню"))
    return kb

# --- Команда /start ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    user_id = message.from_user.id
    users.add(user_id)  # запоминаем пользователя
    await message.answer(
        f"👋 *Привет, {message.from_user.first_name}!*\n\n"
        f"Я — бот магазина электроники. Я помогу:\n"
        f"• Подобрать товар\n"
        f"• Ответить на вопросы\n"
        f"• Принять заявку и даже оплату\n\n"
        f"Выбери действие в меню 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id)
    )

# --- Возврат в главное меню ---
@dp.message_handler(lambda msg: msg.text == "🏠 В главное меню")
async def back_to_main(message: Message):
    await cmd_start(message)

# --- Блок вопросов (имитация ИИ) ---
@dp.message_handler(lambda msg: msg.text == "💬 Задать вопрос")
async def ask_question(message: Message):
    await message.answer(
        "📝 *Задайте ваш вопрос*\n\n"
        "Например: «Какой ноутбук подойдёт для видеомонтажа?»",
        parse_mode="Markdown",
        reply_markup=back_keyboard()
    )
    await QuestionState.waiting.set()

@dp.message_handler(state=QuestionState.waiting)
async def handle_question(message: Message, state: FSMContext):
    question = message.text.lower()
    await message.answer("🤔 *Думаю над ответом...*", parse_mode="Markdown")
    await asyncio.sleep(1.5)

    # Простая логика (можно заменить на вызов реального ИИ)
    if "ноутбук" in question:
        answer = f"✅ *Рекомендую:*\n{products['laptop']['emoji']} {products['laptop']['title']}"
    elif "пк" in question or "компьютер" in question or "игр" in question:
        answer = f"✅ *Рекомендую:*\n{products['gaming_pc']['emoji']} {products['gaming_pc']['title']}"
    else:
        answer = "❓ Я не совсем понял. Посмотрите каталог или оставьте заявку."

    ikb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🛍️ Каталог", callback_data="catalog"),
        InlineKeyboardButton("📞 Связаться", callback_data="contact")
    )
    await message.answer(answer, parse_mode="Markdown", reply_markup=ikb)
    await state.finish()

# --- Блок каталога ---
@dp.message_handler(lambda msg: msg.text == "🛍️ Каталог")
async def show_catalog(message: Message):
    ikb = InlineKeyboardMarkup(row_width=1)
    for prod_id, prod in products.items():
        btn_text = f"{prod['emoji']} {prod['title']} — {prod['price']//100} ₽"
        ikb.add(InlineKeyboardButton(btn_text, callback_data=f"prod_{prod_id}"))
    await message.answer(
        "🛍️ *Наш каталог*\n\nВыберите товар:",
        parse_mode="Markdown",
        reply_markup=ikb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("prod_"))
async def show_product(callback: CallbackQuery):
    prod_id = callback.data.split("_")[1]
    prod = products[prod_id]
    text = (f"*{prod['emoji']} {prod['title']}*\n\n"
            f"{prod['description']}\n\n"
            f"💰 *Цена:* {prod['price']//100} ₽")
    ikb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("💳 Купить", callback_data=f"buy_{prod_id}"),
        InlineKeyboardButton("◀ Назад", callback_data="catalog"),
        InlineKeyboardButton("📞 Связаться", callback_data="contact")
    )
    await callback.message.answer_photo(
        photo=prod['photo'],
        caption=text,
        parse_mode="Markdown",
        reply_markup=ikb
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def back_to_catalog(callback: CallbackQuery):
    await callback.message.delete()
    await show_catalog(callback.message)

# --- Блок платежей ---
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):
    if not PAYMENT_TOKEN:
        await callback.message.answer("❌ Платежи временно недоступны.")
        return
    prod_id = callback.data.split("_")[1]
    prod = products[prod_id]
    prices = [LabeledPrice(label=prod['title'], amount=prod['price'])]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=prod['title'],
        description=prod['description'][:255],
        payload=f"order_{prod_id}_{callback.from_user.id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="test_bot_payment",
        photo_url=prod['photo'],
        photo_height=300,
        photo_width=300
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    orders.append(payload)  # сохраняем заказ
    await message.answer(
        f"✅ *Оплата прошла успешно!*\n"
        f"Номер заказа: `{payload}`\n"
        f"Скоро мы свяжемся с вами для уточнения деталей.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(message.from_user.id)
    )

# --- Блок заявок (сбор контактов) ---
@dp.message_handler(lambda msg: msg.text == "✍️ Оставить заявку")
async def start_order(message: Message):
    await message.answer(
        "✍️ *Оставьте заявку*\n\nВведите ваше *имя*:",
        parse_mode="Markdown",
        reply_markup=back_keyboard()
    )
    await OrderState.name.set()

@dp.message_handler(state=OrderState.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📞 Теперь укажите *номер телефона*:", parse_mode="Markdown")
    await OrderState.phone.set()

@dp.message_handler(state=OrderState.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("💬 Если хотите, добавьте *комментарий* (или отправьте «-», чтобы пропустить):",
                         parse_mode="Markdown")
    await OrderState.comment.set()

@dp.message_handler(state=OrderState.comment)
async def process_comment(message: Message, state: FSMContext):
    comment = message.text if message.text != "-" else ""
    data = await state.get_data()
    name = data['name']
    phone = data['phone']
    user_id = message.from_user.id

    # Отправляем заявку админу
    if ADMIN_ID:
        admin_msg = (f"📬 *Новая заявка*\n"
                     f"👤 Имя: {name}\n"
                     f"📞 Телефон: {phone}\n"
                     f"💬 Комментарий: {comment}\n"
                     f"🆔 ID: {user_id}")
        try:
            await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить заявку админу: {e}")

    # Сохраняем в список заказов
    orders.append({"user": user_id, "name": name, "phone": phone, "comment": comment})

    await message.answer(
        "✅ *Заявка принята!*\nСкоро мы свяжемся с вами.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id)
    )
    await state.finish()

# --- Блок контактов ---
@dp.message_handler(lambda msg: msg.text == "📞 Контакты")
async def contacts(message: Message):
    text = ("📞 *Свяжитесь с нами*\n\n"
            "📱 Телефон: +7 (999) 123-45-67\n"
            "✉️ Email: shop@example.com\n"
            "🌐 Сайт: www.example.com")
    await message.answer(text, parse_mode="Markdown", reply_markup=back_keyboard())

@dp.callback_query_handler(lambda c: c.data == "contact")
async def contact_callback(callback: CallbackQuery):
    text = "📞 +7 (999) 123-45-67\n✉️ shop@example.com"
    await callback.message.answer(text, reply_markup=back_keyboard())
    await callback.answer()

# --- Админ-панель ---
@dp.message_handler(lambda msg: msg.text == "👑 Админ-панель" and msg.from_user.id == ADMIN_ID)
async def admin_panel(message: Message):
    await message.answer(
        "👑 *Админ-панель*\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )

@dp.message_handler(lambda msg: msg.text == "📊 Статистика" and msg.from_user.id == ADMIN_ID)
async def admin_stats(message: Message):
    total_users = len(users)
    total_orders = len(orders)
    await message.answer(
        f"📊 *Статистика*\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📦 Заказов: {total_orders}",
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )

@dp.message_handler(lambda msg: msg.text == "📢 Сделать рассылку" and msg.from_user.id == ADMIN_ID)
async def admin_broadcast_start(message: Message):
    await message.answer(
        "📢 *Режим рассылки*\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    # Здесь можно добавить состояние для рассылки, но для простоты реализуем в следующем хэндлере
    # Я оставлю это как точку для расширения. Пока просто выведем список пользователей в консоль.

# --- Обработка остальных сообщений (fallback) ---
@dp.message_handler()
async def other_messages(message: Message):
    await message.answer(
        "⚠️ Я не понимаю эту команду.\nПожалуйста, воспользуйтесь кнопками меню.",
        reply_markup=main_keyboard(message.from_user.id)
    )

# --- Запуск бота ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
