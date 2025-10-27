# Base44 Persistent Login Setup (Chrome)

## Step 1. Create a seeded Chrome profile
Run this command in **PowerShell** (close all Chrome windows first):

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --user-data-dir="C:\Users\User\EdgePW" `
  --profile-directory="Default"
```

This opens Chrome with a **separate profile folder** (`ChromePW`).

## Step 2. Log into Base44
- In that Edge window, go to [https://app.base44.com](https://app.base44.com).
- Log in with your account as normal.
- Once logged in, close the window.

Your Base44 login cookies/session are now saved in `C:\Users\User\EdgePW`.

## Step 3. Run the seed script to test
Run:

```powershell
python seed_base44_session.py
```

What this does:
- Launches Playwright with the `EdgePW` profile.
- Opens Base44 automatically **already logged in**.
- Takes a screenshot for confirmation.

---

✅ At this point your profile is set up and working.  
You can now build further automation scripts on top of this persistent session.
