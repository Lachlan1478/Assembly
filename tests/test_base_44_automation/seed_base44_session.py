
import os
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("BASE44_URL", "https://app.base44.com").rstrip("/")
CHANNEL = os.getenv("BASE44_BROWSER_CHANNEL", "msedge")          # "msedge" or "chrome"
USER_DATA_DIR = os.getenv("BASE44_USER_DATA_DIR", r"C:\Users\User\EdgePW")
PROFILE_DIR = os.getenv("BASE44_PROFILE_DIR", "Default")

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print(f"[i] Launching persistent context")
    print(f"    channel       : {CHANNEL}")
    print(f"    user_data_dir : {USER_DATA_DIR}")
    print(f"    profile       : {PROFILE_DIR}")
    with sync_playwright() as p:
        # Important: this reuses the exact profile directory you seeded manually
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel=CHANNEL,           # "msedge" or "chrome"
            headless=False,            # keep headful for visibility
            args=[f"--profile-directory={PROFILE_DIR}"],
        )
        ctx.set_default_timeout(15000)

        # Reuse the first page if the browser opens one, else create a new one
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print(f"[i] Navigating to {BASE_URL} ...")
        page.goto(BASE_URL, wait_until="domcontentloaded")

        # Heuristic: try to decide if you're logged in
        # (Adjust selectors based on Base44’s UI; these are intentionally loose.)
        logged_in = True
        try:
            # If a “Log in” button or similar is visible, we’re probably *not* logged in
            page.wait_for_selector("text=Log in, text=Sign in, button:has-text('Log in')", timeout=3000)
            logged_in = False
        except Exception:
            # No login prompt found quickly — likely logged in
            logged_in = True

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot = ARTIFACT_DIR / f"base44_{'in' if logged_in else 'out'}_{ts}.png"
        try:
            page.screenshot(path=str(shot), full_page=True)
            print(f"[i] Screenshot saved: {shot}")
        except Exception as e:
            print(f"[!] Could not take screenshot: {e}")

        if logged_in:
            print("[✓] Looks like you are already logged into Base44 with this profile.")
        else:
            print("[!] It looks like you’re NOT logged in. If that’s wrong, ignore.")
            print("    If you are not logged in, do the manual bootstrap again:")
            print('    1) Close Edge completely')
            print('    2) Run: & "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" '
                  '--user-data-dir="C:\\Users\\User\\EdgePW" --profile-directory="Default"')
            print("    3) Log in to Base44 in that window, then close it and rerun this script.")

        print("\n[i] Keeping the browser open so you can confirm things. Close the window to exit.")
        try:
            # Keep the process alive until the window closes
            ctx.on("close", lambda *_: None)
            for _ in iter(int, 1):
                if not ctx.pages:
                    break
                page.wait_for_timeout(5000)
        finally:
            try:
                ctx.close()
            except Exception:
                pass

if __name__ == "__main__":
    # Helpful preflight messages
    if not Path(USER_DATA_DIR).exists():
        print(f"[!] WARNING: user_data_dir does not exist yet: {USER_DATA_DIR}")
        print("    If you haven’t seeded it, do the manual step first:")
        print('    & "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" '
              '--user-data-dir="C:\\Users\\User\\EdgePW" --profile-directory="Default"')
        print("    Then log into Base44 and close the window.")
    main()
