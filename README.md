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

- **WocaBee:** Please make sure that you have the package already completed before you farm it, the script is supposed to do the tedious grind currently
- **Python:** 3.9+ recommended
- **Libraries:** See `requirements.txt` (if present). At minimum the script uses `playwright`, `requests`, `toml`.
- **Playwright:** Please use the `playwright install-deps` and `playwright install` command to fully install all additional dependencies

Installing dependencies:

```bash
# Installing requirements and dependencies
python -m pip install -r requirements.txt
python -m playwright install-deps
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
  - `headless` — This variable tells the program if you want to launch a window as well or just farm it blindly, its recommended to set headless if you want to use it in the background without hogging resources
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
headless = true
double_points = false
username = "coolUsername"
password = "coolPassword"
ntfy_server = "https://example.ntfy.server"
ntfy_topic = "wocabee-bot"
ntfy_token = "secret_token_here"
```

**Usage**

- There are 2 ways to use the script, you can either use the script or the [docker](https://github.com/toomcis/WocaFuckOff-docker)

**Docker**

- Follow the instructions on the [WocaFuckOff-docker](https://github.com/toomcis/WocaFuckOff-docker) repository page

**Local**

- You need to use a chromium based browser, doing the before mentioned `playwright install-deps` should download one that works ! NOTE: Please don't use your own chromium based browser, It's not really tested properly 
- The startup script will automatically open the chromium browser with the correct arguments
- Running the bot:
- While using the startup.py script, you need to insert username and password into the [config.toml](config.toml) file

```bash
# You rely on config.toml for all variables
python startup.py
```

**How it works (short)**

- The startup.py script opens a chromium browser with specific arguments and automatically navigates to a specific class and package you want to farm
- The solver.py script automatically starts and attaches to the browser via CDP, finds the website, and automates UI actions with Playwright.
- Mappings for words and pictures are stored in JSON files (`wordlist.json`, `picturelist.json`). Unknown items may prompt for manual input once and get saved. ! NOTE: If you get specific new words, please map them and send them into an [issue](https://github.com/toomcis/WocaFuckOff/issues) under the tag `additional word mapping` or `additional picture mapping`

**Limitations & Caveats**

- The project was generated/assisted by AI — expect brittle behavior and imperfect code, if any issue arises please report it in the [issues](https://github.com/toomcis/WocaFuckOff/issues).
- It assumes specific DOM IDs and classes on the target site; UI changes will break handlers.
- Designed and tested against Slovak-English examples; other languages may require adjusting the translation fallback settings and the `source` language in the translator calls.
- Use responsibly: automated interaction with websites may violate terms of service. I am not responsible for any bans that might come with breaking ToS of the WocaBee app.

**Troubleshooting**

- If handlers fail to click elements, the site DOM may have changed; open [solver.py](solver.py) and inspect the locator logic.
- Network/translation failures fallback to manual prompts — check `wordlist.json` for saved entries.

**License & Attribution**

- This project uses the [MIT license](LICENSE)
