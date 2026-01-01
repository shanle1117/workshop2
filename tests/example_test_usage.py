"""
Simple Example: How to Use the Chatbot Test Script

This file shows simple examples of how to use the test script.
"""

import subprocess
import sys
from pathlib import Path

# Example 1: Quick test (standalone mode)
print("Example 1: Quick test in standalone mode")
print("Command: python tests/test_chatbot_with_questions.py --quick --mode standalone")
print()

# Example 2: Test via API (requires Django server running)
print("Example 2: Test via API")
print("Command: python tests/test_chatbot_with_questions.py --mode api")
print()

# Example 3: Test specific category
print("Example 3: Test specific category")
print("Command: python tests/test_chatbot_with_questions.py --category program_info")
print()

# Example 4: Test with limit
print("Example 4: Test with limited questions")
print("Command: python tests/test_chatbot_with_questions.py --limit 5")
print()

# Example 5: Save results to file
print("Example 5: Save results to JSON")
print("Command: python tests/test_chatbot_with_questions.py --quick --save-results results.json")
print()

# Uncomment to run a quick test:
# if __name__ == '__main__':
#     result = subprocess.run([
#         sys.executable,
#         'tests/test_chatbot_with_questions.py',
#         '--quick',
#         '--mode', 'standalone'
#     ])
#     sys.exit(result.returncode)

