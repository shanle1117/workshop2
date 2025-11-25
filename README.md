# FAIX Chatbot Conversation Module

Rule-based conversation management utilities plus a lightweight CLI used in the FAIX chatbot workshop exercises.

## Features
- Maintains conversational context (`conversation_manager.py`) with topic, last question, history, and graceful closing logic.
- Keyword-based intent detection for registration, contact info, and general greetings, ready to be swapped with an NLP module later.
- Friendly fallback and closing responses to keep the assistant helpful even when intent is unclear.
- Interactive CLI (`chatbot_cli.py`) for manual smoke-testing without the web UI.
- Reference data files (course info, schedules, FAQs, staff contacts) that downstream modules can load.

## Project Structure
- `conversation_manager.py` – conversation state machine and helper utilities.
- `chatbot_cli.py` – REPL wrapper that feeds user text into `process_conversation`.
- `knowledge_base.py` – helper for structured data lookups used by other modules.
- `faqs.json`, `course_info.json`, `schedule.json`, `staff_contacts.json` – curated datasets for future integrations.
- `test_chatbot.py` – pytest suite covering the conversation flow.
- `main.html`, `style.css` – sample frontend shell for embedding the chatbot UI.

## Requirements
- Python 3.10+ (tested on 3.11)
- Optional: virtual environment for isolation
- No third-party packages are required; everything uses the standard library.

## Setup
```bash
git clone https://github.com/shanle1117/workshop2.git
cd workshop2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## Running the Conversation CLI
```bash
python -X utf8 chatbot_cli.py
```
Tips:
- Use UTF-8 mode (`-X utf8`) on Windows so emoji responses render properly.
- Press `Ctrl+C` (or `Ctrl+Z` + Enter on Windows) to exit.
- After the bot says goodbye, the CLI automatically resets the context.

## Programmatic Usage
```python
from conversation_manager import process_conversation

context = {}
response, context = process_conversation("Hi", context)
```

`process_conversation` returns both the bot reply and the updated context dictionary that can be stored in sessions or passed to other layers (e.g., Django, FastAPI).

## Running Tests
```bash
python -m pytest test_chatbot.py
```

## Roadmap
- Replace keyword-based intent detection with an NLP intent classifier.
- Plug `get_response_for_topic` into `knowledge_base.py` for richer dynamic answers.
- Expose `ConversationContext` through a web interface for the main chatbot UI.

## License
This workshop project is distributed under the MIT license unless otherwise noted.

