
import json
import logging
import re
import sys

from pathlib import Path
from urllib.parse import urlparse, parse_qs


# ============================================================
# CONFIGURATION
# ============================================================

VIDEOS_FILE = Path("videos.json")

# GitHub provides the issue body through the workflow environment.
# The script also supports running locally with a manually supplied body.
ISSUE_BODY = None


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


# ============================================================
# ISSUE PARSING
# ============================================================

def get_section(body: str, heading: str) -> str:
    """
    Extracts a section from a GitHub issue form body.

    Example:
    ### Exercise Name

    Backwards Step Up
    """

    logger.info("Extracting section: %s", heading)

    pattern = (
        rf"###\s+{re.escape(heading)}\s*\n"
        rf"(.*?)(?=\n###\s|\Z)"
    )

    match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)

    if not match:
        logger.warning("Section not found: %s", heading)
        return ""

    value = match.group(1).strip()

    if value.lower() in ("_no response_", "no response"):
        value = ""

    logger.info(
        "Successfully extracted '%s' (%d characters)",
        heading,
        len(value)
    )

    return value


def extract_tags(body: str) -> list:
    """
    Extracts checked checkboxes from the Exercise Tags section.
    """

    logger.info("Extracting exercise tags")

    tags_section = get_section(body, "Exercise Tags")

    tags = re.findall(
        r"^- \[x\]\s*(.+)$",
        tags_section,
        re.MULTILINE | re.IGNORECASE
    )

    tags = [tag.strip() for tag in tags]

    logger.info("Found %d selected tags: %s", len(tags), tags)

    return tags


# ============================================================
# YOUTUBE URL HANDLING
# ============================================================

def get_youtube_id(url: str) -> str:
    """
    Extracts the YouTube video ID from supported URL formats.
    """

    logger.info("Extracting YouTube video ID")

    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    video_id = None

    if hostname in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]

    elif hostname.endswith("youtube.com"):

        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]

        elif parsed.path.startswith(
            ("/embed/", "/shorts/", "/live/")
        ):
            video_id = parsed.path.split("/")[2]

    if not video_id:
        logger.error("Could not extract a YouTube video ID from: %s", url)
        raise ValueError("Invalid or unsupported YouTube URL")

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        logger.error("Invalid YouTube video ID: %s", video_id)
        raise ValueError("YouTube video ID must be 11 valid characters")

    logger.info("Successfully extracted YouTube ID: %s", video_id)

    return video_id


# ============================================================
# VIDEO LIBRARY
# ============================================================

def load_videos() -> list:
    """
    Loads videos.json.

    Creates an empty JSON array if the file does not exist.
    Rejects blank or invalid JSON rather than silently overwriting it.
    """

    logger.info("Loading video library: %s", VIDEOS_FILE)

    if not VIDEOS_FILE.exists():
        logger.warning("videos.json does not exist. Creating an empty library.")

        VIDEOS_FILE.write_text("[]\n", encoding="utf-8")

        return []

    if VIDEOS_FILE.stat().st_size == 0:
        raise ValueError(
            "videos.json is empty. Add [] to the file before continuing."
        )

    with VIDEOS_FILE.open("r", encoding="utf-8") as file:
        videos = json.load(file)

    if not isinstance(videos, list):
        raise ValueError("videos.json must contain a JSON array.")

    for index, video in enumerate(videos):
        if not isinstance(video, dict):
            raise ValueError(
                f"Entry at index {index} must be a JSON object."
            )

    logger.info("Successfully loaded %d existing exercises", len(videos))

    return videos


def get_next_id(videos: list) -> int:
    """
    Generates the next exercise ID using the highest existing ID.
    """

    logger.info("Generating next exercise ID")

    ids = []

    for video in videos:
        video_id = video.get("id")

        if isinstance(video_id, int) and not isinstance(video_id, bool):
            ids.append(video_id)

    next_id = max(ids, default=-1) + 1

    logger.info("Next exercise ID: %d", next_id)

    return next_id


def check_duplicate(videos: list, youtube_id: str) -> bool:
    """
    Checks whether a YouTube video already exists in the library.
    """

    logger.info("Checking for duplicate YouTube videos")

    for video in videos:
        existing_link = video.get("link", "")

        try:
            existing_id = get_youtube_id(existing_link)

            if existing_id == youtube_id:
                logger.warning(
                    "Duplicate video found: %s",
                    existing_link
                )
                return True

        except ValueError:
            logger.warning(
                "Skipping existing entry with an invalid YouTube URL: %s",
                existing_link
            )

    logger.info("No duplicate video found")

    return False


def save_videos(videos: list) -> None:
    """
    Writes the updated video library to videos.json.
    """

    logger.info("Saving updated video library")

    with VIDEOS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            videos,
            file,
            indent=4,
            ensure_ascii=False
        )

        file.write("\n")

    logger.info("Successfully saved videos.json")
    logger.info("Total exercises in library: %d", len(videos))


# ============================================================
# MAIN PROCESS
# ============================================================

def main() -> None:

    logger.info("=" * 60)
    logger.info("STARTING EXERCISE SUBMISSION PROCESS")
    logger.info("=" * 60)

    # --------------------------------------------------------
    # Get issue body
    # --------------------------------------------------------

    logger.info("Reading GitHub issue body")

    body = ISSUE_BODY or __import__("os").environ.get("ISSUE_BODY", "")

    if not body.strip():
        raise ValueError(
            "Issue body is empty. Check that ISSUE_BODY is passed "
            "to the workflow."
        )

    logger.info("Issue body loaded (%d characters)", len(body))

    # --------------------------------------------------------
    # Extract exercise information
    # --------------------------------------------------------

    logger.info("Extracting exercise information")

    name = get_section(body, "Exercise Name")
    link = get_section(body, "Video Link")
    description = get_section(body, "Description")
    tags = extract_tags(body)

    logger.info("Exercise name: %s", name)
    logger.info("Video link: %s", link)
    logger.info("Tags: %s", tags)
    logger.info("Description length: %d", len(description))

    # --------------------------------------------------------
    # Validate required fields
    # --------------------------------------------------------

    logger.info("Validating required fields")

    if not name:
        raise ValueError("Exercise name is missing.")

    if not link:
        raise ValueError("Video link is missing.")

    if not description:
        raise ValueError("Exercise description is missing.")

    logger.info("Required fields validated")

    # --------------------------------------------------------
    # Extract YouTube ID
    # --------------------------------------------------------

    video_id = get_youtube_id(link)

    # --------------------------------------------------------
    # Load existing videos
    # --------------------------------------------------------

    videos = load_videos()

    # --------------------------------------------------------
    # Check for duplicates
    # --------------------------------------------------------

    if check_duplicate(videos, video_id):
        logger.info("Submission skipped because the video already exists.")
        return

    # --------------------------------------------------------
    # Generate new exercise
    # --------------------------------------------------------

    next_id = get_next_id(videos)

    exercise = {
        "id": next_id,
        "name": name,
        "link": link,
        "description": description,
        "tags": tags
    }

    logger.info("Prepared new exercise:")
    logger.info(
        "%s",
        json.dumps(exercise, indent=4, ensure_ascii=False)
    )

    # --------------------------------------------------------
    # Add exercise
    # --------------------------------------------------------

    logger.info("Adding exercise to video library")

    videos.append(exercise)

    save_videos(videos)

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    logger.info("=" * 60)
    logger.info("EXERCISE SUCCESSFULLY ADDED")
    logger.info("Exercise ID: %d", next_id)
    logger.info("Exercise name: %s", name)
    logger.info("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:
        main()

    except Exception:
        logger.exception("EXERCISE SUBMISSION FAILED")
        sys.exit(1)
