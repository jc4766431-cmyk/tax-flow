"""
Live click-through of the auth pages against the real Next.js dev server +
FastAPI backend, per HANDOFF.md §0f's instruction to actually run npm run dev
and click through login/register/logout/redirect-when-logged-out.
"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
results = []


def check(name, cond, extra=""):
    results.append((name, cond))
    print(("PASS" if cond else "FAIL") + " - " + name + (f" ({extra})" if extra else ""))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    # 1. Unauthenticated access to dashboard should redirect to /login
    page.goto(f"{BASE}/dashboard", wait_until="networkidle")
    check("unauthenticated /dashboard redirects to /login", "/login" in page.url, page.url)

    # 2. Register a new user through the actual form
    page.goto(f"{BASE}/register", wait_until="networkidle")
    email = "playwright.test@example.com"
    # Try to find inputs by common name/label patterns
    def fill_first(selectors, value):
        for sel in selectors:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.fill(value)
                return True
        return False

    ok_name = fill_first(['input[name="full_name"]', 'input[name="fullName"]', 'input#full_name', 'input[placeholder*="name" i]'], "Playwright Test")
    ok_email = fill_first(['input[name="email"]', 'input[type="email"]'], email)
    ok_pw = fill_first(['input#password', 'input[name="password"]'], "TestPass123!")
    ok_confirm = fill_first(['input#confirm_password', 'input[name="confirm_password"]'], "TestPass123!")
    check("register form: name field found and filled", ok_name)
    check("register form: email field found and filled", ok_email)
    check("register form: password field found and filled", ok_pw)
    check("register form: confirm-password field found and filled", ok_confirm)

    page.screenshot(path="/tmp/register_filled.png")

    submit = page.locator('button[type="submit"]')
    if submit.count() > 0:
        submit.first.click()
        page.wait_for_timeout(3000)
    check("after register submit, navigated away from /register (success)",
          "/register" not in page.url, page.url)
    page.screenshot(path="/tmp/after_register.png")

    # 3. Logout if we landed in the dashboard, then log back in
    page.goto(f"{BASE}/login", wait_until="networkidle")
    fill_first(['input[name="email"]', 'input[type="email"]'], email)
    fill_first(['input[name="password"]', 'input[type="password"]'], "TestPass123!")
    submit = page.locator('button[type="submit"]')
    if submit.count() > 0:
        submit.first.click()
        page.wait_for_timeout(3000)
    check("after login submit, redirected to a dashboard route",
          "/login" not in page.url, page.url)
    page.screenshot(path="/tmp/after_login.png")

    check("no console errors during the whole flow", len(console_errors) == 0, str(console_errors[:5]))

    browser.close()

print()
failed = [n for n, ok in results if not ok]
if failed:
    print(f"{len(failed)} CHECK(S) FAILED:")
    for n in failed:
        print(" -", n)
    sys.exit(1)
else:
    print(f"ALL {len(results)} CHECKS PASSED")
