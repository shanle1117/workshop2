"""
Interactive CLI for manual testing of the FAIX conversation manager.

Usage (Windows recommended):
    python -X utf8 chatbot_cli.py
"""

from __future__ import annotations

from typing import Dict, Tuple

from conversation_manager import process_conversation


def run_cli() -> None:
    """Run an interactive prompt that feeds user text into process_conversation."""
    print("=" * 70)
    print("FAIX Chatbot Interactive CLI")
    print("=" * 70)
    print("Type your message and press Enter. Use Ctrl+C or Ctrl+Z to exit.")
    print("Tip: on Windows, run with `python -X utf8 chatbot_cli.py` for emoji support.")
    print()

    context: Dict | None = {}

    while True:
        try:
            user_message = input("You: ").strip()
        except EOFError:
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye!")
            break

        if not user_message:
            continue

        response, context_dict = process_conversation(user_message, context)
        context = context_dict

        print("Bot:", response)
        print()

        # Reset context automatically if the conversation manager closed the session
        if not context.get("session_active", True):
            print("(Conversation reset. Start a new topic!)")
            print()
            context = {}


if __name__ == "__main__":
    run_cli()

