# WocaFuckOff

![logo](assets/logo.png)

**Project Overview**

- **Purpose:** Automated helper for Wocabee language practice using a browser CDP connection.
- **Main script:** [startup.py](startup.py) ! The script doesn't have a gui, if you want I made a [docker image](https://github.com/toomcis/WocaFuckOff-docker) for this project !
- **Main Solver script** [solver.py](solver.py)
- **Primary language focus:** Slovak (designed for Slovak → English), but the approach is language-agnostic in principle.

**Quick Notes**

- **AI-assisted:** This project was created with AI help and may contain bugs or imperfect heuristics. Don't be scared of making an [issue](https://github.com/toomcis/WocaFuckOff/issues) and reposting any bugs or imperfections!

**Requirements**

- **Python:** 3.9+ recommended
- **Libraries:** See `requirements.txt` (if present). At minimum the script uses `playwright`, `requests`, `toml`.

Install basics:

```bash
python -m pip install -r requirements.txt
python -m playwright install
```

**Configuration**

- Edit [config.toml](config.toml) or set environment variables. Important settings:
  - `urlbase` — base URL to target (default: https://wocabee.app/app)
  - `debug_port` — CDP endpoint, e.g. `http://localhost:9222`
  - `wordlist_file` / `picture_file` — JSON files used for mappings
  - `placeholder_words` — List of words to ignore
  - `class_index` / `package_index` — Indexes to select class and package on startup
  - `addon_points` — Amount of points you want to get (Not the final value, but rather the addition)
  - `milestone_reminder` — Amount points needed to get a milestone (if set to 1000, every 1000th point (4000 then 5000 then 6000 ext.))) will send a notification
  - `double_points` — A boolean value, set true if you want to play double points mode
  - `username` / `password` — Username and password for wocabee account
  - `ntfy_server`, `ntfy_topic`, `ntfy_token` — optional notifications

Example config snippet (see [config.toml](config.toml) for the full file):

```toml
urlbase = "https://wocabee.app/app"
debug_port = "http://localhost:9222"
wordlist_file = "wordlist.json"
picture_file = "picturelist.json"
placeholder_words = ["", "translate", "check"]
class_index = 0
package_index = 0
addon_points = 1000
milestone_reminder = 100
double_points = false
username = "coolUsername"
password = "coolPassword"
ntfy_server = "https://example.ntfy.server"
ntfy_topic = "wocabee-bot"
ntfy_token = "secret_token_here"
```

**Usage**

- There are 2 ways to use this script, either using the [docker image](https://github.com/toomcis/WocaFuckOff-docker) or using your personal computer:

**Docker**

- Follow the instructions on the [WocaFuckOff-docker](https://github.com/toomcis/WocaFuckOff-docker) repository page

**Local**

- There is a requirement of a chromium based browser, you can start it with your own chromium based browser or you can install a comparible one using playwright ! Not recommended !

```bash
python -m playwright install-depo

# If you use your own chromium browser, you can skip the startup.py script and use solver.py directly

python solver.py
```

- To start it manually (With chromium already opened) you can do this specific command:

```bash
# launch chrome/chromium with remote debugging port 9222
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/wocabee-profile
```

- If you do not have a chromium currently opened sucesfully, the script will automatically open it with the correct arguments
- Running the bot:
- If you decide to use the startup.py script, you need to insert username and password into the [config.toml](config.toml) file

```bash
# explicit URL
python startup.py --url https://wocabee.app/

# or rely on config.toml / environment variables
python solver.py
```

The bot connects to the running browser via the `debug_port` CDP endpoint and attaches to a tab whose URL contains `urlbase`.

**How it works (short)**

- The script attaches to a browser context via CDP, finds the tab with the target site, and automates UI actions with Playwright.
- Mappings for words and pictures are stored in JSON files (`wordlist.json`, `picturelist.json`). Unknown items may prompt for manual input once and get saved.

**Limitations & Caveats**

- The project was generated/assisted by AI — expect brittle behavior, race conditions, and imperfect selectors.
- It assumes specific DOM IDs and classes on the target site; UI changes will break handlers.
- Designed and tested against Slovak→English examples; other languages may require adjusting the translation fallback settings and the `source` language in the translator calls.
- Use responsibly: automated interaction with websites may violate terms of service.

**Troubleshooting**

- If the script cannot attach: verify the browser is running with the correct `--remote-debugging-port` and that `debug_port` points to the CDP URL.
- If handlers fail to click elements, the site DOM may have changed; open [solver.py](solver.py) and inspect the locator logic.
- Network/translation failures fallback to manual prompts — check `wordlist.json` for saved entries.

**License & Attribution**

- This project uses the [MIT license](LICENSE)
