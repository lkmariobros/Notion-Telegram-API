from notion_client import Client
import os
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

print(f"Using Database ID: {database_id}")

try:
    response = notion.databases.retrieve(database_id)
    print(f"Successfully connected to database: {response['title'][0]['plain_text']}")
except Exception as e:
    print(f"Error: {str(e)}")
