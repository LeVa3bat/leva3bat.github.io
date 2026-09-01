import asyncio
import time
import requests
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, Message

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"

# Токен провайдера оплаты (например, ЮKassa) полученный в BotFather
PAYMENT_PROVIDER_TOKEN = "381764678:TEST:00000" # Замените на свой рабочий или тестовый токен

# Ссылка на Firebase Realtime Database
FIREBASE_URL = "https://kapterka-pro-default-rtdb.europe-west1.firebasedatabase.app/licenses"

# Цена в рублях за 30 дней
PRICE_RUB = 500
# =============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_callsigns = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Приветствую в системе активации <b>КАПТЁРКА PRO</b>!\n\n"
        "Для приобретения лицензии на <b>30 ДНЕЙ</b> и доступа к облачной синхронизации, "
        "пожалуйста, отправьте мне ваш <b>Позывной</b> (ровно так же, как вы ввели его в приложении).",
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def handle_callsign(message: Message):
    callsign = message.text.strip().lower()
    user_callsigns[message.from_user.id] = callsign
    
    # Цена передается в копейках (1 рубль = 100 копеек)
    prices = [LabeledPrice(label="PRO Лицензия (30 дней)", amount=PRICE_RUB * 100)]
    
    await message.answer(f"✅ Позывной <b>{callsign.upper()}</b> принят.\n\n"
                         f"Оплатите лицензию банковской картой. После успешной оплаты доступ "
                         f"на 30 дней будет автоматически открыт.", parse_mode="HTML")
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="PRO Лицензия (30 дней)",
        description=f"Доступ к облачной синхронизации подразделения для позывного: {callsign.upper()}",
        payload=f"license_payment_{message.from_user.id}",
        currency="RUB",
        prices=prices,
        provider_token=PAYMENT_PROVIDER_TOKEN,
    )

@dp.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda message: bool(message.successful_payment))
async def on_successful_payment(message: Message):
    user_id = message.from_user.id
    callsign = user_callsigns.get(user_id, f"user_{user_id}")
    
    # 30 дней в миллисекундах
    thirty_days_ms = 30 * 24 * 60 * 60 * 1000
    expires_at = int(time.time() * 1000) + thirty_days_ms
    
    license_data = {
        "status": "APPROVED",
        "expiresAt": expires_at,
        "key": f"PRO-{callsign.upper()}-{int(time.time())}",
        "paid_at": int(time.time()),
        "amount": message.successful_payment.total_amount / 100
    }
    
    url = f"{FIREBASE_URL}/{callsign}.json"
    response = requests.put(url, json=license_data)
    
    if response.status_code == 200:
        await message.answer(
            f"🎉 <b>Оплата успешно получена!</b>\n\n"
            f"Лицензия для позывного <b>{callsign.upper()}</b> активирована ровно на 30 дней.\n\n"
            f"📱 Теперь откройте приложение Каптёрка -> Настройки -> нажмите <b>«ПРОВЕРИТЬ ОПЛАТУ»</b>.\n"
            f"Приложение мгновенно разблокируется!",
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Оплата прошла, но произошла ошибка при записи в базу данных. Обратитесь к разработчику.")

async def main():
    print("Бот запущен и готов принимать платежи картой в рублях!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
