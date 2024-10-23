from notion_handler import NotionHandler
import asyncio

async def main():
    handler = NotionHandler()
    handler.print_database_schema()
    results = await handler.get_and_send_recently_done_content()
    print(f"\nSent {len(results)} recently done items to Telegram.")

if __name__ == "__main__":
    asyncio.run(main())