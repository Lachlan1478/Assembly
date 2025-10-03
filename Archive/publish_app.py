# publish_app.py
import os, re, time
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

USER_DATA_DIR = os.getenv("EDGE_PROFILE_DIR", r"C:\Users\User\EdgePW")
PROFILE_NAME  = os.getenv("EDGE_PROFILE_NAME", "Default")

def normalize_to_editor(url: str) -> str:
    # Ensure we're on the editor preview page (selectors below expect editor chrome)
    if "/editor/preview/" not in url:
        url = re.sub(r"/preview/", "/editor/preview/", url)
    return url

def _open_publish_drawer(page):
    # Click the "Publish" button in the top-right editor navbar
    # Primary selector: button with visible text Publish
    # Fallback: aria role
    try:
        page.get_by_role("button", name=re.compile(r"Publish\b", re.I)).click(timeout=5000)
    except Exception:
        page.locator('button:has-text("Publish")').click(timeout=5000)
    # Wait for drawer heading
    page.get_by_role("heading", name=re.compile(r"Publish Your App", re.I)).wait_for(timeout=8000)

def _read_domain_from_drawer(page) -> Optional[str]:
    """
    Scrape the public domain from the Publish drawer.
    It appears under 'Available Domains' as an <a> like: pantry-pal-...base44.app
    """
    # Try a direct anchor containing .base44.app
    links = page.locator("a[href*='.base44.app']")
    if links.count() > 0:
        txt = (links.first.inner_text() or "").strip()
        href = links.first.get_attribute("href") or ""
        # Prefer the visible domain text (no tracking params)
        domain = txt if ".base44.app" in txt else href
        return domain.strip()

    # Fallback: scan drawer text for something.base44.app
    drawer = page.get_by_role("dialog")
    raw = (drawer.inner_text() or "")
    m = re.search(r"([a-z0-9-]+\.(?:base44\.app))", raw, re.I)
    if m:
        return m.group(0)
    return None

def _click_publish_if_needed(page) -> bool:
    """
    Clicks 'Publish App' if present. Returns True if we clicked it (i.e., first publish),
    False if button wasn't present (already published).
    """
    btn = page.get_by_role("button", name=re.compile(r"^Publish App$", re.I))
    if btn.count():
        btn.click(timeout=8000)
        # Optional: wait for any success toast/snackbar
        try:
            page.get_by_text(re.compile(r"(Published|Success|deployed)", re.I)).wait_for(timeout=8000)
        except PWTimeout:
            pass
        return True
    return False

def publish_and_get_domain(editor_preview_url: str, headless: bool = False) -> str:
    url = normalize_to_editor(editor_preview_url)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="msedge",
            headless=headless,
            args=[f"--profile-directory={PROFILE_NAME}"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(15000)

        # Go to editor preview (logged-in via your Edge profile)
        page.goto(url, wait_until="domcontentloaded")

        # Open Publish drawer
        _open_publish_drawer(page)

        # Read existing domain (if any) before publishing
        domain = _read_domain_from_drawer(page)

        # Publish if needed
        clicked = _click_publish_if_needed(page)

        # After publish, drawer can refresh—re-read domain
        if clicked:
            # small wait for drawer to refresh the “Available Domains”
            page.wait_for_timeout(1200)
            domain = _read_domain_from_drawer(page) or domain

        if not domain:
            raise RuntimeError("Could not find public domain in Publish drawer.")

        ctx.close()
        return domain

# --- quick manual test ---
if __name__ == "__main__":
    EDITOR_URL = "https://app.base44.com/apps/68d286dcc9898bd6f6681053/editor/preview/Dashboard"
    pub_domain = publish_and_get_domain(EDITOR_URL, headless=False)
    print("[published]", pub_domain)
