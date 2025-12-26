# Staff Hallucination Fix

## Problem
The chatbot was generating fake staff members (e.g., "Mr. Wong Hock Chye", "Ms. Ng Siew Hua") that don't exist in `staff_contacts.json`. The LLM was inventing staff information instead of using only the provided data.

## Solution
Enhanced the staff agent's system prompt and context formatting to strictly enforce using only the provided staff list.

### Changes Made

#### 1. Strengthened System Prompt (`src/agents.py`)
- Added explicit CRITICAL RULES section
- Emphasized that ONLY staff from the provided context should be used
- Added clear instructions for when staff are not found
- Made it explicit that the Staff Contacts Context is the ONLY source of truth

#### 2. Enhanced Context Formatting (`src/prompt_builder.py`)
- Added header: "Staff Contacts Context (ONLY SOURCE - USE THIS LIST ONLY)"
- Added total count: "Total staff members available: X"
- Added warning: "You MUST ONLY use staff from this list. Do NOT invent or create any staff members."
- Added critical prefix message when staff context is present

### Key Improvements

**Before:**
```
"Never invent people or contact details; if you don't find the information, say you are not sure..."
```

**After:**
```
"CRITICAL RULES - READ CAREFULLY:
1. ONLY list staff members whose names appear in the 'Staff Contacts Context'
2. NEVER invent, create, or mention staff members who are NOT in the provided context
3. NEVER use generic names or make up staff information
4. If asked about staff not in the context, say: 'I don't have information about that staff member in my database...'
5. If no matching staff are found, say: 'I couldn't find any staff members matching your query...'"
```

### Testing
To verify the fix works:

1. Ask: "Who are the administration staff?"
   - Should only return staff from `staff_contacts.json`
   - Should NOT invent names like "Mr. Wong Hock Chye"

2. Ask: "Who is the Deputy Director?"
   - Should say: "I don't have information about that staff member in my database"
   - Should NOT invent a fake deputy director

3. Ask: "List all professors"
   - Should only list professors from the JSON file
   - Currently: Professor Ts. Dr. Burhanuddin Bin Mohd Aboobaider

### Current Staff Data
- **Total staff**: 39 members
- **Administration**: 7 staff (Deputy Registrar, Senior Assistant Registrar, etc.)
- **Academic**: 32 staff (Professors, Associate Professors, Lecturers, Senior Lecturers)

All staff data comes from `data/staff_contacts.json` - this is the ONLY source.

### Files Modified
1. `src/agents.py` - Updated staff agent system prompt
2. `src/prompt_builder.py` - Enhanced context formatting and added critical warnings

