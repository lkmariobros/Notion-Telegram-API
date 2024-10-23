import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from notion_handler import NotionHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import telegram

# Load environment variables
load_dotenv()
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
MAX_ITEMS_PER_CHECK = int(os.getenv('MAX_ITEMS_PER_CHECK', '5'))

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file = 'bot.log'
log_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
log_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[log_handler, logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize NotionHandler
notion_handler = NotionHandler(NOTION_TOKEN, NOTION_DATABASE_ID, MAX_ITEMS_PER_CHECK)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Bot started. Use /check to manually check for new items.')

async def check_recent_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = await notion_handler.get_recently_done_content()
    if items:
        for item in items:
            await send_item_preview(update, context, item)
    else:
        await update.message.reply_text("No new items found.")

async def send_item_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, item):
    formatted_content, reply_markup = notion_handler.format_content_for_telegram(item)
    
    if not formatted_content:
        await update.message.reply_text(f"Error displaying content for {item['properties']['Creation Title']['title'][0]['plain_text']}")
        return

    try:
        sent_message = await update.message.reply_text(
            formatted_content, 
            reply_markup=reply_markup, 
            parse_mode='HTML'
        )
    except telegram.error.BadRequest as e:
        if "Message is too long" in str(e):
            shortened_content = formatted_content[:3000] + "...\n\n(Content truncated due to length. Click 'View full content' to read more)"
            await update.message.reply_text(
                shortened_content,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            logger.error(f"Error sending message: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('approve:'):
        item_id = query.data.split(':')[1]
        success = await notion_handler.update_item_status(item_id, "Scheduled")
        if success:
            # Get the original message's inline keyboard
            original_keyboard = query.message.reply_markup.inline_keyboard
            # Find the "View Full Content" button
            view_content_button = next((button for row in original_keyboard for button in row if button.text == "View full content"), None)
            
            if view_content_button:
                # Create a new keyboard with only the "View Full Content" button
                new_keyboard = InlineKeyboardMarkup([[view_content_button]])
                await query.edit_message_reply_markup(reply_markup=new_keyboard)
            else:
                await query.edit_message_reply_markup(reply_markup=None)
            
            await query.message.reply_text("Item scheduled successfully!")
        else:
            await query.message.reply_text("Failed to schedule item. Please try again later.")

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your chat ID is: {update.effective_chat.id}")

async def check_and_send_updates(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Checking for updates...")
    items = await notion_handler.get_recently_done_content()
    if items:
        for item in items:
            formatted_content, reply_markup = notion_handler.format_content_for_telegram(item)
            if formatted_content:
                try:
                    await context.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=formatted_content,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except telegram.error.BadRequest as e:
                    if "Message is too long" in str(e):
                        shortened_content = formatted_content[:3000] + "...\n\n(Content truncated due to length. Click 'View full content' to read more)"
                        await context.bot.send_message(
                            chat_id=TELEGRAM_CHAT_ID,
                            text=shortened_content,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    else:
                        logger.error(f"Error sending message: {str(e)}")
                except Exception as e:
                    logger.error(f"Error sending message: {str(e)}")
            else:
                logger.error(f"Error formatting content for item: {item['id']}")
    else:
        logger.info("No new items found.")

async def schema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notion_handler.print_database_schema()
    await update.message.reply_text("Database schema printed to console.")

async def view_scheduled_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = await notion_handler.get_scheduled_items()
    if items:
        for item in items:
            await send_item_preview(update, context, item)
    else:
        await update.message.reply_text("No scheduled items found.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def main():
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("get_chat_id", get_chat_id))
        application.add_handler(CommandHandler("check", check_recent_items))
        application.add_handler(CommandHandler("schema", schema))
        application.add_handler(CommandHandler("view_scheduled", view_scheduled_items))
        application.add_handler(CallbackQueryHandler(button_click))
        application.add_error_handler(error_handler)

        # Start periodic checking
        application.job_queue.run_repeating(check_and_send_updates, interval=CHECK_INTERVAL, first=10)

        logger.info("Starting application")
        await application.initialize()
        await application.start()
        
        logger.info("Bot is now polling for updates")
        await application.updater.start_polling()
        
        # Run the bot until you press Ctrl-C
        logger.info("Bot is running. Press Ctrl-C to stop.")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received Ctrl-C, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
    finally:
        logger.info("Stopping application")
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
