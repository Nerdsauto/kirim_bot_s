from telegram import Update, Bot, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import logging
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# 1. Telegram bot token
TOKEN = "8183691124:AAHEtu-NYALVH9qcYoIGeRGO4DBHsGnY4pU"

# 2. Remove webhook to avoid polling conflict
bot = Bot(token=TOKEN)
bot.delete_webhook(drop_pending_updates=True)

# 3. Load Google credentials
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
if not creds_json:
    print("❌ GOOGLE_CREDENTIALS env var not found!")
    exit(1)
creds_info = json.loads(creds_json)

# 4. Define scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)

# 5. Authorize gspread
client = gspread.authorize(creds)
sheet = client.open_by_key("12H87uDfhvYDyfuCMEHZJ4WDdcIvHpjn1xp2luvrbLaM").worksheet("realauto")

# 6. Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
ASK_CAR_NUMBER, ASK_CAR_YEAR, GET_IMAGES, GET_INITIAL, GET_3, GET_4, GET_5 = range(7)

def format_summa(summa, point_format=False):
    """Raqamni 6.100.000 yoki 6 100 000 ko‘rinishida formatlash uchun"""
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
    # D ustun = index 3, E ustun = index 4 (Excel'da A=0, B=1, C=2, D=3, E=4)
    idx_number = 3   # D ustun
    idx_year = 4     # E ustun
    idx_model = 1    # B ustun (model)
    idx_kraska = 6   # G ustun
    idx_probeg = 5   # F ustun
    idx_narx = 7     # H ustun

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
            'narx': selected[idx_narx] if len(selected) > idx_narx else 'NOMA’LUM'
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
            'narx': idx_narx
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
        'narx': selected[idx['narx']] if len(selected) > idx['narx'] else 'NOMA’LUM'
    }
    context.user_data['photos'] = []
    update.message.reply_text("📸 Mashina rasmlarini yuboring. Tayyor bo‘lsa, 'Finish' deb yozing.")
    return GET_IMAGES

def get_images(update: Update, context: CallbackContext):
    text = update.message.text
    if text and text.lower() == 'finish':
        update.message.reply_text("💵 Boshlang‘ich to‘lov summasini kiriting ($):")
        return GET_INITIAL
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
        return GET_IMAGES
    update.message.reply_text("❗ Foto yuboring yoki 'Finish' deb yozing.")
    return GET_IMAGES

def get_initial(update: Update, context: CallbackContext):
    context.user_data['initial'] = update.message.text
    update.message.reply_text("💰 3 yillik oylik to‘lovni kiriting ($):")
    return GET_3

def get_3(update: Update, context: CallbackContext):
    context.user_data['pay3'] = update.message.text
    update.message.reply_text("💰 4 yillik oylik to‘lovni kiriting ($):")
    return GET_4

def get_4(update: Update, context: CallbackContext):
    context.user_data['pay4'] = update.message.text
    update.message.reply_text("💰 5 yillik oylik to‘lovni kiriting ($):")
    return GET_5

def get_5(update: Update, context: CallbackContext):
    context.user_data['pay5'] = update.message.text
    c = context.user_data['car']
    photos = context.user_data['photos']
    initial = format_summa(context.user_data['initial'])  # boshlang‘ich uchun bo‘sh joy, oxirida $ bo‘ladi
    pay3 = format_summa(context.user_data['pay3'], point_format=True)
    pay4 = format_summa(context.user_data['pay4'], point_format=True)
    pay5 = format_summa(context.user_data['pay5'], point_format=True)
    probeg = format_summa(c['probeg'], point_format=True)  # probeg ham nuqtali ko‘rinishda
    narx = format_summa(c['narx'], point_format=True)      # narx ham nuqtali ko‘rinishda

    post = (
        f"<b>🚗 #{c['model']}</b>\n"
        f"<b>📆 {c['year']} yil</b>\n"
        f"<b>💎 {c['kraska']}</b>\n"
        f"<b>🏎 {probeg}km</b>\n"
        f"<b>💰 {narx}$</b>\n"
        f"\n"
        f"<b>🏦 Kapital bank</b>\n"
        f"\n"
        f"<b>Boshlang‘ich : {initial} $</b>\n"
        f"\n"
        f"<b>3 yil: {pay3} $</b>so'm\n"
        f"<b>4 yil: {pay4} $</b>so'm\n"
        f"<b>5 yil: {pay5} $</b>so'm\n"
        f"\n"
        f"<b>+998333152222</b>\n"
        f"\n"
        f"<b>https://t.me/real_auto_uz</b>"
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
            GET_INITIAL: [MessageHandler(Filters.text & ~Filters.command, get_initial)],
            GET_3: [MessageHandler(Filters.text & ~Filters.command, get_3)],
            GET_4: [MessageHandler(Filters.text & ~Filters.command, get_4)],
            GET_5: [MessageHandler(Filters.text & ~Filters.command, get_5)]
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
