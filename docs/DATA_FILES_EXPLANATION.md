# Data Files Explanation

## Overview

The chatbot uses **two main JSON configuration/data files** that serve different purposes:

### 1. `data/intent_config.json` - Intent Classification Configuration

**Purpose**: Configuration for NLP intent classification and routing

**Contains**:
- **`intent_categories`**: List of all possible intents (e.g., `program_info`, `staff_contact`, `admission`)
- **`intent_descriptions`**: Human-readable descriptions of each intent (used by zero-shot classifier)
- **`keyword_patterns`**: Keyword lists for each intent (used for fallback keyword matching)
- **`faix_data_mapping`**: Maps intents to sections in `faix_json_data.json` (currently informational only)
- **`model_config`**: NLP model settings (model name, zero-shot flag, confidence threshold)

**Used by**:
- `src/nlp_intent_classifier.py` - For intent classification
- `src/query_preprocessing.py` - For keyword-based intent detection fallback

**When to modify**:
- Adding new intent categories
- Updating keyword patterns for better intent detection
- Changing NLP model settings
- Adjusting confidence thresholds

---

### 2. `data/faix_json_data.json` - FAIX Data Content

**Purpose**: Actual FAIX faculty data (programs, staff, facilities, etc.)

**Contains**:
- **`faculty_info`**: Faculty name, dean, contact info, address
- **`vision_mission`**: Vision, mission, objectives
- **`programmes`**: Undergraduate and postgraduate programs (BCSAI, BCSCS, MCSSS, MTDSA)
- **`admission`**: Admission requirements for local/international students
- **`departments`**: Department information
- **`facilities`**: Lab facilities, booking systems
- **`academic_resources`**: uLearn portal, handbook, forms
- **`staff_contacts`**: Staff members with contact details
- **`schedule`**: Academic calendar and important dates
- **`course_info`**: Course information
- **`faqs`**: Frequently asked questions
- **`research_focus`**: Research areas and focus

**Used by**:
- `src/knowledge_base.py` - For retrieving answers based on intent
- `src/agents.py` - For loading staff/schedule documents
- `django_app/views.py` - For routing and context retrieval

**When to modify**:
- Updating staff contact information
- Adding/removing programs
- Updating admission requirements
- Changing facility information
- Adding new FAQs

---

## Relationship Between Files

```
User Query
    ↓
intent_config.json (classifies intent)
    ↓
Detected Intent (e.g., "program_info")
    ↓
faix_json_data.json (retrieves data for that intent)
    ↓
Response
```

### Example Flow:

1. **User asks**: "What programs does FAIX offer?"
2. **`intent_config.json`** → Classifies as `program_info` intent
3. **`faix_json_data.json`** → Retrieves data from `programmes.undergraduate` and `programmes.postgraduate`
4. **Response**: Lists all programs with details

---

## Current Status

- ✅ **`intent_config.json`** - Fully used for intent classification
- ✅ **`faix_json_data.json`** - Fully used for data retrieval
- ⚠️ **`faix_data_mapping`** in `intent_config.json` - Currently **informational only** (not actively used in code)

The `faix_data_mapping` section shows which parts of `faix_json_data.json` correspond to which intents, but the code currently has hardcoded mappings in `knowledge_base.py`. This mapping could be used in the future to make the code more maintainable.

---

## Recommendations

### Keep Both Files Separate

**Why**:
- **Separation of concerns**: Configuration vs. Data
- **Different update frequencies**: Intent config changes less often than data
- **Different maintainers**: NLP team vs. content team
- **Easier version control**: Changes to keywords don't affect data

### Future Enhancement

Consider using `faix_data_mapping` from `intent_config.json` to dynamically route intents to data sections, making the code more maintainable:

```python
# Instead of hardcoded:
if intent == 'program_info':
    return self._get_program_answer(user_lower)

# Use mapping:
sections = self.faix_data_mapping.get(intent, [])
if sections:
    return self._get_answer_from_sections(sections, user_lower)
```

---

## Summary

**Use BOTH files**:
- **`intent_config.json`** → For intent classification configuration
- **`faix_json_data.json`** → For actual FAIX data content

They work together but serve different purposes. Don't consolidate them - keep them separate for better maintainability.

