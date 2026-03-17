---
name: life-manager
description: A comprehensive life management skill handling voice memos, food nutrition analysis via images, and monthly financial reports from WeChat/Alipay CSVs, syncing to Obsidian and Apple Reminders.
---

# Life Manager Skill

This skill acts as a central hub for personal life management. It processes different types of media (voice, images, documents) to automate daily logging and financial tracking.

## Core Capabilities

1.  **Voice Memos -> Tasks/Logs:** Transcribes voice messages (using local SenseVoice), categorizes them, adds tasks to Apple Reminders, and logs them to Obsidian Daily Notes.
2.  **Food Images -> Nutrition Logs:** Analyzes food photos (using Gemini Vision), estimates calories and macros, and logs the analysis to Obsidian Daily Notes.
3.  **Financial Documents -> Monthly Reports:** Parses WeChat/Alipay export files (Excel/CSV), categorizes spending using LLM, and generates a monthly financial review in Obsidian.

## Agent Instructions (How to use this skill)

When the user sends you a file or media, you must route it through the `core_engine.py` script.

### Prerequisites
- Ensure the Python virtual environment at `~/.openclaw/workspace/funasr_venv` is used to run the script.
- Ensure `GEMINI_API_KEY` is exported in the environment.

### Routing Logic

**1. If the user sends an Audio file (Voice Message):**
- **Action:** You must execute the engine with the `voice` action.
- **Command:** `source ~/.openclaw/workspace/funasr_venv/bin/activate && python3 ~/.openclaw/workspace/skills/life-manager/scripts/core_engine.py voice <path_to_audio_file>`
- **Expected Outcome:** The script will transcribe, optionally set an Apple Reminder, and return the Markdown text to append to the Obsidian Daily Note. You should then acknowledge the action to the user.

**2. If the user sends an Image file (Food Photo):**
- **Action:** You must execute the engine with the `food` action.
- **Command:** `source ~/.openclaw/workspace/funasr_venv/bin/activate && export GEMINI_API_KEY="<api_key>" && python3 ~/.openclaw/workspace/skills/life-manager/scripts/core_engine.py food <path_to_image_file>`
- **Expected Outcome:** The script returns a nutritional analysis in Markdown. You must append this to the Obsidian Daily Note and summarize it for the user.

**3. If the user sends an Excel/CSV file (Financial Statement):**
- **Action:** You must execute the engine with the `finance` action.
- **Command:** `source ~/.openclaw/workspace/funasr_venv/bin/activate && export GEMINI_API_KEY="<api_key>" && python3 ~/.openclaw/workspace/skills/life-manager/scripts/core_engine.py finance <path_to_excel_file>`
- **Expected Outcome:** The script parses the bill, categorizes it, and outputs a complete Monthly Financial Report in Markdown. You should save this output to a dedicated file in the Obsidian `Finance` folder (e.g., `YYYY-MM_财务复盘.md`) and notify the user it's complete.

## Configuration
The Obsidian vault path defaults to `~/Library/Mobile Documents/iCloud~md~obsidian/Documents`. If this changes, update the script.