import asyncio
import json
import urllib.robotparser
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

async def is_scraping_allowed(url: str, user_agent: str = "*") -> bool:
    def _check():
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            return rp.can_fetch(user_agent, url)
        except Exception:
            return True
    return await asyncio.to_thread(_check)

async def scrape_trustpilot(company_name: str) -> dict | None:
    url = f"https://www.trustpilot.com/review/{company_name.lower().replace(' ', '')}"
    
    # Check robots.txt
    allowed = await is_scraping_allowed(url)
    if not allowed:
        return {"error": "Scraping disallowed by robots.txt", "url": url}
        
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.text, "html.parser")
            rating = None
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0]
                    if "aggregateRating" in data:
                        rating = data["aggregateRating"]["ratingValue"]
                        break
                except Exception:
                    continue
            if not rating:
                meta = soup.find("meta", attrs={"name": "twitter:image:alt"})
                if meta and "rating" in meta.get("content", "").lower():
                    import re
                    match = re.search(r"(\d+\.\d+|\d+)", meta.get("content", ""))
                    if match:
                        rating = float(match.group(1))
            return {"rating": float(rating) if rating else None, "url": url}
    except Exception as exc:
        return {"error": str(exc), "url": url}

async def scrape_g2(company_name: str) -> dict | None:
    url = f"https://www.g2.com/products/{company_name.lower().replace(' ', '-')}/reviews"
    
    # Check robots.txt
    allowed = await is_scraping_allowed(url)
    if not allowed:
        return {"error": "Scraping disallowed by robots.txt", "url": url}
        
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.text, "html.parser")
            rating = None
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if "aggregateRating" in data:
                        rating = data["aggregateRating"]["ratingValue"]
                        break
                except Exception:
                    continue
            if not rating:
                meta = soup.find("meta", itemprop="ratingValue")
                if meta:
                    rating = meta.get("content")
            return {"rating": float(rating) if rating else None, "url": url}
    except Exception as exc:
        return {"error": str(exc), "url": url}
