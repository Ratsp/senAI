import asyncio
import json
from pathlib import Path

import httpx

from app.config import settings


async def main() -> None:
    data_path = Path(settings.email_data_file)
    if not data_path.is_absolute():
        data_path = Path(__file__).resolve().parents[1] / data_path
    emails = json.loads(data_path.read_text(encoding="utf-8"))

    async with httpx.AsyncClient(base_url=f"http://localhost:{settings.port}") as client:
        for email in emails:
            response = await client.post("/api/ingest", json=email)
            print(email["message_id"], response.status_code, response.text)
            await asyncio.sleep(settings.simulation_speed)


if __name__ == "__main__":
    asyncio.run(main())
