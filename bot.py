
import os
import asyncio
import logging
import random

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import requests

from telegram import Update
from telegram.error import (
    Conflict,
    NetworkError,
    TimedOut,
    RetryAfter,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# ============================================================
# CONFIG — LEX FX BOT V5
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

TIMEZONE = ZoneInfo("Africa/Algiers")

# التاريخ المتوقع لبداية رمضان 2027
RAMADAN_DATE = os.getenv(
    "RAMADAN_DATE",
    "2027-02-08"
)

UPDATE_INTERVAL = 3 * 60 * 60
FIRST_UPDATE = 10

MAX_SOURCE_DIFFERENCE = Decimal("0.005")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("LEX")


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "LEX-FX-Bot/5.0",
    "Accept": "application/json",
})


# ============================================================
# ADHKAR DATABASE
# ============================================================

ADHKAR = [

    "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ.",

    "أَسْتَغْفِرُ اللَّهَ وَأَتُوبُ إِلَيْهِ.",

    "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ.",

    "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ ﷺ.",

    "سُبْحَانَ اللَّهِ، وَالْحَمْدُ لِلَّهِ، وَلَا إِلَهَ إِلَّا اللَّهُ، وَاللَّهُ أَكْبَرُ.",

    "رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ ﷺ نَبِيًّا.",

    "اللَّهُمَّ اغْفِرْ لِي وَارْحَمْنِي وَاهْدِنِي.",

    "الْحَمْدُ لِلَّهِ عَلَى كُلِّ حَالٍ.",

    "لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ.",

    "اللَّهُمَّ إِنَّكَ عَفُوٌّ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي.",

    "رَبِّ اغْفِرْ لِي وَلِوَالِدَيَّ وَلِلْمُؤْمِنِينَ.",

    "اللَّهُمَّ ارْزُقْنَا حُسْنَ الْخَاتِمَةِ.",

    "يَا رَبِّ، لَكَ الْحَمْدُ كَمَا يَنْبَغِي لِجَلَالِ وَجْهِكَ وَعَظِيمِ سُلْطَانِكَ.",

    "اللَّهُمَّ اهْدِنَا وَاهْدِ بِنَا وَاجْعَلْنَا سَبَبًا لِمَنِ اهْتَدَى.",

    "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ.",

    "اللَّهُمَّ أَصْلِحْ لَنَا دِينَنَا وَدُنْيَانَا وَآخِرَتَنَا.",

    "اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ.",

    "حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ.",

    "اللَّهُمَّ اجْعَلْنَا مِنَ الشَّاكِرِينَ وَالصَّابِرِينَ.",

    "رَبِّ زِدْنِي عِلْمًا.",

    "اللَّهُمَّ بَارِكْ لَنَا فِي أَرْزَاقِنَا وَأَعْمَارِنَا.",

    "أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ الَّذِي لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ وَأَتُوبُ إِلَيْهِ.",

    "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ.",

    "اللَّهُمَّ اجْعَلْنَا مِنْ أَهْلِ الْجَنَّةِ.",

    "يَا مُقَلِّبَ الْقُلُوبِ ثَبِّتْ قَلْبِي عَلَى دِينِكَ.",

    "اللَّهُمَّ أَعِنَّا عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِكَ.",

    "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا.",

    "اللَّهُمَّ ارْحَمْ وَالِدَيْنَا وَاغْفِرْ لَهُمَا.",

    "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ.",

    "اللَّهُمَّ فَرِّجْ هُمُومَنَا وَيَسِّرْ أُمُورَنَا."
]


# منع تكرار الذكر السابق
last_dhikr = None


def get_daily_dhikr():

    global last_dhikr

    choices = [
        item for item in ADHKAR
        if item != last_dhikr
    ]

    selected = random.choice(choices)

    last_dhikr = selected

    return selected


# ============================================================
# RAMADAN COUNTDOWN — ALGERIA
# ============================================================

def get_ramadan_countdown():

    today = datetime.now(TIMEZONE).date()

    try:

        ramadan = date.fromisoformat(RAMADAN_DATE)

    except ValueError:

        logger.error("Invalid RAMADAN_DATE")

        ramadan = date(2027, 2, 8)

    remaining = (ramadan - today).days

    if remaining > 1:

        countdown = (
            f"🌙 باقي تقريباً {remaining} يوماً "
            "على رمضان بإذن الله."
        )

    elif remaining == 1:

        countdown = (
            "🌙 باقي تقريباً يوم واحد "
            "على رمضان بإذن الله."
        )

    elif remaining == 0:

        countdown = (
            "🌙 من المتوقع أن يكون اليوم بداية رمضان "
            "بإذن الله."
        )

    else:

        countdown = (
            "🌙 نسأل الله أن يتقبل منا ومنكم "
            "صالح الأعمال."
        )

    return (
        countdown
        + "\n"
        + "📌 التاريخ تقريبي ويخضع لرؤية الهلال والإعلان الرسمي."
    )


# ============================================================
# VALIDATE RATE
# ============================================================

def validate_rate(value):

    try:

        rate = Decimal(str(value))

        if not rate.is_finite():
            return None

        if rate <= Decimal("0.50"):
            return None

        if rate >= Decimal("1.50"):
            return None

        return rate

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# SOURCE 1 — TWELVE DATA
# ============================================================

def get_twelve_data():

    if not TWELVE_DATA_API_KEY:

        raise RuntimeError(
            "TWELVE_DATA_API_KEY missing"
        )

    url = "https://api.twelvedata.com/price"

    params = {
        "symbol": "EUR/USD",
        "apikey": TWELVE_DATA_API_KEY,
    }

    logger.info("1️⃣ Requesting Twelve Data...")

    response = session.get(
        url,
        params=params,
        timeout=(5, 15),
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get("message", "Twelve Data error")
        )

    price = data.get("price")

    if price is None:

        raise RuntimeError(
            f"Twelve Data price missing: {data}"
        )

    eur_usd = validate_rate(price)

    if eur_usd is None:

        raise RuntimeError(
            f"Invalid EUR/USD: {price}"
        )

    usd_eur = Decimal("1") / eur_usd

    logger.info(
        "✅ Twelve Data EUR/USD = %.8f",
        eur_usd,
    )

    return usd_eur


# ============================================================
# SOURCE 2 — EXCHANGERATE.DEV
# ============================================================

def get_exchangerate_dev():

    url = (
        "https://api.exchangerate.dev/"
        "v1/latest/USD"
    )

    params = {
        "symbols": "EUR",
    }

    logger.info("2️⃣ Requesting ExchangeRate.dev...")

    response = session.get(
        url,
        params=params,
        timeout=(5, 15),
    )

    response.raise_for_status()

    data = response.json()

    if data.get("result") != "success":

        raise RuntimeError(
            f"ExchangeRate.dev error: {data}"
        )

    rates = data.get("rates")

    if not isinstance(rates, dict):

        raise RuntimeError(
            "ExchangeRate.dev rates missing"
        )

    value = rates.get("EUR")

    usd_eur = validate_rate(value)

    if usd_eur is None:

        raise RuntimeError(
            f"Invalid ExchangeRate.dev USD/EUR: {value}"
        )

    logger.info(
        "✅ ExchangeRate.dev USD/EUR = %.8f",
        usd_eur,
    )

    return usd_eur


# ============================================================
# DOUBLE VERIFICATION
# ============================================================

def get_verified_rate_sync():

    twelve_rate = get_twelve_data()

    second_rate = get_exchangerate_dev()

    difference = abs(
        twelve_rate - second_rate
    )

    average = (
        twelve_rate + second_rate
    ) / Decimal("2")

    relative_difference = difference / average

    logger.info(
        "📊 Twelve Data = %.8f",
        twelve_rate,
    )

    logger.info(
        "📊 ExchangeRate.dev = %.8f",
        second_rate,
    )

    logger.info(
        "📊 Difference = %.4f%%",
        relative_difference * 100,
    )

    if relative_difference > MAX_SOURCE_DIFFERENCE:

        raise RuntimeError(
            "Sources disagree too much: "
            f"{relative_difference * 100:.4f}%"
        )

    usd_eur = average

    eur_usd = Decimal("1") / usd_eur

    logger.info(
        "🎯 VERIFIED USD/EUR = %.8f",
        usd_eur,
    )

    return usd_eur, eur_usd


# ============================================================
# ASYNC RATE + RETRY
# ============================================================

async def get_verified_rate():

    delays = [2, 5, 10]

    for attempt in range(1, 4):

        try:

            logger.info(
                "💱 Rate verification %s/3",
                attempt,
            )

            return await asyncio.to_thread(
                get_verified_rate_sync
            )

        except Exception as e:

            logger.warning(
                "Rate verification failed %s/3: %s",
                attempt,
                e,
            )

            if attempt < 3:

                await asyncio.sleep(
                    delays[attempt - 1]
                )

    raise RuntimeError(
        "Could not verify FX rate"
    )


# ============================================================
# MESSAGE
# ============================================================

def make_message(usd_eur, eur_usd):

    countdown = get_ramadan_countdown()

    dhikr = get_daily_dhikr()

    return (
        f"🇺🇸 1 USD = {usd_eur:.3f} EUR\n"
        f"🇪🇺 1 EUR = {eur_usd:.3f} USD\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{countdown}\n"
        "\n"
        "🤲 ذكر وتذكير:\n"
        f"«{dhikr}»\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "By LEX"
    )


# ============================================================
# TELEGRAM SEND
# ============================================================

async def send_safe(context, chat_id, message):

    for attempt in range(1, 4):

        try:

            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
            )

            logger.info("✅ Telegram message sent")

            return True

        except RetryAfter as e:

            logger.warning(
                "Telegram rate limit: %s sec",
                e.retry_after,
            )

            await asyncio.sleep(
                e.retry_after
            )

        except (
            TimedOut,
            NetworkError,
        ) as e:

            logger.warning(
                "Telegram network error %s/3: %s",
                attempt,
                e,
            )

            if attempt < 3:

                await asyncio.sleep(attempt * 3)

        except Conflict:

            logger.critical("🚨 409 CONFLICT")

            logger.critical(
                "Another instance is using BOT_TOKEN."
            )

            return False

        except Exception as e:

            logger.exception(
                "Telegram send error: %s",
                e,
            )

            return False

    return False


# ============================================================
# AUTOMATIC UPDATE
# ============================================================

async def send_price(
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.info("========== FX UPDATE ==========")

    try:

        usd_eur, eur_usd = await get_verified_rate()

        message = make_message(
            usd_eur,
            eur_usd,
        )

        sent = await send_safe(
            context,
            GROUP_ID,
            message,
        )

        if sent:

            logger.info("✅ VERIFIED PRICE SENT")

        else:

            logger.error("❌ TELEGRAM MESSAGE NOT SENT")

    except Exception as e:

        logger.error(
            "❌ PRICE NOT SENT: %s",
            e,
        )

    logger.info("================================")


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🤖 LEX FX BOT V5 خدام\n"
        "\n"
        "💱 USD / EUR\n"
        "📊 Double Verified Forex Rate\n"
        "🌙 Ramadan Countdown\n"
        "🤲 Islamic Adhkar\n"
        "🇩🇿 Algeria Timezone\n"
        "⏰ تحديث كل 3 ساعات\n"
        "\n"
        "By LEX"
    )


# ============================================================
# /PRICE
# ============================================================

async def price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        usd_eur, eur_usd = await get_verified_rate()

        await update.message.reply_text(
            make_message(
                usd_eur,
                eur_usd,
            )
        )

    except Exception as e:

        logger.error(
            "/price failed: %s",
            e,
        )

        await update.message.reply_text(
            "❌ السعر غير متوفر حاليا.\n"
            "المصدران لم يعطيا سعراً متوافقاً."
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context: ContextTypes.DEFAULT_TYPE,
):

    error = context.error

    if isinstance(error, Conflict):

        logger.critical("🚨 TELEGRAM 409 CONFLICT")

        logger.critical(
            "Only ONE instance can use BOT_TOKEN."
        )

        return

    logger.exception(
        "Telegram application error: %s",
        error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    if not GROUP_ID:
        raise RuntimeError("GROUP_ID missing")

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY missing")

    logger.info("======================================")
    logger.info("🚀 LEX PRO FX BOT V5")
    logger.info("1️⃣ Twelve Data")
    logger.info("2️⃣ ExchangeRate.dev")
    logger.info("🔐 Double verification enabled")
    logger.info("🌙 Ramadan Countdown enabled")
    logger.info("🤲 Adhkar variety enabled")
    logger.info("🇩🇿 Africa/Algiers timezone")
    logger.info("💱 3 decimal places")
    logger.info("⏰ Update every 3 HOURS")
    logger.info("======================================")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(10)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(10)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("price", price)
    )

    app.add_error_handler(error_handler)

    app.job_queue.run_repeating(
        send_price,
        interval=UPDATE_INTERVAL,
        first=FIRST_UPDATE,
    )

    logger.info("✅ Bot initialized")
    logger.info("⏰ Automatic update every 3 hours")
    logger.info("▶️ Telegram polling started")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
 
