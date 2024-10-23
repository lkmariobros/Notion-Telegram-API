from notion_client import Client
import os
from dotenv import load_dotenv

load_dotenv()

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID")

try:
    response = notion.databases.retrieve(database_id)
    print(f"Successfully connected to database: {response['title'][0]['plain_text']}")
    
    # Let's also try to query the database
    query_response = notion.databases.query(database_id=database_id)
    print(f"Successfully queried the database. Found {len(query_response['results'])} items.")
except Exception as e:
    print(f"Error: {str(e)}")
