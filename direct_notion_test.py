import requests
import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}"

print(f"Using Database ID: {DATABASE_ID}")
print(f"Using Notion Token: {NOTION_TOKEN[:4]}...{NOTION_TOKEN[-4:]}")

response = requests.get(url, headers=headers)

if response.status_code == 200:
    print(f"Successfully connected to database: {response.json()['title'][0]['plain_text']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
