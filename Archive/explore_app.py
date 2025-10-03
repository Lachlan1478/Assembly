# explore_app.py
import os, re, json, time, hashlib
from pathlib import Path
from collections import deque, defaultdict
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright

APP_URL = os.getenv("APP_URL", "https://app.base44.com/apps/68d286dcc9898bd6f6681053/editor/preview/Dashboard")
USER_DATA_DIR = os.getenv("EDGE_PROFILE_DIR", r"C:\Users\User\EdgePW")
PROFILE_NAME = os.getenv("EDGE_PROFILE_NAME", "Default")

ARTIFACTS = Path("explore_artifacts"); ARTIFACTS.mkdir(exist_ok=True)
IMG_DIR = ARTIFACTS / "screens"; IMG_DIR.mkdir(exist_ok=True)

DENY_WORDS = {"delete","remove","reset","drop","archive","logout","sign out","destroy","pay","checkout","buy"}
MAX_STEPS = 40
MAX_DEPTH = 3

def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()[:12]

def screenshot_and_hash(page, tag: str) -> str:
    out = IMG_DIR / f"{int(time.time()*1000)}_{tag}.png"
    page.screenshot(path=str(out), full_page=True)
    with open(out, "rb") as f:
        return str(out), hashlib.sha1(f.read()).hexdigest()[:12]

def visible_clickables(page):
    """
    Return a deduped list of (label, Locator) for visible, safe-to-click elements.
    Use CSS-only selectors (no mixing with role= engine).
    """
    loc = page.locator("button, a, [role='button'], [role='link'], [onclick], [tabindex]")
    items = []
    try:
        count = min(200, loc.count())
    except Exception:
        count = 0

    seen = set()
    for i in range(count):
        el = loc.nth(i)
        try:
            if not el.is_visible():
                continue
            box = el.bounding_box()
            if not box or box["width"] < 8 or box["height"] < 8:
                continue
            label = (el.text_content() or el.get_attribute("aria-label") or "").strip()
            label = re.sub(r"\s+", " ", label)
            if not label:
                continue
            lower = label.lower()
            if any(w in lower for w in DENY_WORDS):
                continue
            if label in seen:
                continue
            seen.add(label)
            items.append((label, el))
        except Exception:
            continue

    return items[:60]

def ax_summary(page) -> List[str]:
    try:
        snap = page.accessibility.snapshot()
        out = []
        def walk(n, depth=0):
            if not n: return
            role = n.get("role"); name = n.get("name")
            if role in {"button","link","textbox","menuitem","combobox","listitem","heading"}:
                out.append(("  "*depth) + f"{role}: {name}")
            for c in n.get("children",[])[:10]:
                walk(c, depth+1)
        walk(snap)
        return out[:200]
    except Exception:
        return []

def dom_fingerprint(page) -> str:
    try:
        js = r"""
        () => {
          const q = Array.from(document.querySelectorAll("button,a,[role='button'],[role='link'],h1,h2,h3"));
          return q.filter(el => {
            const r = el.getBoundingClientRect();
            return r.width>8 && r.height>8 && !!(el.offsetParent || el.getClientRects().length);
          }).slice(0,200).map(el => {
            const role = el.getAttribute("role") || el.tagName.toLowerCase();
            const txt = (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g," ");
            return role + "::" + txt;
          });
        }
        """
        arr = page.evaluate(js)
        s = "\n".join(arr)
        return hashlib.sha1(s.encode()).hexdigest()[:12]
    except Exception:
        return "domhash_err"

def collect_console_and_failures(page):
    logs = []
    def on_console(msg):
        # In Playwright Python, type/text are properties
        if msg.type in {"error", "warning"}:
            logs.append({"type": msg.type, "text": (msg.text or "")[:400]})
    page.on("console", on_console)

    fails = []
    page.on("requestfailed", lambda r: fails.append({"url": r.url[:200], "failure": r.failure}))
    return logs, fails

def human_explore(app_url: str) -> Dict[str, Any]:
    trace_path = ARTIFACTS / "steps.jsonl"
    f = open(trace_path, "w", encoding="utf-8")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="msedge",
            headless=False,
            args=[f"--profile-directory={PROFILE_NAME}"],
        )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(15000)

        console_logs, network_failures = collect_console_and_failures(page)
        page.goto(app_url, wait_until="domcontentloaded")

        img_path, img_hash = screenshot_and_hash(page, "home")
        state0 = {
            "url": page.url,
            "title": page.title(),
            "dom_hash": dom_fingerprint(page),
            "ax": ax_summary(page)[:80],
            "screenshot": str(img_path),
            "img_hash": img_hash,
        }
        f.write(json.dumps({"type":"observation","stage":"start","data":state0}, ensure_ascii=False) + "\n")

        # BFS frontier
        q = deque()
        visited_states = set([state0["dom_hash"] + "|" + state0["url"]])
        q.append((0, None))

        steps = 0
        click_memory: Dict[str,int] = defaultdict(int)

        while q and steps < MAX_STEPS:
            depth, _ = q.popleft()
            if depth > MAX_DEPTH:
                continue

            # enumerate current page clickables
            cands = visible_clickables(page)
            for label, el in cands:
                if steps >= MAX_STEPS:
                    break
                if click_memory[label] >= 2:
                    continue
                click_memory[label] += 1

                before = {
                    "url": page.url,
                    "title": page.title(),
                    "dom_hash": dom_fingerprint(page),
                }

                try:
                    el.scroll_into_view_if_needed()
                    el.click(timeout=5000, trial=True)  # pre-flight
                    el.click(timeout=10000)
                except Exception as e:
                    f.write(json.dumps({"type":"action","label":label,"status":"failed","error":str(e)[:300]}, ensure_ascii=False) + "\n")
                    continue

                page.wait_for_timeout(300)
                img_path, img_hash = screenshot_and_hash(page, f"step{steps}")

                after = {
                    "url": page.url,
                    "title": page.title(),
                    "dom_hash": dom_fingerprint(page),
                    "ax": ax_summary(page)[:80],
                    "screenshot": str(img_path),
                    "img_hash": img_hash,
                }

                changed = (before["url"] != after["url"]) or (before["dom_hash"] != after["dom_hash"])
                f.write(json.dumps({
                    "type":"action","label":label,"status":"ok","changed":changed,
                    "before": before, "after": after
                }, ensure_ascii=False) + "\n")

                steps += 1
                key = after["dom_hash"] + "|" + after["url"]
                if changed and key not in visited_states:
                    visited_states.add(key)
                    q.append((depth+1, label))

        # final logs
        f.write(json.dumps({"type":"summary","console":console_logs[-50:], "failed_requests":network_failures[-50:]}, ensure_ascii=False) + "\n")
        f.close()
        ctx.close()

    return {"trace_file": str(trace_path), "screens_dir": str(IMG_DIR)}

if __name__ == "__main__":
    out = human_explore(APP_URL)
    print("[done]", out)
