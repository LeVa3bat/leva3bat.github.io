import asyncio
import time
import requests
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, Message

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"

# Ссылка на вашу Firebase (которую мы только что настроили для синхронизации)
FIREBASE_URL = "https://kapterka-pro-default-rtdb.europe-west1.firebasedatabase.app/licenses"

# Цена в Telegram Stars (например, 100 звезд за вечную PRO лицензию)
STARS_PRICE = 100 
# =============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Храним позывные, чтобы знать, кому выдавать лицензию после оплаты
user_callsigns = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Приветствую в системе активации <b>КАПТЁРКА PRO</b>!\n\n"
        "Для приобретения вечной PRO-лицензии и доступа к облачной синхронизации подразделений, "
        "пожалуйста, отправьте мне ваш <b>Позывной</b> (ровно так же, как вы ввели его в приложении).",
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def handle_callsign(message: Message):
    callsign = message.text.strip().lower()
    user_callsigns[message.from_user.id] = callsign
    
    prices = [LabeledPrice(label="Вечная PRO лицензия", amount=STARS_PRICE)]
    
    await message.answer(f"✅ Позывной <b>{callsign.upper()}</b> принят.\n\n"
                         f"Оплатите лицензию с помощью Telegram Stars. После оплаты лицензия будет "
                         f"МГНОВЕННО активирована в базе данных.", parse_mode="HTML")
    
    # Отправляем счет (Invoice)
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="PRO Лицензия Каптёрки",
        description=f"Бессрочный доступ к облачной синхронизации для позывного: {callsign.upper()}",
        payload=f"license_payment_{message.from_user.id}",
        currency="XTR", # Код валюты для Telegram Stars
        prices=prices,
        provider_token="", # Для Telegram Stars провайдер токен пустой
    )

@dp.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    # Подтверждаем, что готовы принять оплату
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda message: bool(message.successful_payment))
async def on_successful_payment(message: Message):
    user_id = message.from_user.id
    callsign = user_callsigns.get(user_id, f"user_{user_id}")
    
    # 1. Формируем данные лицензии
    license_data = {
        "status": "APPROVED",
        "expiresAt": 0, # 0 = бессрочно
        "key": f"PRO-{callsign.upper()}-STARS",
        "paid_at": int(time.time()),
        "stars_amount": message.successful_payment.total_amount
    }
    
    # 2. Записываем в Firebase!
    url = f"{FIREBASE_URL}/{callsign}.json"
    response = requests.put(url, json=license_data)
    
    if response.status_code == 200:
        await message.answer(
            f"🎉 <b>Оплата успешно получена!</b>\n\n"
            f"Лицензия для позывного <b>{callsign.upper()}</b> активирована в облаке Firebase.\n\n"
            f"📱 Теперь откройте приложение Каптёрка -> Настройки -> нажмите <b>«ПРОВЕРИТЬ ОПЛАТУ»</b>.\n"
            f"Приложение мгновенно разблокируется!",
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Оплата прошла, но произошла ошибка при записи в базу данных. Обратитесь к разработчику.")

async def main():
    print("Бот запущен и готов принимать платежи в Telegram Stars!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
