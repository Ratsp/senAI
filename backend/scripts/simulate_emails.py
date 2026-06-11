import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
import httpx

from app.config import settings


async def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate streaming emails into SenAI Platform")
    parser.add_argument(
        "--speed",
        type=float,
        default=settings.simulation_speed,
        help="Streaming speed (emails per second)",
    )
    args = parser.parse_args()

    # Load emails from backend directory
    backend_dir = Path(__file__).resolve().parents[1]
    data_path = backend_dir / "email-data-advanced.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Email dataset not found at: {data_path}")

    emails = json.loads(data_path.read_text(encoding="utf-8"))

    # Sort emails by timestamp ascending
    def get_timestamp(e) -> datetime:
        ts = e.get("timestamp")
        if isinstance(ts, str):
            # Normalise 'Z' offset for standard fromisoformat parsing
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)
        return datetime.min

    sorted_emails = sorted(emails, key=get_timestamp)
    total_emails = len(sorted_emails)

    print(f"Starting simulation of {total_emails} emails at {args.speed} emails/sec...\n")

    base_url = f"http://127.0.0.1:{settings.port}"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        for index, email in enumerate(sorted_emails, start=1):
            try:
                response = await client.post("/api/ingest", json=email, headers={"X-API-Key": settings.api_key})
                if response.status_code == 409:
                    print(
                        f"[{index}/{total_emails}] msg_id: {email['message_id']:25} | "
                        f"thread_id: {email['thread_id']:30} | "
                        f"status: 409 (WARNING: Duplicate)"
                    )
                else:
                    print(
                        f"[{index}/{total_emails}] msg_id: {email['message_id']:25} | "
                        f"thread_id: {email['thread_id']:30} | "
                        f"status: {response.status_code}"
                    )
            except Exception as exc:
                print(
                    f"[{index}/{total_emails}] msg_id: {email['message_id']:25} | "
                    f"thread_id: {email['thread_id']:30} | "
                    f"status: FAILED (Error: {exc})"
                )

            # Sleep between requests according to simulation speed
            if args.speed > 0:
                await asyncio.sleep(1.0 / args.speed)


if __name__ == "__main__":
    asyncio.run(main())
