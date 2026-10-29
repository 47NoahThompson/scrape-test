import json
from pathlib import Path

import yt_dlp

CHANNEL_URL = "https://www.youtube.com/@RightMoveRX/videos"
OUTPUT_PATH = Path(__file__).with_name("videos.json")


def get_channel_videos(channel_url):
    """Return video details from a YouTube channel's Videos tab."""
    if not channel_url.endswith("/videos"):
        channel_url = channel_url.rstrip("/") + "/videos"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
    }

    videos = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Scraping channel: {channel_url}")
        info = ydl.extract_info(channel_url, download=False)

        if not info:
            return []

        for entry in info.get("entries", []):
            if not entry:
                continue

            video_id = entry.get("id")
            if not video_id:
                continue

            videos.append({
                "id": len(videos),
                "name": entry.get("title") or video_id,
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "description": entry.get("description") or "",
                "tags": entry.get("tags") or [],
            })

    return videos


def load_existing_videos(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("videos.json must contain a JSON array.")

    return [item for item in data if isinstance(item, dict) and item.get("link")]


def main():
    new_videos = get_channel_videos(CHANNEL_URL)

    # Do not replace a working database if YouTube temporarily returns no results.
    if not new_videos:
        raise RuntimeError("The scraper returned zero videos; leaving videos.json unchanged.")

    existing_videos = load_existing_videos(OUTPUT_PATH)
    existing_links = {video["link"] for video in existing_videos}

    additions = []
    for video in new_videos:
        if video["link"] not in existing_links:
            additions.append(video)
            existing_links.add(video["link"])

    # New uploads appear first. Existing entries (including manually maintained
    # tags) are preserved.
    combined = additions + existing_videos

    for index, video in enumerate(combined):
        video["id"] = index

    temp_path = OUTPUT_PATH.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(combined, file, indent=4, ensure_ascii=False)
        file.write("\n")

    temp_path.replace(OUTPUT_PATH)

    print(f"Found {len(new_videos)} videos on the channel.")
    print(f"Added {len(additions)} new videos.")
    print(f"Total videos in database: {len(combined)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
