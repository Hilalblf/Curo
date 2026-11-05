
import os
import asyncio
import random
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ==========================================
# LEX RATE BOT - V6
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

TIMEZONE = ZoneInfo("Africa/Algiers")

# تاريخ رمضان المتوقع، يمكن تغييره من Railway Variables
RAMADAN_DATE = os.getenv("RAMADAN_DATE", "2027-02-08")

# أقصى فرق مسموح بين المصدرين: 0.50%
MAX_SOURCE_DIFFERENCE = Decimal("0.005")

UPDATE_INTERVAL = 3 * 60 * 60

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("LEX")

last_dhikr = None


# ==========================================
# الأذكار
# ==========================================

ADHKAR = [
    "سبحان الله وبحمده، سبحان الله العظيم",
    "أستغفر الله وأتوب إليه",
    "لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير",
    "سبحان الله والحمد لله ولا إله إلا الله والله أكبر",
    "اللهم صل وسلم على نبينا محمد",
    "لا حول ولا قوة إلا بالله",
    "حسبي الله لا إله إلا هو عليه توكلت وهو رب العرش العظيم",
    "اللهم اغفر لي ولوالدي وللمؤمنين والمؤمنات",
    "رب اغفر لي وتب علي إنك أنت التواب الرحيم",
    "سبحان الله وبحمده عدد خلقه ورضا نفسه وزنة عرشه ومداد كلماته",
    "اللهم إنك عفو تحب العفو فاعف عني",
    "يا حي يا قيوم برحمتك أستغيث",
    "اللهم ارزقنا حسن الخاتمة",
    "اللهم اجعل القرآن ربيع قلوبنا ونور صدورنا",
    "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار",
    "اللهم إني أسألك العفو والعافية في الدنيا والآخرة",
    "اللهم ثبت قلوبنا على دينك",
    "اللهم ارزقنا رزقاً حلالاً طيباً مباركاً فيه",
    "اللهم اهدنا واهد بنا واجعلنا سبباً لمن اهتدى",
    "اللهم أعنا على ذكرك وشكرك وحسن عبادتك",
    "رضيت بالله رباً وبالإسلام ديناً وبمحمد صلى الله عليه وسلم نبياً",
    "اللهم إني أعوذ بك من الهم والحزن والعجز والكسل",
    "اللهم اجعلنا من الذاكرين الشاكرين",
    "أستغفر الله العظيم الذي لا إله إلا هو الحي القيوم وأتوب إليه",
    "اللهم اغفر لنا وارحمنا وأنت خير الراحمين",
    "سبحانك اللهم وبحمدك، أشهد أن لا إله إلا أنت، أستغفرك وأتوب إليك",
    "اللهم ارزقنا قلوباً خاشعة وألسنة ذاكرة",
    "اللهم بارك لنا في أوقاتنا وأعمالنا وأرزاقنا",
    "اللهم إنا نسألك الجنة ونعوذ بك من النار",
    "يا مقلب القلوب ثبت قلبي على دينك",
]


def get_daily_dhikr():
    global last_dhikr

    choices = [item for item in ADHKAR if item != last_dhikr]

    selected = random.choice(choices)
    last_dhikr = selected

    return selected


# ==========================================
# عداد رمضان
# ==========================================

def get_ramadan_countdown():

    today = datetime.now(TIMEZONE).date()

    try:
        ramadan = date.fromisoformat(RAMADAN_DATE)
    except ValueError:
        ramadan = date(2027, 2, 8)

    remaining = (ramadan - today).days

    if remaining > 0:
        return f"🌙 باقي على رمضان تقريبا {remaining} يوماً"

    elif remaining == 0:
        return "🌙 رمضان اليوم بإذن الله"

    else:
        return "🌙 نسأل الله أن يتقبل منا ومنكم صالح الأعمال."


# ==========================================
# المصدر الأول: Twelve Data
# ==========================================

def get_twelve_data_rate():

    url = "https://api.twelvedata.com/exchange_rate"

    params = {
        "symbol": "EUR/USD",
        "apikey": TWELVE_DATA_API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    if "rate" not in data:
        raise ValueError(f"Twelve Data error: {data}")

    eur_usd = Decimal(str(data["rate"]))

    if eur_usd <= 0:
        raise ValueError("Invalid Twelve Data rate")

    # تحويل EUR/USD إلى USD/EUR
    usd_eur = Decimal("1") / eur_usd

    return usd_eur


# ==========================================
# المصدر الثاني: ExchangeRate-API
# ==========================================

def get_second_source_rate():

    url = "https://api.exchangerate-api.com/v4/latest/USD"

    response = requests.get(
        url,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    eur_rate = data.get("rates", {}).get("EUR")

    if eur_rate is None:
        raise ValueError("Second source returned no EUR rate")

    rate = Decimal(str(eur_rate))

    if rate <= 0:
        raise ValueError("Invalid second source rate")

    return rate


# ==========================================
# مقارنة المصدرين
# ==========================================

def fetch_rates_once():

    rate_one = get_twelve_data_rate()
    rate_two = get_second_source_rate()

    difference = abs(rate_one - rate_two)

    average = (rate_one + rate_two) / Decimal("2")

    relative_difference = difference / average

    logger.info(
        "Source 1: %s | Source 2: %s | Difference: %s",
        rate_one,
        rate_two,
        relative_difference,
    )

    if relative_difference > MAX_SOURCE_DIFFERENCE:
        raise ValueError(
            "Source difference is too high. "
            "Publishing cancelled."
        )

    # متوسط المصدرين
    usd_eur = average

    # السعر العكسي
    eur_usd = Decimal("1") / usd_eur

    return usd_eur, eur_usd


# ==========================================
# إعادة المحاولة
# ==========================================

async def get_rates():

    delays = [2, 5, 10]

    for attempt, delay in enumerate(delays, start=1):

        try:
            return await asyncio.to_thread(fetch_rates_once)

        except Exception as error:

            logger.error(
                "Rate attempt %s failed: %s",
                attempt,
                error,
            )

            if attempt < len(delays):
                await asyncio.sleep(delay)

    raise RuntimeError("All rate attempts failed")


# ==========================================
# إنشاء الرسالة
# ==========================================

async def make_message():

    usd_eur, eur_usd = await get_rates()

    dhikr = get_daily_dhikr()

    now = datetime.now(TIMEZONE)

    message = (
        "💱 LEX EXCHANGE RATES\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🇺🇸 1 USD = {usd_eur:.3f} EUR\n"
        f"🇪🇺 1 EUR = {eur_usd:.3f} USD\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        f"{get_ramadan_countdown()}\n\n"

        "🤲 ذكر اليوم:\n"
        f"{dhikr}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        f"🕒 {now.strftime('%Y-%m-%d | %H:%M')}\n"
        "⚡ By LEX"
    )

    return message


# ==========================================
# إرسال آمن إلى Telegram
# ==========================================

async def send_safe(bot, chat_id, message):

    for attempt in range(3):

        try:

            await bot.send_message(
                chat_id=chat_id,
                text=message,
                disable_web_page_preview=True,
            )

            logger.info("Message sent successfully")
            return True

        except Exception as error:

            logger.error(
                "Telegram send attempt %s failed: %s",
                attempt + 1,
                error,
            )

            if attempt < 2:
                await asyncio.sleep(3 * (attempt + 1))

    return False


# ==========================================
# تحديث الأسعار في المجموعة
# ==========================================

async def update_rates(context: ContextTypes.DEFAULT_TYPE):

    try:

        message = await make_message()

        await send_safe(
            context.bot,
            GROUP_ID,
            message,
        )

    except Exception as error:

        logger.exception("Update failed: %s", error)


# ==========================================
# أمر /start
# ==========================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "👋 مرحباً بك في LEX Rate Bot\n\n"
        "💱 للحصول على أسعار العملات:\n"
        "/price\n\n"
        "⚡ By LEX"
    )


# ==========================================
# أمر /price
# ==========================================

async def price_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        message = await make_message()

        await update.message.reply_text(message)

    except Exception as error:

        logger.error("Price command error: %s", error)

        await update.message.reply_text(
            "⚠️ تعذر الحصول على الأسعار حالياً، حاول لاحقاً."
        )


# ==========================================
# معالجة الأخطاء
# ==========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Telegram application error:",
        exc_info=context.error,
    )


# ==========================================
# تشغيل البوت
# ==========================================

def main():

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing")

    if not GROUP_ID:
        raise ValueError("GROUP_ID is missing")

    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is missing")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start_command)
    )

    application.add_handler(
        CommandHandler("price", price_command)
    )

    application.add_error_handler(error_handler)

    # تحديث أول بعد 10 ثوانٍ
    # ثم كل 3 ساعات
    application.job_queue.run_repeating(
        update_rates,
        interval=UPDATE_INTERVAL,
        first=10,
        name="LEX_RATE_UPDATE",
    )

    logger.info("LEX Rate Bot V6 started")

    application.run_polling(
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
 
