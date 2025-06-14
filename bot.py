from telegram import Update, Bot, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import logging
import os
import json
import gspread
from google.oauth2.service_account import Credentials

TOKEN = "7976266533:AAH66Fal4sCsKwtlAmUiK5tzSGYMR6f86NY"

bot = Bot(token=TOKEN)
bot.delete_webhook(drop_pending_updates=True)

creds_json = os.environ.get("GOOGLE_CREDENTIALS")
if not creds_json:
    print("❌ GOOGLE_CREDENTIALS env var not found!")
    exit(1)
creds_info = json.loads(creds_json)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)

client = gspread.authorize(creds)
sheet = client.open_by_key("12H87uDfhvYDyfuCMEHZJ4WDdcIvHpjn1xp2luvrbLaM").worksheet("realauto")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ASK_CAR_NUMBER, ASK_CAR_YEAR, GET_IMAGES = range(3)

def format_summa(summa, point_format=False):
    try:
        s = "{:,}".format(int(summa)).replace(",", " ")
        if point_format:
            s = s.replace(" ", ".")
        return s
    except Exception:
        return summa

def start(update: Update, context: CallbackContext):
    keyboard = [["Post yasash"]]
    update.message.reply_text(
        "🚗 Assalomu alaykum! Menyudan 'Post yasash' ni tanlang.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

def post_yasash(update: Update, context: CallbackContext):
    update.message.reply_text("🚘 Avto raqamini kiriting (masalan: 01A123AA):")
    return ASK_CAR_NUMBER

def ask_car_number(update: Update, context: CallbackContext):
    car_number = update.message.text.strip().replace(" ", "").upper()
    rows = sheet.get_all_values()
    # Ustun indekslari
    idx_model = 1  # B
    idx_year = 4   # E
    idx_number = 3 # D
    idx_kraska = 6 # G
    idx_probeg = 5 # F
    idx_yog = 15   # O (Yoqilg'i turi)
    idx_olingan_narx = 7 # H
    idx_sot_narx = 8     # I

    matches = [
        row for row in rows[1:]
        if len(row) > idx_number
        and row[idx_number].replace(" ", "").upper() == car_number
    ]
    if not matches:
        update.message.reply_text("❌ Bunday avto raqami topilmadi. Qaytadan kiriting:")
        return ASK_CAR_NUMBER
    if len(matches) == 1:
        selected = matches[0]
        context.user_data['car'] = {
            'number': selected[idx_number] if len(selected) > idx_number else 'NOMA’LUM',
            'model': selected[idx_model] if len(selected) > idx_model else 'NOMA’LUM',
            'year': selected[idx_year] if len(selected) > idx_year else 'NOMA’LUM',
            'kraska': selected[idx_kraska] if len(selected) > idx_kraska else 'NOMA’LUM',
            'probeg': selected[idx_probeg] if len(selected) > idx_probeg else 'NOMA’LUM',
            'yoqilgi': selected[idx_yog] if len(selected) > idx_yog else 'NOMA’LUM',
            'olingan_narx': selected[idx_olingan_narx] if len(selected) > idx_olingan_narx else 'NOMA’LUM',
            'sot_narx': selected[idx_sot_narx] if len(selected) > idx_sot_narx else 'NOMA’LUM'
        }
        context.user_data['photos'] = []
        update.message.reply_text("📸 Mashina rasmlarini yuboring. Tayyor bo‘lsa, 'Finish' deb yozing.")
        return GET_IMAGES
    else:
        years = []
        for row in matches:
            if len(row) > idx_year and row[idx_year] not in years:
                years.append(row[idx_year])
        context.user_data['car_number_matches'] = matches
        context.user_data['car_indexes'] = {
            'number': idx_number,
            'model': idx_model,
            'year': idx_year,
            'kraska': idx_kraska,
            'probeg': idx_probeg,
            'yoqilgi': idx_yog,
            'olingan_narx': idx_olingan_narx,
            'sot_narx': idx_sot_narx
        }
        update.message.reply_text(
            "🔎 Bir nechta shu raqamli mashina topildi. Iltimos, avtomobil yilini kiriting. "
            f"Mavjud yillar: {', '.join(years)}"
        )
        return ASK_CAR_YEAR

def ask_car_year(update: Update, context: CallbackContext):
    car_year = update.message.text.strip()
    matches = context.user_data.get('car_number_matches', [])
    idx = context.user_data['car_indexes']
    selected = None
    for row in matches:
        if len(row) > idx['year'] and row[idx['year']] == car_year:
            selected = row
            break
    if not selected:
        update.message.reply_text("❌ Bunday yil topilmadi. Qaytadan yilni kiriting:")
        return ASK_CAR_YEAR
    context.user_data['car'] = {
        'number': selected[idx['number']] if len(selected) > idx['number'] else 'NOMA’LUM',
        'model': selected[idx['model']] if len(selected) > idx['model'] else 'NOMA’LUM',
        'year': selected[idx['year']] if len(selected) > idx['year'] else 'NOMA’LUM',
        'kraska': selected[idx['kraska']] if len(selected) > idx['kraska'] else 'NOMA’LUM',
        'probeg': selected[idx['probeg']] if len(selected) > idx['probeg'] else 'NOMA’LUM',
        'yoqilgi': selected[idx['yoqilgi']] if len(selected) > idx['yoqilgi'] else 'NOMA’LUM',
        'olingan_narx': selected[idx['olingan_narx']] if len(selected) > idx['olingan_narx'] else 'NOMA’LUM',
        'sot_narx': selected[idx['sot_narx']] if len(selected) > idx['sot_narx'] else 'NOMA’LUM'
    }
    context.user_data['photos'] = []
    update.message.reply_text("📸 Mashina rasmlarini yuboring. Tayyor bo‘lsa, 'Finish' deb yozing.")
    return GET_IMAGES

def get_images(update: Update, context: CallbackContext):
    text = update.message.text
    if text and text.lower() == 'finish':
        c = context.user_data['car']
        photos = context.user_data['photos']
        probeg = format_summa(c['probeg'], point_format=True)
        olingan_narx = format_summa(c['olingan_narx'], point_format=True)
        sot_narx = format_summa(c['sot_narx'], point_format=True)

        post = (
            f"<b>🚗 #{c['model']}</b>\n"
            f"<b>📆 {c['year']} yil</b>\n"
            f"<b>💎 {c['kraska']}</b>\n"
            f"<b>🏎 {probeg}km</b>\n"
            f"<b>⛽ Yoqilg'i turi: {c['yoqilgi']}</b>\n"
            f"\n"
            f"<b>💰 Olingan narxi: {olingan_narx}$</b>\n"
            f"<b>💰 Sotiladigan narxi: {sot_narx}$</b>\n"
            f"\n"
        )

        if len(photos) == 1:
            update.message.reply_photo(photos[0], caption=post, parse_mode='HTML')
        elif len(photos) > 1:
            media = [InputMediaPhoto(fid) for fid in photos]
            media[0].caption = post
            media[0].parse_mode = 'HTML'
            update.message.reply_media_group(media)
        else:
            update.message.reply_text(post, parse_mode='HTML')
        return ConversationHandler.END
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
        return GET_IMAGES
    update.message.reply_text("❗ Foto yuboring yoki 'Finish' deb yozing.")
    return GET_IMAGES

def echo(update: Update, context: CallbackContext):
    update.message.reply_text("❗Menyu bo‘yicha davom eting yoki /start yozing.")

def main():
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Post yasash$'), post_yasash)],
        states={
            ASK_CAR_NUMBER: [MessageHandler(Filters.text & ~Filters.command, ask_car_number)],
            ASK_CAR_YEAR: [MessageHandler(Filters.text & ~Filters.command, ask_car_year)],
            GET_IMAGES: [MessageHandler((Filters.photo | Filters.text) & ~Filters.command, get_images)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    updater.start_polling(drop_pending_updates=True)
    logger.info("✅ BOT ISHLAYAPTI")
    updater.idle()

if __name__ == '__main__':
    main()
