import requests
import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

print(f"Token starts with: {NOTION_TOKEN[:7]}...")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}

url = "https://api.notion.com/v1/users/me"

print(f"Requesting URL: {url}")

response = requests.get(url, headers=headers)

print(f"Response status code: {response.status_code}")
print(f"Response content: {response.text}")

if response.status_code == 200:
    print(f"Successfully connected. User: {response.json()['name']}")
else:
    print(f"Error: {response.status_code} - {response.text}")