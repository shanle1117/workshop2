# Chatbot Test Questions - Usage Guide

This directory contains test questions and scripts for testing the FAIX chatbot.

## Files

- **`CHATBOT_TEST_QUESTIONS.md`** - Comprehensive list of 200+ test questions organized by intent category
- **`QUICK_TEST_QUESTIONS.txt`** - Essential questions for quick testing
- **`test_chatbot_with_questions.py`** - Python script to automatically test the chatbot with questions
- **`example_test_usage.py`** - Example usage of the test script

## Quick Start

### 1. Test via API (Django Server Required)

First, start the Django server:
```bash
python manage.py runserver
```

Then in another terminal, run the test script:
```bash
# Quick test
python tests/test_chatbot_with_questions.py --quick --mode api

# Full test
python tests/test_chatbot_with_questions.py --mode api

# Test specific category
python tests/test_chatbot_with_questions.py --mode api --category program_info
```

### 2. Test Standalone (No Django Required)

```bash
# Quick test
python tests/test_chatbot_with_questions.py --quick --mode standalone

# Full test
python tests/test_chatbot_with_questions.py --mode standalone

# Test specific category with limit
python tests/test_chatbot_with_questions.py --mode standalone --category admission --limit 5
```

## Command Line Options

```
--mode {api,standalone}    Test mode (default: standalone)
--api-url URL              API URL for API mode (default: http://localhost:8000)
--category CATEGORY        Test specific category only
--quick                    Use quick test questions only
--limit N                  Limit number of questions per category
--save-results FILE        Save results to JSON file
```

## Test Categories

Available categories (matching intent names):
- `greeting` - Greetings
- `program_info` - Program Information
- `admission` - Admission Requirements
- `fees` - Fees and Tuition
- `career` - Career Opportunities
- `about_faix` - About FAIX Faculty
- `staff_contact` - Staff Contacts
- `facility_info` - Facility Information
- `academic_resources` - Academic Resources
- `research` - Research Areas
- `course_info` - Course Information
- `registration` - Registration
- `academic_schedule` - Academic Schedule
- `farewell` - Farewells

## Examples

### Example 1: Quick Test
```bash
python tests/test_chatbot_with_questions.py --quick
```

### Example 2: Test Specific Category
```bash
python tests/test_chatbot_with_questions.py --category program_info
```

### Example 3: Test with Results Saved
```bash
python tests/test_chatbot_with_questions.py --quick --save-results test_results.json
```

### Example 4: Test via API with Custom URL
```bash
python tests/test_chatbot_with_questions.py --mode api --api-url http://localhost:8000
```

### Example 5: Limited Questions per Category
```bash
python tests/test_chatbot_with_questions.py --limit 3
```

## Output

The test script provides:
- **Real-time progress**: Shows each question being tested with success/failure indicator
- **Statistics**: Overall success rate, performance metrics, and category breakdown
- **Failed tests**: List of failed questions with error details
- **JSON export**: Optional JSON file with detailed results

### Sample Output

```
================================================================================
                    FAIX Chatbot Test Suite
================================================================================

→ Testing: Quick Test Questions
  [1/10] Testing: Hello... ✓ (0.05s)
  [2/10] Testing: What programs does FAIX offer?... ✓ (1.23s)
  ...

================================================================================
                            Test Statistics
================================================================================

Overall Results:
  Total Questions: 10
  Successful: 9
  Failed: 1
  Success Rate: 90.0%

Performance:
  Average Time: 0.85s
  Min Time: 0.05s
  Max Time: 2.34s

By Category:
  greeting          : 2/2 (100.0%)
  program_info      : 1/1 (100.0%)
  ...
```

## JSON Results Format

When using `--save-results`, the JSON file contains:

```json
{
  "statistics": {
    "total": 10,
    "successful": 9,
    "failed": 1,
    "success_rate": 90.0,
    "avg_time": 0.85,
    "max_time": 2.34,
    "min_time": 0.05,
    "by_category": {
      "greeting": {"total": 2, "success": 2},
      ...
    }
  },
  "results": [
    {
      "question": "Hello",
      "response": "Hello! I'm the FAIX AI Chatbot...",
      "success": true,
      "time_taken": 0.05,
      "error": null,
      "intent": "greeting",
      "category": "greeting"
    },
    ...
  ]
}
```

## Troubleshooting

### API Mode Issues

**Error: Connection refused**
- Make sure Django server is running: `python manage.py runserver`
- Check the API URL is correct (default: http://localhost:8000)

**Error: requests library not installed**
```bash
pip install requests
```

### Standalone Mode Issues

**Error: Module not found**
- Make sure you're running from the project root directory
- Check that all dependencies are installed: `pip install -r requirements.txt`

**Error: Import errors**
- Verify that `src/` directory contains the required modules
- Check Python path includes the project root

## Tips

1. **Start with quick test**: Use `--quick` flag to test basic functionality first
2. **Test by category**: Use `--category` to focus on specific areas
3. **Save results**: Use `--save-results` to analyze results later
4. **Limit questions**: Use `--limit` to test fewer questions during development
5. **Check statistics**: Review the category breakdown to identify weak areas

## Integration with CI/CD

You can integrate this test script into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Test Chatbot
  run: |
    python manage.py runserver &
    sleep 5
    python tests/test_chatbot_with_questions.py --mode api --quick --save-results results.json
```

## Manual Testing

For manual testing, you can also use the questions directly:

1. Open `CHATBOT_TEST_QUESTIONS.md` or `QUICK_TEST_QUESTIONS.txt`
2. Copy questions and paste them into the chatbot interface
3. Verify responses are correct and relevant

---

**Last Updated**: December 2025

