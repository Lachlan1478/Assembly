# generate_initial_design.py
# Minimal "Base44 bot" stub — no external deps or API calls.

import uuid

import re, time
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from pathlib import Path

BASE44_URL = "https://app.base44.com"

def _base44_create_stub(prompt: dict):
    app_id = "app_" + uuid.uuid4().hex[:8]
    preview_url = "http://localhost:8000/mock_preview/" + app_id
    # In a real client you would POST 'prompt' to Base44 and parse the response.
    return app_id, preview_url

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
    # 1) Try placeholder (most stable)
    try:
        box = page.get_by_placeholder(re.compile(r"Describe the app you want to create", re.I))
        box.wait_for(state="visible", timeout=10_000)
        return box
    except Exception:
        pass
    # 2) Fallback: any textarea/contenteditable
    loc = page.locator("textarea, [contenteditable='true']").first
    loc.wait_for(state="visible", timeout=10_000)
    return loc

def build_from_spec(spec_text: str, headless: bool = True) -> Tuple[str, str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        storage_file = "storage_state.json"
        if Path(storage_file).exists():
            context = browser.new_context(storage_state=storage_file)
        else:
            context = browser.new_context()

        page = context.new_page()
        page.set_default_timeout(30_000)

        page.goto(BASE44_URL + "/", wait_until="domcontentloaded")

        # if you need to log in manually, do it once in the launched browser;
        # then you can persist storage_state and reuse it later.

        input_loc = _find_builder_input(page)

        # clear + type
        try:
            tag = page.evaluate("(el)=>el.tagName && el.tagName.toLowerCase()", input_loc.element_handle())
        except Exception:
            tag = None

        if tag in ("textarea", "input"):
            input_loc.fill("")       # clear
            input_loc.fill(spec_text)
        else:
            page.evaluate(
                "(el, txt)=>{el.focus(); el.innerText=''; el.dispatchEvent(new Event('input',{bubbles:true}));}",
                input_loc.element_handle(), spec_text
            )
            input_loc.type(spec_text, delay=1)

        # submit: try a nearby button, then keyboard fallbacks
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
                mod = "Control" if page.context.browser.browser_type.name == "chromium" and page.context.browser.is_connected() and page.context.browser_name != "webkit" and page.context.browser_name != "firefox" and page.context.browser_name != "webkit" else "Control"
                # Keep it simple: Ctrl/Cmd+Enter; Windows/Linux use Control
                input_loc.press("Control+Enter")
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

        preview_url = _wait_for_preview_url(context, page, timeout_s=180)
        app_id = _extract_app_id(preview_url) or f"unknown_{int(time.time())}"

        context.close()
        browser.close()
        return app_id, preview_url




def create_initial_design(initial_spec):
    return build_from_spec(initial_spec, headless = False)
