# Separated Data Agent Testing

This document describes the test module for verifying that chatbot agents correctly load and use separated JSON data files.

## Overview

The test module `test_separated_data_agents.py` validates that:
1. Each agent loads data from the correct separated JSON files
2. Agents only load their assigned data sections (no unnecessary data)
3. Context retrieval works correctly for each agent
4. Prompts are built properly with agent-specific context
5. Data isolation is maintained between agents

## Running the Tests

### Basic Usage

```bash
python tests/test_separated_data_agents.py
```

### With pytest (if available)

```bash
pytest tests/test_separated_data_agents.py -v
```

## Test Coverage

### Test 1: Separated File Loading
- Validates that all 15 separated JSON files can be loaded
- Checks file structure and data types
- Verifies files exist in `data/separated/` directory

### Test 2: FAQ Agent Data Loading
- Verifies FAQ agent loads 12 expected sections:
  - faculty_info, vision_mission, top_management, programmes, admission, departments, facilities, academic_resources, key_highlights, faqs, research_focus, course_info
- Confirms it excludes staff_contacts and schedule
- Validates data structures

### Test 3: Schedule Agent Data Loading
- Verifies Schedule agent loads 3 sections:
  - schedule, academic_resources, faculty_info (minimal)
- Tests schedule document retrieval (136 schedule items)
- Validates document structure

### Test 4: Staff Agent Data Loading
- Verifies Staff agent loads 3 sections:
  - staff_contacts, departments, faculty_info (minimal - dean only)
- Tests staff document retrieval (39 staff members)
- Validates staff document structure

### Test 5: Agent Context Retrieval
- Tests context retrieval for each agent with sample queries
- Validates that context contains expected keys
- Verifies FAIX data sections are correctly included

### Test 6: Prompt Building
- Tests prompt construction with agent-specific context
- Validates message structure (system, context, user)
- Ensures context is properly included in prompts

### Test 7: Data Isolation
- Verifies agents don't load unnecessary data
- Confirms proper data boundaries between agents
- Validates minimal data loading (e.g., schedule agent only gets name/university from faculty_info)

## Expected Results

When all tests pass, you should see:
```
Total: 7/7 tests passed
All tests passed!
```

## Test Output

The test module provides colored output:
- 🟢 **[PASS]** - Test passed
- 🔴 **[FAIL]** - Test failed
- 🟡 **[WARN]** - Warning (non-critical issue)
- 🔵 **[INFO]** - Informational message

## Test Data Requirements

The tests expect the following separated JSON files in `data/separated/`:
- `faculty_info.json`
- `vision_mission.json`
- `top_management.json`
- `programmes.json`
- `admission.json`
- `departments.json`
- `facilities.json`
- `academic_resources.json`
- `key_highlights.json`
- `faqs.json`
- `research_focus.json`
- `staff_contacts.json`
- `schedule.json`
- `course_info.json`
- `metadata.json`

## Troubleshooting

### Tests Fail with "File not found"
- Ensure `data/separated/` directory exists
- Verify all separated JSON files are present
- Check file permissions

### Tests Fail with "Import Error"
- Ensure you're running from project root
- Install required dependencies: `pip install -r requirements.txt`
- For pytest: `pip install pytest`

### Data Structure Errors
- Verify JSON files are valid JSON
- Check that files follow expected structure:
  - Files should have the section key as root (e.g., `{"schedule": [...]}`)
  - Or the data directly (e.g., `[...]` for lists, `{...}` for dicts)

## Continuous Integration

These tests can be integrated into CI/CD pipelines to ensure data separation remains correct after updates.

Example GitHub Actions workflow:
```yaml
- name: Run Separated Data Tests
  run: python tests/test_separated_data_agents.py
```

## Related Files

- `src/agents.py` - Agent definitions and data loading functions
- `src/prompt_builder.py` - Prompt construction logic
- `data/separated/` - Separated JSON data files
