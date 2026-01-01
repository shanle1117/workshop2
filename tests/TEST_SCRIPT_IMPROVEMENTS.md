# Test Script Improvements

## Issues Fixed

### 1. **Invalid Questions Being Tested**
**Problem**: The test script was parsing markdown links, checklist items, and notes as questions.

**Examples of invalid questions that were being tested:**
- `[Greetings](#greetings)` - Markdown link
- `[ ] Greetings work correctly` - Checklist item
- `Questions marked with [staff name] should be replaced...` - Note/instruction

**Fix**: Added comprehensive filtering to skip:
- Markdown links `[text](#link)`
- Checklist items `[ ]` or `[x]`
- Table of contents entries
- Notes and instructions (lines with "should be replaced", "may require", etc.)
- Very long lines (>200 chars)
- Lines without letters

### 2. **Fallback Responses Counted as Success**
**Problem**: Questions getting fallback responses like "I'm sorry, I didn't quite understand" were being counted as successful tests.

**Fix**: Added fallback detection that marks responses as failures if they contain phrases like:
- "i'm sorry, i didn't quite understand"
- "could you please clarify"
- "i couldn't find"
- "i don't understand"
- "please rephrase"

### 3. **Default Mode Issue**
**Problem**: Default was set to `standalone` mode which may not have full knowledge base access.

**Fix**: Changed default to `api` mode which has better access to the full knowledge base and LLM agents.

## Improvements Made

### Better Question Parsing
- Skips markdown formatting
- Validates questions (must contain letters, reasonable length)
- Filters out notes, instructions, and metadata
- Handles emoji in category headers

### Better Success Detection
- Only counts responses as successful if they're NOT fallback responses
- Validates that responses contain actual information

### Better Category Mapping
- Properly maps category names to intent names
- Handles emoji in category headers

## Usage

### Test with API Mode (Recommended)
```bash
# Make sure Django server is running first
python manage.py runserver

# In another terminal, run tests
python tests/test_chatbot_with_questions.py --quick --mode api
```

### Test Specific Category
```bash
python tests/test_chatbot_with_questions.py --category program_info --mode api
```

### Save Results
```bash
python tests/test_chatbot_with_questions.py --quick --mode api --save-results results.json
```

## Expected Results

With these improvements, you should see:
- **Fewer total questions** (invalid ones filtered out)
- **Lower success rate** (fallback responses now count as failures)
- **More accurate testing** (only real questions are tested)
- **Better identification** of areas needing improvement

## Next Steps

If you're still seeing many fallback responses, consider:

1. **Check Intent Detection**: Verify that intents are being detected correctly
2. **Check Knowledge Base**: Ensure FAIX JSON data is loaded properly
3. **Check LLM**: If using LLM agents, ensure Ollama is running
4. **Review Failed Tests**: Look at the failed tests output to see which questions need better handling

## Example Output

Before improvements:
```
Total Questions: 94
Successful: 94 (100%)
```

After improvements:
```
Total Questions: 45
Successful: 12 (26.7%)
Failed: 33 (73.3%)
```

This more accurately reflects that many questions are getting fallback responses and need improvement in the chatbot's knowledge base or intent detection.

