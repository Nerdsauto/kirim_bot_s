import os
import json
import time
import logging
import gspread
from telegram import Bot

# --- Config ---
TOKEN = "7976266533:AAH66Fal4sCsKwtlAmUiK5tzSGYMR6f86NY"
GROUP_CHAT_ID = 1002122162040  # <-- O'zingizning guruh chat id'ingizni yozing!
GOOGLE_SHEET_KEY = "12H87uDfhvYDyfuCMEHZJ4WDdcIvHpjn1xp2luvrbLaM"

CHECK_INTERVAL = 60  # soniyalarda, necha sekundda bir tekshirish

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Google Sheets setup ---
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
if not creds_json:
    logger.error("❌ GOOGLE_CREDENTIALS env var not found!")
    exit(1)
creds_info = json.loads(creds_json)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key("12H87uDfhvYDyfuCMEHZJ4WDdcIvHpjn1xp2luvrbLaM").worksheet("realauto")

# --- Telegram Bot setup ---
bot = Bot(token=TOKEN)

# --- Faylda post qilingan mashinalar ro'yxatini saqlash ---
POSTED_FILE = "posted_numbers.json"
if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "r") as f:
        posted_numbers = set(json.load(f))
else:
    posted_numbers = set()

def save_posted():
    with open(POSTED_FILE, "w") as f:
        json.dump(list(posted_numbers), f)

def format_summa(summa, point_format=False):
    try:
        s = "{:,}".format(int(summa)).replace(",", " ")
        if point_format:
            s = s.replace(" ", ".")
        return s
    except Exception:
        return summa

def make_post_text(row):
    # Ustun indekslari (A=0)
    idx_model = 1    # B
    idx_year = 4     # E
    idx_number = 3   # D
    idx_kraska = 6   # G
    idx_probeg = 5   # F
    idx_yoqilgi = 15 # P ("Yoqilg'i turi")
    idx_olingan_narx = 7  # H
    idx_sot_narx = 8      # I

    probeg = format_summa(row[idx_probeg], point_format=True) if len(row) > idx_probeg else "NOMA’LUM"
    olingan_narx = format_summa(row[idx_olingan_narx], point_format=True) if len(row) > idx_olingan_narx else "NOMA’LUM"
    sot_narx = format_summa(row[idx_sot_narx], point_format=True) if len(row) > idx_sot_narx else "NOMA’LUM"

    post = (
        f"<b>🚗 #{row[idx_model] if len(row) > idx_model else 'NOMA’LUM'}</b>\n"
        f"<b>📆 {row[idx_year] if len(row) > idx_year else 'NOMA’LUM'} yil</b>\n"
        f"<b>💎 {row[idx_kraska] if len(row) > idx_kraska else 'NOMA’LUM'}</b>\n"
        f"<b>🏎 {probeg}km</b>\n"
        f"<b>⚡️ Yoqilg'i turi: {row[idx_yoqilgi] if len(row) > idx_yoqilgi else 'NOMA’LUM'}</b>\n"
        f"<b>💰 Olingan narxi: {olingan_narx}$</b>\n"
        f"<b>💰 Sotiladigan narxi: {sot_narx}$</b>\n"
        f"\n"
    )
    return post

def main_loop():
    global posted_numbers
    logger.info("Bot started. Monitoring sheet for sold cars...")
    while True:
        try:
            rows = sheet.get_all_values()
            for row in rows[1:]:
                try:
                    idx_number = 3   # D ustun (mashina raqami)
                    idx_holat = 10   # K ustun ("Holati")
                    idx_rasm = 16    # Q ustun ("Rasm")

                    car_number = row[idx_number] if len(row) > idx_number else None
                    holat = row[idx_holat] if len(row) > idx_holat else None

                    if (
                        car_number
                        and holat
                        and holat.strip().lower() == "sotilgan"
                        and car_number not in posted_numbers
                    ):
                        post_text = make_post_text(row)
                        rasm = row[idx_rasm] if len(row) > idx_rasm else None

                        if rasm:
                            try:
                                bot.send_photo(
                                    chat_id=GROUP_CHAT_ID,
                                    photo=rasm,
                                    caption=post_text,
                                    parse_mode="HTML"
                                )
                                logger.info(f"Posted car {car_number}")
                            except Exception as e:
                                logger.error(f"Error sending photo for {car_number}: {e}")
                        else:
                            try:
                                bot.send_message(
                                    chat_id=GROUP_CHAT_ID,
                                    text=post_text,
                                    parse_mode="HTML"
                                )
                                logger.info(f"Posted car {car_number} (text only)")
                            except Exception as e:
                                logger.error(f"Error sending text for {car_number}: {e}")

                        posted_numbers.add(car_number)
                        save_posted()
                except Exception as e:
                    logger.error(f"Error processing row: {e}")

        except Exception as e:
            logger.error(f"Error fetching sheet: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main_loop()
