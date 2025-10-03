# generate_initial_design.py
# Base44 automation using persistent Edge profile (no storage_state.json needed)

import uuid, re, time
from typing import Optional, Tuple
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE44_URL = "https://app.base44.com"

# Path to your seeded Edge profile (update if different)
EDGE_PROFILE_DIR = r"C:\Users\User\EdgePW"
PROFILE_NAME = "Default"   # usually "Default"

def _extract_app_id(preview_url: str) -> Optional[str]:
    m = re.search(r"/preview/([a-zA-Z0-9_-]+)", preview_url)
    if m: return m.group(1)
    m = re.search(r"[?&]app_id=([a-zA-Z0-9_-]+)", preview_url)
    if m: return m.group(1)
    return None

def _wait_for_preview_url(context, page, timeout_s: int = 180) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            link = page.locator('a:has-text("Preview"), a[href*="/preview/"]').first
            if link.count() and link.is_visible():
                href = link.get_attribute("href")
                if href:
                    return href if href.startswith("http") else (BASE44_URL + href)
        except PWTimeout:
            pass
        except Exception:
            pass

        # also scan any open page
        for p in context.pages:
            url = p.url or ""
            if "/preview/" in url:
                return url
        time.sleep(1)
    raise TimeoutError("Timed out waiting for preview URL")

def _find_builder_input(page):
    try:
        box = page.get_by_placeholder(re.compile(r"Describe the app you want to create", re.I))
        box.wait_for(state="visible", timeout=10_000)
        return box
    except Exception:
        pass
    loc = page.locator("textarea, [contenteditable='true']").first
    loc.wait_for(state="visible", timeout=10_000)
    return loc

def build_from_spec(spec_text: str, headless: bool = True) -> Tuple[str, str]:
    with sync_playwright() as p:
        # 👇 Launch with your persistent Edge profile
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=EDGE_PROFILE_DIR,
            channel="msedge",
            headless=headless,
            args=[f"--profile-directory={PROFILE_NAME}"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(30_000)

        page.goto(BASE44_URL + "/", wait_until="domcontentloaded")

        # Should already be logged in since we're reusing EdgePW profile
        input_loc = _find_builder_input(page)

        # Clear + type spec text
        try:
            tag = page.evaluate("(el)=>el.tagName && el.tagName.toLowerCase()", input_loc.element_handle())
        except Exception:
            tag = None

        if tag in ("textarea", "input"):
            input_loc.fill("")
            input_loc.fill(spec_text)
        else:
            page.evaluate(
                "(el, txt)=>{el.focus(); el.innerText=''; el.dispatchEvent(new Event('input',{bubbles:true}));}",
                input_loc.element_handle(), spec_text
            )
            input_loc.type(spec_text, delay=1)

        # Try to submit
        submitted = False
        try:
            container = input_loc.locator(
                "xpath=ancestor::*[(self::div or self::section)][.//textarea or .//*[@contenteditable='true']][1]"
            )
            btn = container.locator(
                'button:has-text("Generate"), button:has-text("Build"), button:has(svg)'
            ).first
            if btn.count():
                btn.scroll_into_view_if_needed()
                btn.click(timeout=5_000)
                submitted = True
        except Exception:
            pass

        if not submitted:
            try:
                input_loc.press("Control+Enter")  # Windows/Linux
                submitted = True
            except Exception:
                pass

        if not submitted:
            try:
                gbtn = page.locator('button:has-text("Generate"), button:has-text("Build"), button:has(svg)').first
                if gbtn.count():
                    gbtn.click(timeout=5_000)
                    submitted = True
            except Exception:
                pass

        if not submitted:
            input_loc.press("Enter")

        # Wait for preview URL
        preview_url = _wait_for_preview_url(ctx, page, timeout_s=180)
        app_id = _extract_app_id(preview_url) or f"unknown_{int(time.time())}"

        print(f"[✓] Built app {app_id}, preview at: {preview_url}")

        ctx.close()
        return app_id, preview_url

def create_initial_design(initial_spec):
    return build_from_spec(initial_spec, headless=False)
