#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time
import random
import requests
import unicodedata
import json
import os
import traceback
import toml
import argparse

# ----------------- CLI -----------------
parser = argparse.ArgumentParser()
parser.add_argument("--url", help="Target URL")
args = parser.parse_args()

# ----------------- Config file -----------------
config_file = "config.toml"
config = toml.load(config_file) if os.path.exists(config_file) else {}

# ----------------- Variables -----------------
URLBASE = args.url or os.environ.get("URLBASE") or config.get("urlbase", "wocabee.app/app")
# Ensure URL starts with http:// or https://
if not URLBASE.startswith(("http://", "https://")):
    URLBASE = "https://" + URLBASE

# CDP debug port/url used to connect to an existing Chromium/Edge instance.  
# Before running the bot you must start your browser with something like:
#   chrome --remote-debugging-port=9222
# or point DEBUG_PORT to a running instance.  The script now normalizes
# simple port values and will fall back to launching its own browser when
# connection is refused.
DEBUG_PORT = os.environ.get("DEBUG_PORT") or config.get("debug_port", "http://127.0.0.1:9222")
# some users may just provide a port number (e.g. "9222"), so normalize to a full URL
if DEBUG_PORT and DEBUG_PORT.isdigit():
    DEBUG_PORT = f"http://127.0.0.1:{DEBUG_PORT}"

WORDLIST_FILE = os.environ.get("WORDLIST_FILE") or config.get("wordlist_file", "wordlist.json")
PICTURE_FILE = os.environ.get("PICTURE_FILE") or config.get("picture_file", "picturelist.json")

addon_points = int(os.environ.get("ADDON_POINTS") or config.get("addon_points", 0))
milestone_reminder = int(os.environ.get("MILESTONE_REMINDER") or config.get("milestone_reminder", 1000))

PLACEHOLDER_WORDS = {
    w.strip() for w in (
        os.environ.get("PLACEHOLDER_WORDS")
        or ",".join(config.get("placeholder_words", ["", "translate", "check"]))
    ).split(",")
}
NTFY_SERVER = (os.environ.get("NTFY_SERVER") or config.get("ntfy_server") or "").strip() or None
NTFY_TOPIC  = (os.environ.get("NTFY_TOPIC")  or config.get("ntfy_topic")  or "").strip() or None
NTFY_TOKEN  = (os.environ.get("NTFY_TOKEN")  or config.get("ntfy_token")  or "").strip() or None

if not URLBASE or not DEBUG_PORT:
    print("Error: URLBASE and DEBUG_PORT must be set via environment variables, config.toml, or CLI arguments.")
    exit(1)

# ----------- NTFY ERROR FUNCTION ------------

def notify_ntfy(title: str, message: str):
    if NTFY_SERVER and NTFY_TOPIC:
        try:
            url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
            data = message.encode("utf-8")
            headers = {
                "Title": title,
            }
            if NTFY_TOKEN:
                headers["Authorization"] = f"Bearer {NTFY_TOKEN}"
            response = requests.post(url, data=data, headers=headers, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print("Failed to send NTFY notification:", e)

# ---------------- LOAD DATA ----------------

notify_ntfy("Wocabee Bot Started", f"The bot has been started and is connecting into the browser, estimated time until finished = {addon_points * 1.75} seconds")

if os.path.exists(WORDLIST_FILE):
    with open(WORDLIST_FILE, "r", encoding="utf-8") as f:
        WORD_TABLE = json.load(f)
else:
    WORD_TABLE = {
        "pracovny postup": "technique",
        "viditelny": "visible",
        "vazny": "serious",
        "seriozny": "serious",
        "vazny, seriozny": "serious",
        "vedecke laboratorium": "science laboratory",
        "krok": "step",
        "vyznam, zmysel": "significance",
        "burka": "storm",
    }
    with open(WORDLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(WORD_TABLE, f, ensure_ascii=False, indent=2)

if os.path.exists(PICTURE_FILE):
    with open(PICTURE_FILE, "r", encoding="utf-8") as f:
        PICTURE_MAP = json.load(f)
else:
    PICTURE_MAP = {}

def save_picture_map():
    with open(PICTURE_FILE, "w", encoding="utf-8") as f:
        json.dump(PICTURE_MAP, f, ensure_ascii=False, indent=2)

# ---------------- HELPERS ----------------

def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def normalize(text: str) -> str:
    text = text.strip().lower()
    text = strip_accents(text)
    return text

def find_target_page(context):
    for page in context.pages:
        if URLBASE in page.url:
            return page
    return None

def get_answer_auto_update(word: str) -> str:
    normalized_word = normalize(word)

    # Direct match
    answer = WORD_TABLE.get(normalized_word)
    if answer:
        return answer

    # Reverse lookup
    for sk, en in WORD_TABLE.items():
        if normalize(en) == normalized_word:
            return sk

    # Multi-word
    if "," in normalized_word:
        for w in [w.strip() for w in normalized_word.split(",")]:
            answer = WORD_TABLE.get(w)
            if answer:
                return answer
            for sk, en in WORD_TABLE.items():
                if normalize(en) == w:
                    return sk

    # Manual fallback
    answer = input(f"Enter translation for unknown word '{word}': ").strip()
    if answer:
        WORD_TABLE[normalized_word] = answer
        with open(WORDLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(WORD_TABLE, f, ensure_ascii=False, indent=2)
        print(f"New word added: '{word}' -> '{answer}'")
    return answer

def human_click(page, locator_or_handle, min_delay=0.05, max_delay=0.2):
    time.sleep(random.uniform(min_delay, max_delay))
    if hasattr(locator_or_handle, "element_handle"):
        handle = locator_or_handle.element_handle()
    else:
        handle = locator_or_handle
    if handle:
        page.evaluate("(el) => el.click()", handle)

# ---------------- Picture Mapping ----------------
PICTURE_FILE = "picturelist.json"

# load picture map
if os.path.exists(PICTURE_FILE):
    with open(PICTURE_FILE, "r", encoding="utf-8") as f:
        PICTURE_MAP = json.load(f)
else:
    PICTURE_MAP = {}

def save_picture_map():
    with open(PICTURE_FILE, "w", encoding="utf-8") as f:
        json.dump(PICTURE_MAP, f, ensure_ascii=False, indent=2)

def handle_choose_picture(page):
    container = page.locator("#choosePicture")
    if container.count() == 0 or not container.is_visible():
        return False

    # get the target word from the green button
    target_word_raw = page.locator("#choosePictureWord").inner_text()
    target_word = normalize(target_word_raw)

    # load picture table
    PICTURELIST_FILE = "picturelist.json"
    if os.path.exists(PICTURELIST_FILE):
        with open(PICTURELIST_FILE, "r", encoding="utf-8") as f:
            PICTURE_TABLE = json.load(f)
    else:
        PICTURE_TABLE = {}

    # figure out the correct src for this word
    correct_src = None
    for src, word in PICTURE_TABLE.items():
        if normalize(word) == target_word:
            correct_src = src
            break
    if not correct_src:
        print(f"ChoosePicture: no mapping found for '{target_word}'")
        return False

    # slick container
    slick_container = page.locator("#word-img-container")
    if slick_container.count() == 0:
        return False

    # prev/next buttons
    btn_prev = slick_container.locator(".slick-prev")
    btn_next = slick_container.locator(".slick-next")

    # loop until the correct image is visible
    max_attempts = 10
    for _ in range(max_attempts):
        visible_img = slick_container.locator(".slick-slide.slick-current img.picture")
        if visible_img.count() == 0:
            break
        visible_src = visible_img.get_attribute("src")
        if visible_src == correct_src:
            # double click
            el_handle = visible_img.element_handle()
            if el_handle:
                page.evaluate("(el) => el.click()", el_handle)
                time.sleep(0.05)
                page.evaluate("(el) => el.click()", el_handle)
                print(f"ChoosePicture: clicked '{target_word}'")
                return True
        else:
            # click next if possible, else prev
            if btn_next.is_enabled():
                btn_next.click()
            elif btn_prev.is_enabled():
                btn_prev.click()
            else:
                print("ChoosePicture: cannot navigate carousel")
                break
            time.sleep(random.uniform(0.2, 0.4))

    print(f"ChoosePicture: could not find correct picture for '{target_word}'")
    return False

def handle_describe_picture(page):
    container = page.locator("#describePicture")
    if container.count() == 0 or not container.is_visible():
        return False

    img_elem = page.locator("#describePictureImg")
    input_elem = page.locator("#describePictureAnswer")
    submit_elem = page.locator("#describePictureSubmitBtn")

    if img_elem.count() == 0 or input_elem.count() == 0 or submit_elem.count() == 0:
        return False

    src = img_elem.get_attribute("src")
    answer = PICTURE_MAP.get(src)
    if not answer:
        # Ask manually once and store for future runs
        answer = input(f"Enter English word for image {src}: ").strip()
        if answer:
            PICTURE_MAP[src] = answer
            save_picture_map()

    # Type answer and submit
    input_elem.click()
    page.keyboard.type(answer, delay=random.randint(60, 120))
    submit_elem.click()

    print("DescribePicture answered:", answer)
    return True

# ---------------- One-Out-Of-Many Handler ----------------

def handle_translate_falling_word(page):
    container = page.locator("#translateFallingWord")
    if container.count() == 0 or not container.is_visible():
        return False

    word_elem = page.locator("#tfw_word")
    input_elem = page.locator("#translateFallingWordAnswer")
    submit_elem = page.locator("#translateFallingWordSubmitBtn")

    if word_elem.count() == 0 or input_elem.count() == 0 or submit_elem.count() == 0:
        return False

    word_raw = word_elem.inner_text()
    word = normalize(word_raw)

    if word in PLACEHOLDER_WORDS:
        return False

    answer = get_answer_auto_update(word)
    if not answer:
        print(f"TranslateFallingWord: no answer found for '{word_raw}'")
        return False

    input_elem.click()
    page.keyboard.type(answer, delay=random.randint(60, 120))

    # wait until button is enabled
    max_wait = 3.0  # seconds
    elapsed = 0
    while not submit_elem.is_enabled() and elapsed < max_wait:
        time.sleep(0.05)
        elapsed += 0.05

    submit_elem.click()
    print(f"TranslateFallingWord answered: {answer}")
    return True

def handle_choose_word(page):
    container = page.locator("#chooseWord")
    if container.count() == 0 or not container.is_visible():
        return False

    question_elem = page.locator("#ch_word")
    answers = page.locator(".chooseWordAnswer")

    if question_elem.count() == 0 or answers.count() == 0:
        return False

    question_raw = question_elem.inner_text()
    question = normalize(question_raw)

    print("ChooseWord Question:", question_raw)

    # get expected answer (auto handles reverse)
    raw_answer = get_answer_auto_update(question)
    if not raw_answer:
        print("ChooseWord: no known answer")
        return False

    # split possible answers (comma-safe)
    expected_parts = [normalize(p) for p in raw_answer.split(",")]

    clicked = False

    for i in range(answers.count()):
        btn = answers.nth(i)
        btn_text_raw = btn.inner_text()
        btn_text = normalize(btn_text_raw)

        for expected in expected_parts:
            if expected in btn_text or btn_text in expected:
                time.sleep(random.uniform(0.1, 0.3))
                handle = btn.element_handle()
                if handle:
                    page.evaluate("(el) => el.click()", handle)
                    print("ChooseWord: clicked", btn_text_raw)
                    clicked = True
                    break

        if clicked:
            break

    if not clicked:
        print("ChooseWord: answer not present in choices")
        time.sleep(0.5)
        return False

    return True

def handle_pexeso(page):
    container = page.locator("#pexeso")
    if container.count() == 0 or not container.is_visible():
        return False

    fronts = page.locator(".pexesoCardWrapper .pexesoFront")
    if fronts.count() == 0:
        return False

    # map w_id to list of front elements
    card_map = {}
    for i in range(fronts.count()):
        wrapper = fronts.nth(i).locator("..")  # parent wrapper
        w_id = wrapper.get_attribute("w_id")
        if w_id not in card_map:
            card_map[w_id] = []
        card_map[w_id].append(fronts.nth(i))

    # iterate over w_id groups and double-click each pair
    for w_id, cards in card_map.items():
        if len(cards) < 2:
            continue  # can't pair if less than 2
        first_card, second_card = cards[:2]  # take first two

        for card in [first_card, second_card]:
            handle = card.element_handle()
            if handle:
                # perform two real clicks
                page.evaluate("(el) => el.click()", handle)
                time.sleep(random.uniform(0.05, 0.15))
                page.evaluate("(el) => el.click()", handle)
                time.sleep(random.uniform(0.05, 0.2))

    return True

def handle_complete_word(page):
    container = page.locator("#completeWord")
    if container.count() == 0 or not container.is_visible():
        return False

    question_elem = page.locator("#completeWordQuestion")
    answer_elem = page.locator("#completeWordAnswer")
    submit_elem = page.locator("#completeWordSubmitBtn")
    if question_elem.count() == 0 or answer_elem.count() == 0 or submit_elem.count() == 0:
        return False

    word_raw = question_elem.inner_text()
    word = normalize(word_raw)  # normalized lowercase
    current_answer_raw = answer_elem.inner_text()
    current_answer_norm = normalize(current_answer_raw)

    if word in PLACEHOLDER_WORDS or not word:
        return False

    # get the "correct target word" using bidirectional lookup
    target_answer = get_answer_auto_update(word)
    if not target_answer:
        print(f"CompleteWord: no answer found for '{word_raw}'")
        return False

    target_answer_norm = normalize(target_answer)

    # if current answer matches target, nothing to do
    if current_answer_norm == target_answer_norm:
        if submit_elem.is_visible() and submit_elem.is_enabled():
            submit_handle = submit_elem.element_handle()
            if submit_handle:
                print("Clicking CompleteWord submit button (already complete)")
                page.evaluate("(el) => el.click()", submit_handle)
        return True

    # find missing letters
    missing_letters = []
    for w_char, c_char in zip(target_answer_norm, current_answer_norm.ljust(len(target_answer_norm), "_")):
        if w_char != c_char:
            missing_letters.append(w_char)

    print("CompleteWord Question:", word_raw)
    print("Target answer:", target_answer)
    print("Missing letters:", missing_letters)

    # click letters
    letter_buttons = page.locator("#characters .char")
    for missing in missing_letters:
        for i in range(letter_buttons.count()):
            btn = letter_buttons.nth(i)
            letter_text_raw = btn.inner_text()
            if letter_text_raw.isupper():       # skip uppercase letters
                continue
            letter_text = normalize(letter_text_raw)
            if letter_text == missing:
                time.sleep(random.uniform(0.05, 0.2))
                element_handle = btn.element_handle()
                if element_handle:
                    page.evaluate("(el) => el.click()", element_handle)
                    break

    # click submit if visible and enabled
    if submit_elem.is_visible() and submit_elem.is_enabled():
        time.sleep(random.uniform(0.1, 0.3))
        submit_handle = submit_elem.element_handle()
        if submit_handle:
            print("Clicking CompleteWord submit button")
            page.evaluate("(el) => el.click()", submit_handle)
    else:
        print("Submit button not ready yet, skipping for now")

    return True

def handle_one_out_of_many(page):
    container = page.locator("#oneOutOfMany")
    if container.count() == 0 or not container.is_visible():
        return False  # event not active

    question_elem = page.locator("#oneOutOfManyQuestionWord")
    if question_elem.count() == 0:
        return False

    question_raw = question_elem.inner_text()
    question = normalize(question_raw)
    if question in PLACEHOLDER_WORDS:
        return False

    answer = get_answer_auto_update(question)
    if not answer:
        print("OneOutOfMany: answer not found")
        return False

    choices = page.locator(".oneOutOfManyWord")
    for i in range(choices.count()):
        choice_elem = choices.nth(i)
        if not choice_elem.is_visible():
            continue
        choice_text = normalize(choice_elem.inner_text())
        if choice_text == answer:
            time.sleep(random.uniform(0.05, 0.2))
            print("OneOutOfMany answered:", choice_text)
            choice_elem.click()
            return True

    print("OneOutOfMany: answer not present in choices")
    return False

def handle_find_pair(page):
    container = page.locator("#findPair")
    if container.count() == 0 or not container.is_visible():
        return False

    questions = page.locator("#q_words .fp_q")
    answers = page.locator("#a_words .fp_a")
    if questions.count() == 0 or answers.count() == 0:
        return False

    # map questions by text for easy lookup
    question_map = {}
    for i in range(questions.count()):
        q_elem = questions.nth(i)
        q_text = normalize(q_elem.inner_text())
        question_map[q_text] = q_elem

    for orig_word, correct_answer in WORD_TABLE.items():
        q_elem = question_map.get(orig_word)
        if not q_elem:
            continue

        # click question button
        q_handle = q_elem.element_handle()
        if q_handle:
            page.evaluate("(el) => el.click()", q_handle)
            time.sleep(random.uniform(0.05, 0.2))

        # click corresponding answer button
        found = False
        for j in range(answers.count()):
            a_elem = answers.nth(j)
            a_text = normalize(a_elem.inner_text())
            is_disabled = a_elem.get_attribute("disabled")
            if a_text == correct_answer and not is_disabled:
                a_handle = a_elem.element_handle()
                if a_handle:
                    page.evaluate("(el) => el.click()", a_handle)
                    found = True
                    break
        if not found:
            print(f"FindPair: answer '{correct_answer}' not present or disabled for '{orig_word}'")

    return True

# ------------- Main Loop -------------

StopBot = False

with sync_playwright() as p:
    try:
        # try to attach to an existing browser via CDP (remote debugging)
        try:
            browser = p.chromium.connect_over_cdp(DEBUG_PORT)
            context = browser.contexts[0]
            page = find_target_page(context)
            if not page:
                raise RuntimeError(f"No open tab found containing '{URLBASE}'")
            print("Attached to tab:", page.url)
        except Exception as e:
            # connection refused / no browser running - fall back to launching a fresh one
            print("CDP connection failed (", e, "), launching new browser instance")
            browser = p.chromium.launch(
                headless=False,
                args=["--no-sandbox","--remote-debugging-port=9222"]
            )
            context = browser.new_context()
            page = context.new_page()
            # if a URL was provided, navigate there so the bot has a page to work with
            if URLBASE:
                # ensure we have a proper scheme
                if not URLBASE.startswith(("http://", "https://")):
                    page.goto("https://" + URLBASE)
                else:
                    page.goto(URLBASE)
            print("Opened new browser, current URL:", page.url)
        
        original_points = int(page.locator("#WocaPoints").inner_text().strip())
        last_milestone = original_points  # store the last milestone notified

        one_time = time.time()

        while True:
            try:
                # 1. Handle one-out-of-many
                if handle_one_out_of_many(page):
                    page.wait_for_timeout(400)
                    continue
                
                if handle_translate_falling_word(page):
                    page.wait_for_timeout(400)
                    continue

                if handle_choose_picture(page):
                    page.wait_for_timeout(400)
                    continue

                if handle_describe_picture(page):
                    page.wait_for_timeout(400)
                    continue

                if handle_pexeso(page):
                    page.wait_for_timeout(400)
                    continue

                if handle_complete_word(page):
                    page.wait_for_timeout(400)
                    continue

                if handle_choose_word(page):
                    page.wait_for_timeout(400)
                    continue

                # 2. SOUND / TRANSCRIBE
                transcribe = page.locator("#transcribe")
                if transcribe.count() > 0 and transcribe.is_visible():
                    print("Skipping transcribe")
                    page.locator("#transcribeSkipBtn").click()
                    page.wait_for_timeout(300)
                    continue

                if handle_find_pair(page):
                    page.wait_for_timeout(400)
                    continue
                
                points_locator = page.locator("#WocaPoints")

                if points_locator.count() > 0 and points_locator.is_visible():
                    points = int(points_locator.inner_text().strip())
                else:
                    print("#WocaPoints not present — probably returned to standard view")
                    notify_ntfy("Wocabee Bot Finished", "Bot has stopped because it seems to have returned to standard view. The browser will now close.")
                    notify_ntfy("Wocabee Bot Final Report", f"Final points: {original_points + addon_points} (original: {original_points}, addon: {addon_points}) | Total time running: {int(time.time() - one_time)} seconds")
                    exit(0)

                # inside your loop, after updating `points`:
                while points >= last_milestone + milestone_reminder:
                    last_milestone += milestone_reminder
                    notify_ntfy(
                        "Wocabee Bot Progress Report",
                        f"Current points: {points} (original: {original_points}, target: {original_points + addon_points})"
                    )
                
                if points >= original_points + addon_points:
                    notify_ntfy("Wocabee Bot reached the target", f"Wocabee Bot has reached the target of {points} points (original: {original_points}, addon: {addon_points}), stopping and saving!")
                    StopBot = True
                
                if StopBot:
                    page.wait_for_selector("#backBtn", timeout=5000)
                    page.click("#backBtn")
                    try:
                        page.wait_for_selector("#standardView", state="visible", timeout=15000)
                        notify_ntfy("Wocabee Bot Finished", "Bot has stopped and returned to standard view. The browser will now safely close.")
                        break
                    except Exception as e:
                        notify_ntfy("Wocabee Bot Error", f"Failed to load #standardView after clicking back. Exiting anyway. Error: {e}")
                        break
                
                # 3. TRANSLATE INPUT
                question_span = page.locator("#q_word")
                if question_span.count() > 0 and question_span.is_visible():
                    word_raw = question_span.inner_text()
                    word = normalize(word_raw)
                    if word in PLACEHOLDER_WORDS:
                        time.sleep(0.1)
                        continue
                    print("TranslateWord answered:", word_raw)
                    answer = get_answer_auto_update(word)
                    if answer:
                        answer_input = page.locator("#translateWordAnswer")
                        answer_input.click()
                        page.keyboard.type(answer, delay=random.randint(60, 120))
                        page.keyboard.press("Enter")
                    page.wait_for_timeout(400)
                    continue

                time.sleep(0.1)
                
                

            except Exception as e_inner:
                tb = traceback.format_exc()
                print("Runtime error:", tb)
                notify_ntfy("Wocabee Bot Runtime Error", tb)
                time.sleep(1)

    except Exception as e_outer:
        tb = traceback.format_exc()
        print("Startup/Connection error:", tb)
        notify_ntfy("Wocabee Bot Startup Error", tb)
