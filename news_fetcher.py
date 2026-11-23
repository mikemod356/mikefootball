import aiohttp
from bs4 import BeautifulSoup
import asyncio
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

LEAGUE_URLS = {
    "Premier League": "https://tribuna.com/en/league/premier-league/",
    "La Liga": "https://tribuna.com/en/league/la-liga/",
    "Serie A": "https://tribuna.com/en/league/serie-a/",
    "Bundesliga": "https://tribuna.com/en/league/bundesliga/",
    "Ligue 1": "https://tribuna.com/en/league/ligue-1/",
}

async def fetch_league_news(league: str, limit: int = 5):
    """Fetch latest news headlines for a league from tribuna.com."""
    url = LEAGUE_URLS.get(league)
    if not url:
        return []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=15) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, "lxml")
        articles = []
        # tribuna uses article cards; grab anchors with title text
        for a in soup.select("a[href*='/news/']"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if title and len(title) > 20 and href.startswith("/"):
                full = "https://tribuna.com" + href
                if not any(x["url"] == full for x in articles):
                    articles.append({"title": title, "url": full})
            if len(articles) >= limit:
                break
        return articles
    except Exception as e:
        logger.error(f"fetch_league_news error: {e}")
        return []

async def fetch_team_news(team_slug: str, limit: int = 3):
    """Fetch news for a specific team using tribuna tag pages."""
    url = f"https://tribuna.com/en/clubs/{team_slug}/"
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=15) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, "lxml")
        articles = []
        for a in soup.select("a[href*='/news/']"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if title and len(title) > 20 and href.startswith("/"):
                full = "https://tribuna.com" + href
                if not any(x["url"] == full for x in articles):
                    articles.append({"title": title, "url": full})
            if len(articles) >= limit:
                break
        return articles
    except Exception as e:
        logger.error(f"fetch_team_news error: {e}")
        return []
