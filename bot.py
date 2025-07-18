import os
import json
import time
import logging
import gspread
from telegram import Bot
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# --- Config ---
TOKEN = "7976266533:AAH66Fal4sCsKwtlAmUiK5tzSGYMR6f86NY"
GOOGLE_SHEET_KEY = "12H87uDfhvYDyfuCMEHZJ4WDdcIvHpjn1xp2luvrbLaM"
DRIVE_FOLDER_ID = "1zy0hVpoATmkp8tPF3bsdVyaiofFrWdc3"

CHECK_INTERVAL = 60

# --- Supergroup Chat ID va Topic IDlar ---
CHAT_ID = -1002625034435      # Sizning superguruh chat ID (faqat bitta!)
TOPIC_ID_MAVJUD = 440         # "mavjud" mashinalar topic ID
TOPIC_ID_SOTILGAN = 348       # "sotilgan" mashinalar topic ID

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

creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet("realauto")

# --- Google Drive API setup ---
drive_service = build('drive', 'v3', credentials=creds)

# --- Telegram Bot setup ---
bot = Bot(token=TOKEN)

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

def make_post_text(row, holat):
    idx_model = 2
    idx_year = 5
    idx_number = 4
    idx_kraska = 7
    idx_probeg = 6
    idx_yoqilgi = 16
    idx_olingan_narx = 8
    idx_sot_narx = 12

    probeg = format_summa(row[idx_probeg], point_format=True) if len(row) > idx_probeg else "NOMA’LUM"
    olingan_narx = format_summa(row[idx_olingan_narx], point_format=True) if len(row) > idx_olingan_narx else "NOMA’LUM"
    sot_narx = format_summa(row[idx_sot_narx], point_format=True) if len(row) > idx_sot_narx else "NOMA’LUM"

    post = (
        f"<b>🚗 #{row[idx_model] if len(row) > idx_model else 'NOMA’LUM'}</b>\n"
        f"<b>📆 {row[idx_year] if len(row) > idx_year else 'NOMA’LUM'} yil</b>\n"
        f"<b>💎 {row[idx_kraska] if len(row) > idx_kraska else 'NOMA’LUM'}</b>\n"
        f"<b>🏎 {probeg}km</b>\n"
        f"<b>⛽ Yoqilg'i turi: {row[idx_yoqilgi] if len(row) > idx_yoqilgi else 'NOMA’LUM'}</b>\n"
        f"<b>💰 Olingan narxi: {olingan_narx}</b>\n"
    )
    if holat == "sotilgan":
        post += f"<b>🤝 Sotilgan narxi: {sot_narx}</b>\n"
    post += "\n"
    return post

def make_drive_public_url(file_id):
    return f"https://drive.google.com/uc?export=view&id={file_id}"

def get_file_id_by_name(file_path, folder_id):
    file_name = os.path.basename(file_path)
    query = f"'{folder_id}' in parents and name='{file_name}' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def main_loop():
    global posted_numbers
    logger.info("Bot started. Monitoring sheet for cars (topics)...")
    while True:
        try:
            rows = sheet.get_all_values()
            for row in rows[1:]:
                try:
                    idx_number = 4   # D
                    idx_holat = 11   # K
                    idx_rasm = 18    # Q

                    car_number = row[idx_number] if len(row) > idx_number else None
                    holat = row[idx_holat].strip().lower() if len(row) > idx_holat and row[idx_holat] else None

                    if (
                        car_number
                        and holat in ["mavjud", "sotilgan"]
                        and car_number not in posted_numbers
                    ):
                        post_text = make_post_text(row, holat)
                        rasm_nomi = row[idx_rasm] if len(row) > idx_rasm else None

                        photo_url = None
                        if rasm_nomi:
                            if rasm_nomi.startswith("http"):
                                photo_url = rasm_nomi
                            else:
                                file_id = get_file_id_by_name(rasm_nomi, DRIVE_FOLDER_ID)
                                if file_id:
                                    photo_url = make_drive_public_url(file_id)
                                else:
                                    logger.warning(f"Image file '{rasm_nomi}' not found in Drive folder.")

                        # Topic ID ni holatga qarab tanlash
                        if holat == "sotilgan":
                            topic_id = TOPIC_ID_SOTILGAN
                        else:
                            topic_id = TOPIC_ID_MAVJUD

                        if photo_url:
                            try:
                                bot.send_photo(
                                    chat_id=CHAT_ID,
                                    photo=photo_url,
                                    caption=post_text,
                                    parse_mode="HTML",
                                    message_thread_id=topic_id
                                )
                                logger.info(f"Posted car {car_number} to topic {topic_id}")
                            except Exception as e:
                                logger.error(f"Error sending photo for {car_number}: {e}")
                        else:
                            try:
                                bot.send_message(
                                    chat_id=CHAT_ID,
                                    text=post_text,
                                    parse_mode="HTML",
                                    message_thread_id=topic_id
                                )
                                logger.info(f"Posted car {car_number} (text only) to topic {topic_id}")
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
