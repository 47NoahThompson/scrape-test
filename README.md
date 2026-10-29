# RightMoveRX GitHub Pages + Actions setup

This bundle adds a public GitHub Pages admin page. Its **Update Videos** button opens a prefilled GitHub Issue. Opening that specific issue title triggers the workflow, which runs `scraper.py`, updates `videos.json`, and writes its status to `docs/status.json`.

Visitors need a GitHub account to submit the request, but they do not need repository write access. No GitHub token is placed in browser JavaScript.

## Files

- `scraper.py` — non-interactive scraper; adds newly found videos while preserving existing entries and tags.
- `requirements.txt` — Python dependency.
- `.github/workflows/update-videos.yml` — runs the scraper when the request issue is opened.
- `.github/ISSUE_TEMPLATE/update-videos.yml` — prefilled request form.
- `docs/index.html` — GitHub Pages admin page.
- `docs/status.json` — public status consumed by the page.

## Install

1. Copy these files into the root of `47NoahThompson/rmx-yt-screapper`, preserving the folder structure.
2. Ensure the default branch is named `main`. The workflow currently pushes to `main`.
3. Commit and push the files.
4. In GitHub, open **Settings → Actions → General**. Under Workflow permissions, select **Read and write permissions** and save. This is needed for the workflow to commit `videos.json` and `docs/status.json`.
5. In **Settings → Pages**, choose **Deploy from a branch**, select `main`, and select `/docs`. Save.
6. Wait for Pages to publish. The site will be available at `https://47noahthompson.github.io/rmx-yt-screapper/`.

## Test

1. Open the Pages URL.
2. Click **Update Videos**.
3. Sign in to GitHub if prompted and submit the prefilled issue.
4. Open the repository's **Actions** tab to see the run.
5. The Pages status panel refreshes every 15 seconds. On success, the issue receives a comment and closes.

## Important

- The workflow only runs for an issue with the exact title `Update RightMoveRX videos`.
- Anyone with a GitHub account can submit this request. Consider enabling GitHub's issue/reporting protections and monitoring usage if the page is public.
- The workflow uses `actions/checkout@v4` and `actions/setup-python@v5`. GitHub may display deprecation notices for underlying Node runtimes; these are warnings unless the run explicitly fails.
- If your default branch is not `main`, update the two `git pull --rebase origin main` lines and the branch references in `docs/index.html`.
