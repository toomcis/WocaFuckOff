#!/usr/bin/env python3
import os
import sys
import toml
from playwright.sync_api import sync_playwright
import subprocess

CONFIG_FILE = "config.toml"

def load_config(path=CONFIG_FILE):
    if not os.path.exists(path):
        print(f"Config file not found: {path}")
        return {}
    return toml.load(path)


def main():
    cfg = load_config()
    headless = cfg.get("headless", False)
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    double_points = cfg.get("double_points", False)
    class_index = cfg.get("class_index", 0)
    package_index = cfg.get("package_index", 0)
    urlbase = cfg.get("urlbase", "https://wocabee.app/app")

    if not username or not password:
        print("username or password missing in config.toml")
        sys.exit(1)

    def enable_double_points(page):
        try:
            # Wait for wrapper instead of input visibility
            page.wait_for_selector("#toggleWrapper", timeout=5000)

            toggle = page.locator("#levelToggle")

            # Check state directly (hidden is fine)
            is_checked = toggle.is_checked()

            if not is_checked:
                # Click the visible slider, not the hidden input
                page.locator("#toggleWrapper .slider").click()
                print("Double points enabled.")
            else:
                print("Double points already enabled.")

            return True

        except Exception as e:
            print("Failed to enable double points:", e)
            return False
    
    def click_package_by_index(page, index: int):
        page.wait_for_selector("tr.pTableRow", timeout=10000)

        packages = page.locator("tr.pTableRow")

        count = packages.count()
        if index < 0 or index >= count:
            print(f"Package index {index} out of range. Found {count} packages.")
            return False

        print(f"Clicking package {index}")

        # Click practice button inside that row
        packages.nth(index).locator("a .btn-primary").click()

        page.wait_for_load_state("networkidle")
        return True
    
    def click_class_by_index(page, index: int):
        try:
            # Wait for the class list to appear
            page.wait_for_selector("#listOfClasses a", timeout=10000)

            # Get all class links
            class_links = page.query_selector_all("#listOfClasses a")

            if not class_links:
                print("No classes found.")
                return

            if index < 0 or index >= len(class_links):
                print(f"Index {index} out of range. Found {len(class_links)} classes.")
                return

            print(f"Clicking class at index {index}")
            class_links[index].click()

        except Exception as e:
            print("Error clicking class:", e)
    
    p = sync_playwright().start()

    browser = p.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--remote-debugging-port=9222"
        ]
    )

    context = browser.new_context()
    page = context.new_page()

    # navigate to target
    if not urlbase.startswith(("http://", "https://")):
        target = "https://" + urlbase
    else:
        target = urlbase

    page.goto(target)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    print("Opened page:", page.url)

    # fill login fields
    try:
        page.wait_for_selector("#login", timeout=5000)
        page.fill("#login", username)
        print("Filled #login")
    except Exception:
        print("Login input (#login) not found")

    try:
        page.wait_for_selector("#password", timeout=5000)
        page.fill("#password", password)
        print("Filled #password")
        # submit (press Enter)
        page.press("#password", "Enter")
        print("Submitted credentials")
    except Exception:
        print("Password input (#password) not found")
    
            # Wait for navigation after login
    page.wait_for_load_state("networkidle")

    click_class_by_index(page, class_index)
    
    click_package_by_index(page, package_index)
    
    if double_points:
        enable_double_points(page)
    
    solver_proc = subprocess.Popen(["python", "solver.py"])

    try:
        solver_proc.wait()   # Wait until solver exits
    finally:
        print("Solver exited. Cleaning up...")

        browser.close()
        p.stop()


if __name__ == "__main__":
    main()