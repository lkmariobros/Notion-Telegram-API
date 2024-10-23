import requests
import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}

url = "https://api.notion.com/v1/search"

payload = {"filter": {"value": "database", "property": "object"}}

response = requests.post(url, json=payload, headers=headers)

if response.status_code == 200:
    databases = response.json()['results']
    print(f"Found {len(databases)} databases:")
    for db in databases:
        print(f"- {db['id']}: {db['title'][0]['plain_text'] if db['title'] else 'Untitled'}")
else:
    print(f"Error: {response.status_code} - {response.text}")
