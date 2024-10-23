from notion_client import Client, APIResponseError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import re
import json
import html
import textwrap
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
from aiohttp import ClientTimeout
import random

load_dotenv()

class NotionHandler:
    def __init__(self, token, database_id, max_items_per_check):
        self.token = token
        self.database_id = database_id
        self.client = Client(auth=token)
        self.last_check_time = (datetime.now() - timedelta(days=7)).isoformat()
        self.max_items_per_check = max_items_per_check
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    async def get_recently_done_content(self):
        try:
            filter_params = {
                "filter": {
                    "and": [
                        {
                            "property": "Status",
                            "status": {
                                "equals": "Done"
                            }
                        },
                        {
                            "timestamp": "last_edited_time",
                            "last_edited_time": {
                                "after": self.last_check_time
                            }
                        }
                    ]
                },
                "sorts": [
                    {
                        "timestamp": "last_edited_time",
                        "direction": "descending"
                    }
                ]
            }

            response = self.client.databases.query(**filter_params, database_id=self.database_id, page_size=self.max_items_per_check)
            
            items = []
            async with aiohttp.ClientSession() as session:
                for page in response['results']:
                    content = await self.extract_page_content(session, page['id'])
                    page['content'] = content
                    items.append(page)

            self.last_check_time = datetime.now().isoformat()
            return items
        except Exception as e:
            print(f"Error fetching Notion content: {str(e)}")
            return []

    async def extract_page_content(self, session, page_id):
        try:
            print(f"Extracting content for page: {page_id}")
            async with session.get(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=self.headers,
                timeout=ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    blocks = data.get('results', [])
                    content = []
                    for block in blocks:
                        if block['type'] == 'paragraph':
                            text = block['paragraph']['rich_text']
                            if text:
                                content.append(text[0]['plain_text'])
                    return content
                else:
                    print(f"Error fetching page content: {response.status}")
                    return []
        except Exception as e:
            print(f"Error extracting page content: {str(e)}")
            return []

    def format_content_for_telegram(self, page):
        try:
            title = html.escape(page['properties']['Creation Title']['title'][0]['plain_text'])
            content = page['content']
            url = page['url']

            formatted_content = f"📝 <b>{title}</b>\n\n"

            # Combine all paragraphs into a single string
            full_content = "\n\n".join(content)

            # Check if content exceeds 1000 characters
            if len(full_content) > 1000:
                # Truncate content and add ellipsis
                truncated_content = full_content[:997] + "..."
                formatted_content += f"💬 <blockquote>{html.escape(truncated_content)}</blockquote>\n\n"
            else:
                formatted_content += f"💬 <blockquote>{html.escape(full_content)}</blockquote>\n\n"

            keyboard = [
                [InlineKeyboardButton("View full content", url=url)],
                [InlineKeyboardButton("✅ Approve", callback_data=f'approve:{page["id"]}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            return formatted_content, reply_markup
        except Exception as e:
            print(f"Error formatting content for Telegram: {str(e)}")
            return None, None

    async def update_item_status(self, item_id, new_status):
        try:
            await asyncio.to_thread(
                self.client.pages.update,
                page_id=item_id,
                properties={"Status": {"status": {"name": new_status}}}
            )
            return True
        except Exception as e:
            print(f"Error updating Notion item status: {str(e)}")
            return False

    def print_database_schema(self):
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            print("\nDatabase properties:")
            for prop, details in database['properties'].items():
                print(f"- {prop}: {details['type']}")
        except Exception as e:
            print(f"Error fetching database schema: {str(e)}")

    async def get_random_quote(self):
        try:
            response = await asyncio.to_thread(
                self.client.databases.query,
                database_id=self.database_id,
                filter={
                    "property": "Type",
                    "select": {
                        "equals": "Quote"
                    }
                }
            )
            
            if response['results']:
                quote = random.choice(response['results'])
                quote_text = quote['properties']['Content']['rich_text'][0]['plain_text']
                author = quote['properties']['Author']['rich_text'][0]['plain_text']
                return f'"{quote_text}"\n- {author}'
            else:
                return "No quotes found in the database."
        except Exception as e:
            print(f"Error fetching quote: {str(e)}")
            return "Error fetching quote."

    async def get_scheduled_items(self):
        try:
            filter_params = {
                "filter": {
                    "property": "Status",
                    "status": {
                        "equals": "Scheduled"
                    }
                },
                "sorts": [
                    {
                        "timestamp": "last_edited_time",
                        "direction": "descending"
                    }
                ]
            }
            response = self.client.databases.query(**filter_params, database_id=self.database_id, page_size=self.max_items_per_check)
            return response['results']
        except Exception as e:
            print(f"Error fetching scheduled items: {str(e)}")
            return []

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))