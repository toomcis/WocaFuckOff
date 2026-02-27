#!/usr/bin/env python3
"""Startup helper: launch Chromium with remote debugging and autofill login.

Reads `config.toml` for `username`, `password` and `urlbase`, starts a
Chromium/Chrome binary with `--remote-debugging-port=9222`, then connects
using Playwright CDP to navigate to the site and fill `#login` and `#password`.
"""
import os
import time
import sys
import toml
import shutil
from playwright.sync_api import sync_playwright


CONFIG_FILE = "config.toml"


def load_config(path=CONFIG_FILE):
    if not os.path.exists(path):
        print(f"Config file not found: {path}")
        return {}
    return toml.load(path)


def main():
    cfg = load_config()
    username = cfg.get("username", "")
    password = cfg.get("password", "")
    urlbase = cfg.get("urlbase", "https://wocabee.app/app")

    if not username or not password:
        print("username or password missing in config.toml")
        sys.exit(1)

    def find_browser_binary():
        candidates = [
            "chromium",
            "chromium-browser",
            "google-chrome",
            "chrome",
        ]
        for name in candidates:
            path = shutil.which(name)
            if path:
                return path
        return None
    
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

    browser_bin = find_browser_binary()

    with sync_playwright() as p:
        launch_args = {"headless": False, "args": ["--no-sandbox"]}
        if browser_bin:
            launch_args["executable_path"] = browser_bin
            print("Using browser executable:", browser_bin)

        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as e:
            print("Failed to launch browser:", e)
            sys.exit(1)
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

        # Example: click the 0th class (first one)
        click_class_by_index(page, 0)

        while True:
            pass

        print("Credentials filled. Browser remains open for further steps.")


if __name__ == "__main__":
    main()