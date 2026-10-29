import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

VIDEOS_FILE = Path("videos.json")


def get_section(body, heading):
    """Extract a section from a GitHub issue form."""
    pattern = rf"^### {re.escape(heading)}\s*\n(.*?)(?=^### |\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL)

    if not match:
        raise ValueError(f"Missing issue field: {heading}")

    return match.group(1).strip()


def get_youtube_id(url):
    """Extract the YouTube video ID from supported URL formats."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if host == "youtu.be" or host.endswith(".youtu.be"):
        return parsed.path.strip("/").split("/")[0]

    if host == "youtube.com" or host.endswith(".youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]

        match = re.match(r"/(embed|shorts|live)/([^/?]+)", parsed.path)
        if match:
            return match.group(2)

    return None


def main():
    event_path = os.environ["GITHUB_EVENT_PATH"]

    with open(event_path, "r", encoding="utf-8") as file:
        event = json.load(file)

    issue_body = event["issue"]["body"]

    name = get_section(issue_body, "Exercise Name")
    link = get_section(issue_body, "Video Link")
    description = get_section(issue_body, "Description")

    # Extract only checked checkboxes.
    tags_section = get_section(issue_body, "Exercise Tags")

    tags = re.findall(
        r"^- \[x\] (.+)$",
        tags_section,
        re.MULTILINE | re.IGNORECASE
    )

    video_id = get_youtube_id(link)

    if not video_id:
        raise ValueError("The supplied link is not a recognized YouTube URL.")

    # Load existing videos, or create an empty list.
    if VIDEOS_FILE.exists():
        with open(VIDEOS_FILE, "r", encoding="utf-8") as file:
            videos = json.load(file)
    else:
        videos = []

    if not isinstance(videos, list):
        raise ValueError("videos.json must contain a JSON array.")

    # Prevent duplicate videos.
    for video in videos:
        existing_id = get_youtube_id(video.get("link", ""))

        if existing_id == video_id:
            raise ValueError("This video already exists in videos.json.")

    # Generate the next ID.
    next_id = max(
        (video.get("id", -1) for video in videos),
        default=-1
    ) + 1

    new_video = {
        "id": next_id,
        "name": name,
        "link": link,
        "description": description,
        "tags": tags
    }

    videos.append(new_video)

    with open(VIDEOS_FILE, "w", encoding="utf-8") as file:
        json.dump(videos, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Successfully added: {name}")
    print(f"Tags: {', '.join(tags) if tags else 'None'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
