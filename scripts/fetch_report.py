#!/usr/bin/env python3
"""
Raport viralowych YouTube Shorts dla widzów 35+.

Strategia (ważne ograniczenie):
YouTube Data API v3 NIE udostępnia danych demograficznych widzów dla cudzych
filmów (to dane prywatne właściciela kanału, dostępne tylko jemu przez
YouTube Analytics API). Nie istnieje więc sposób, by dokładnie "wiedzieć",
ile widzów danego Shorta ma 35+ lat.

To, co robimy w zamian — i co jest standardową, sensowną metodą przybliżenia:
1. Pobieramy Shorts z ostatnich 24h dla zestawu zapytań/kategorii, które
   STATYSTYCZNIE i TEMATYCZNIE przyciągają starszą publiczność (finanse,
   nieruchomości, motoryzacja klasyczna, polityka/historia, zdrowie 40+,
   ogród/dom, parenting nastolatków, nostalgia lata 80/90, inwestowanie itd.)
   — w kontrze do kategorii młodzieżowych (tańce, lip-sync, gaming dla
   nastolatków, trendy TikTok-style).
2. Liczymy "viral score" na podstawie tempa przyrostu wyświetleń
   (views / godziny od publikacji), engagement rate (like+comment / views)
   i absolutnej liczby wyświetleń.
3. Wynik to ranking "najbardziej prawdopodobnie viralowych Shortsów wśród
   tematów lubianych przez 35+", NIE pomiar faktycznej demografii widzów.

Ta różnica jest jasno opisana w raporcie wyjściowym (disclaimer), żeby nie
wprowadzać w błąd.
"""

import os
import json
import sys
import math
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

API_KEY = os.environ.get("YOUTUBE_API_KEY")

OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "docs/data/latest.json")
HISTORY_DIR = os.environ.get("HISTORY_DIR", "docs/data/history")

# --- Konfiguracja kategorii tematycznych typowych dla 35+ ---
# Każda kategoria ma własne zapytania wyszukiwania. Trzymamy to pod ~8-9
# zapytań search.list dziennie (każde = 100 jednostek quoty -> ok. 900/10000).
CATEGORIES = {
    "Finanse i inwestowanie": [
        "inwestowanie shorts",
        "personal finance shorts",
    ],
    "Nieruchomości i dom": [
        "nieruchomości shorts",
        "home renovation shorts",
    ],
    "Motoryzacja": [
        "klasyczne auta shorts",
        "car review shorts",
    ],
    "Zdrowie i medycyna 40+": [
        "zdrowie po 40 shorts",
    ],
    "Historia, polityka, nostalgia": [
        "historia shorts ciekawostki",
        "nostalgia lata 90 shorts",
    ],
    "Parenting i rodzina": [
        "parenting shorts rodzina",
    ],
}

# Słowa kluczowe, które ZWYKLE wskazują na treści młodzieżowe — używane do
# lekkiej penalizacji w rankingu (nie do twardego wykluczania, bo to tylko
# heurystyka).
YOUTH_SIGNAL_WORDS = [
    "tiktok dance", "fortnite", "roblox", "among us", "skibidi",
    "rizz", "gyat", "lip sync", "dance challenge", "minecraft funny",
]

MAX_RESULTS_PER_QUERY = 12
REGION_CODES = ["PL", "US"]  # PL bo użytkowniczka jest w Polsce, US dla szerszego zasięgu


def get_youtube_client():
    return build("youtube", "v3", developerKey=API_KEY)


def iso_24h_ago():
    dt = datetime.now(timezone.utc) - timedelta(hours=24)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_shorts(youtube, query, region_code, published_after):
    """search.list filtered to short video duration. Koszt: 100 jednostek."""
    try:
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            videoDuration="short",  # <4 minuty; dalej filtrujemy <=60s przez contentDetails
            order="viewCount",
            publishedAfter=published_after,
            regionCode=region_code,
            maxResults=MAX_RESULTS_PER_QUERY,
            relevanceLanguage=None,
        )
        response = request.execute()
        return response.get("items", [])
    except HttpError as e:
        print(f"Błąd wyszukiwania dla '{query}' ({region_code}): {e}", file=sys.stderr)
        return []


def get_video_details(youtube, video_ids):
    """videos.list w paczkach po 50 ID. Koszt: 1 jednostka za zapytanie."""
    details = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        try:
            request = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(chunk),
            )
            response = request.execute()
            for item in response.get("items", []):
                details[item["id"]] = item
        except HttpError as e:
            print(f"Błąd videos.list: {e}", file=sys.stderr)
    return details


def parse_duration_seconds(iso_duration):
    """Parsuje ISO 8601 duration (np. PT45S, PT1M5S) na sekundy."""
    import re
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or ""
    )
    if not match:
        return None
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s


def compute_viral_score(stats, published_at):
    """
    Viral score = kombinacja tempa wzrostu (views/h), engagement rate
    i absolutnej popularności. Wszystko znormalizowane logarytmicznie,
    żeby pojedynczy hit nie zdominował skali w sposób absurdalny.
    """
    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0))
    comments = int(stats.get("commentCount", 0))

    published_dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    hours_since_publish = max(
        (datetime.now(timezone.utc) - published_dt).total_seconds() / 3600, 0.5
    )

    velocity = views / hours_since_publish  # wyświetlenia na godzinę
    engagement_rate = (likes + comments * 2) / views if views > 0 else 0

    score = (
        math.log10(velocity + 1) * 4.0
        + engagement_rate * 50.0
        + math.log10(views + 1) * 1.5
    )
    return round(score, 3), round(velocity, 1), round(engagement_rate * 100, 2)


def has_youth_signal(text):
    text_lower = text.lower()
    return any(word in text_lower for word in YOUTH_SIGNAL_WORDS)


def build_report():
    youtube = get_youtube_client()
    published_after = iso_24h_ago()

    all_videos = {}  # video_id -> merged info
    seen_search_results = {}  # video_id -> (category, query)

    for category, queries in CATEGORIES.items():
        for query in queries:
            for region in REGION_CODES:
                items = search_shorts(youtube, query, region, published_after)
                for item in items:
                    vid = item["id"]["videoId"]
                    if vid not in seen_search_results:
                        seen_search_results[vid] = category

    video_ids = list(seen_search_results.keys())
    if not video_ids:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window": "last_24h",
            "videos": [],
            "note": "Brak wyników w ostatnich 24h dla skonfigurowanych zapytań.",
        }

    details = get_video_details(youtube, video_ids)

    results = []
    for vid, category in seen_search_results.items():
        item = details.get(vid)
        if not item:
            continue

        duration_s = parse_duration_seconds(
            item.get("contentDetails", {}).get("duration", "")
        )
        # Twarda reguła Shorts: <= 60 sekund
        if duration_s is None or duration_s > 60:
            continue

        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        published_at = snippet.get("publishedAt")

        score, velocity, engagement_pct = compute_viral_score(stats, published_at)

        youth_flag = has_youth_signal(title + " " + description)
        if youth_flag:
            score -= 2.0  # lekka penalizacja, nie wykluczenie

        results.append({
            "video_id": vid,
            "title": title,
            "channel": snippet.get("channelTitle", ""),
            "category": category,
            "published_at": published_at,
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "views_per_hour": velocity,
            "engagement_pct": engagement_pct,
            "viral_score": round(score, 2),
            "youth_signal_detected": youth_flag,
            "url": f"https://www.youtube.com/shorts/{vid}",
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        })

    results.sort(key=lambda x: x["viral_score"], reverse=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": "last_24h",
        "methodology_note": (
            "YouTube Data API nie udostępnia danych demograficznych widzów dla "
            "cudzych filmów. Ten raport rankinguje Shorts z ostatnich 24h "
            "po tempie wzrostu wyświetleń i engagement w kategoriach "
            "tematycznych statystycznie popularnych wśród widzów 35+ "
            "(finanse, nieruchomości, motoryzacja, zdrowie, historia, "
            "parenting). To przybliżenie, nie pomiar wieku widzów."
        ),
        "total_candidates": len(results),
        "videos": results[:50],
        "categories_scanned": list(CATEGORIES.keys()),
    }
    return report


def save_report(report):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history_path = os.path.join(HISTORY_DIR, f"{date_str}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Zapisano raport: {OUTPUT_PATH} oraz {history_path}")
    print(f"Liczba znalezionych Shorts: {len(report.get('videos', []))}")


if __name__ == "__main__":
    if not API_KEY:
        print("BŁĄD: brak zmiennej środowiskowej YOUTUBE_API_KEY", file=sys.stderr)
        sys.exit(1)
    report = build_report()
    save_report(report)
