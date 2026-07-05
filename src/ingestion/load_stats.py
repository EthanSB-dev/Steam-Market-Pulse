import os
import sys
import time
import re

import requests
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "db"))
from connection import get_engine

STEAMSPY_APPDETAILS_URL = "https://steamspy.com/api.php"
GLOBAL_ACHIEVEMENTS_URL = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
REQUEST_DELAY_SECONDS = 1.5


def get_tracked_appids(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT appid FROM apps ORDER BY appid"))
        return [row[0] for row in result]


def parse_owners_range(owners_str):
    """SteamSpy returns owners as e.g. '10,000,000 .. 20,000,000' - split into low/high ints."""
    if not owners_str:
        return None, None
    parts = re.findall(r"[\d,]+", owners_str)
    if len(parts) != 2:
        return None, None
    return int(parts[0].replace(",", "")), int(parts[1].replace(",", ""))


def fetch_ownership_stats(appid):
    params = {"request": "appdetails", "appid": appid}
    try:
        response = requests.get(STEAMSPY_APPDETAILS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"  -> warning: SteamSpy request failed for {appid}: {e}")
        return None

    if not data or "owners" not in data:
        return None

    owners_low, owners_high = parse_owners_range(data.get("owners"))
    return {
        "owners_low": owners_low,
        "owners_high": owners_high,
        "avg_playtime_forever_minutes": data.get("average_forever"),
        "avg_playtime_2weeks_minutes": data.get("average_2weeks"),
        "median_playtime_forever_minutes": data.get("median_forever"),
        "positive_reviews": data.get("positive"),
        "negative_reviews": data.get("negative"),
    }


def fetch_achievement_stats(appid):
    """Returns a list of (name, global_completion_pct); empty list if the game has none."""
    params = {"gameid": appid, "format": "json"}
    try:
        response = requests.get(GLOBAL_ACHIEVEMENTS_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"  -> warning: achievement request failed for {appid}: {e}")
        return []

    achievements = data.get("achievementpercentages", {}).get("achievements")
    if not achievements:
        return []  # plenty of games simply have no achievements - not an error

    return [(a["name"], a["percent"]) for a in achievements]


def save_ownership_stats(conn, appid, stats):
    conn.execute(
        text("""
            INSERT INTO ownership_stats (
                appid, owners_low, owners_high,
                avg_playtime_forever_minutes, avg_playtime_2weeks_minutes,
                median_playtime_forever_minutes, positive_reviews, negative_reviews
            ) VALUES (
                :appid, :owners_low, :owners_high,
                :avg_forever, :avg_2weeks, :median_forever, :positive, :negative
            )
        """),
        {
            "appid": appid,
            "owners_low": stats["owners_low"],
            "owners_high": stats["owners_high"],
            "avg_forever": stats["avg_playtime_forever_minutes"],
            "avg_2weeks": stats["avg_playtime_2weeks_minutes"],
            "median_forever": stats["median_playtime_forever_minutes"],
            "positive": stats["positive_reviews"],
            "negative": stats["negative_reviews"],
        },
    )


def save_achievement_stats(conn, appid, achievements):
    for name, percent in achievements:
        conn.execute(
            text("""
                INSERT INTO achievement_stats (appid, achievement_name, global_completion_pct)
                VALUES (:appid, :name, :percent)
            """),
            {"appid": appid, "name": name, "percent": percent},
        )


def main():
    engine = get_engine()
    appids = get_tracked_appids(engine)
    print(f"Collecting ownership + achievement stats for {len(appids)} tracked apps...")

    for i, appid in enumerate(appids, start=1):
        ownership = fetch_ownership_stats(appid)
        time.sleep(REQUEST_DELAY_SECONDS)
        achievements = fetch_achievement_stats(appid)
        time.sleep(REQUEST_DELAY_SECONDS)

        with engine.begin() as conn:
            if ownership:
                save_ownership_stats(conn, appid, ownership)
            if achievements:
                save_achievement_stats(conn, appid, achievements)

        owners_desc = f"{ownership['owners_low']}-{ownership['owners_high']}" if ownership else "n/a"
        print(f"[{i}/{len(appids)}] appid {appid}: owners={owners_desc}, achievements_tracked={len(achievements)}")

    print("Done.")


if __name__ == "__main__":
    main()