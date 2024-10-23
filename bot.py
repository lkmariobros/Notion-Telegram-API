import os
import logging
import asyncio
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from notion_handler import NotionHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # Default to 300 seconds if not set
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

# Initialize NotionHandler
notion_handler = NotionHandler(NOTION_TOKEN, NOTION_DATABASE_ID)

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text('Bot started. Use /check to fetch recent items or /quote to get a random quote.')

async def check_recent_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Check command received")
    items = await notion_handler.get_recently_done_content()
    logger.info(f"Fetched {len(items)} items from Notion")
    if not items:
        await update.message.reply_text('No new completed items found.')
        return

    for item in items:
        await send_item_preview(update, context, item)

async def send_item_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, item):
    title = item['properties']['Creation Title']['title'][0]['plain_text']
    url = item['url']
    content = item.get('content', 'No content available')

    message = f"{title}\n\n{content[:200]}...\n\nView in Notion: {url}"

    keyboard = [
        [InlineKeyboardButton("View in Notion", url=url)],
        [InlineKeyboardButton("Send to channel", callback_data=f"send_to_channel:{item['id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        await update.message.reply_text(f"Error displaying content for {title}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    action = data[0]

    if action == "approve":
        item_id = data[1]
        success = await notion_handler.update_item_status(item_id)
        if success:
            await query.edit_message_text(text=f"Item {item_id} has been scheduled.")
        else:
            await query.edit_message_text(text=f"Failed to schedule item {item_id}.")

async def schema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Schema command received")
    notion_handler.print_database_schema()
    await update.message.reply_text('Database schema printed to console. Check your server logs.')

async def get_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Quote command received")
    quote = await notion_handler.get_random_quote()
    await update.message.reply_text(quote)

async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check_recent_items))
    application.add_handler(CommandHandler("schema", schema))
    application.add_handler(CommandHandler("quote", get_quote))
    application.add_handler(CallbackQueryHandler(button_click))
    
    logger.info("Starting bot")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
