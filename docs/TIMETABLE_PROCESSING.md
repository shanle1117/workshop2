# Timetable Processing Guide

## Overview

This document explains how the timetable schedule data is processed and integrated into the FAIX chatbot system.

**Supported Formats:**
- **Undergraduate Timetables**: Time-based format (e.g., BAXI S1G1, BAXZ S2G1)
- **Master Program Timetables**: Week-based format (e.g., MAXD-FULL TIME, MAXZ-FULLTIME, BRIDGING)

## Process Flow

### 1. Input: Markdown Timetable File

The timetable data comes from a PDF that has been converted to Markdown format. The markdown file contains:
- Multiple timetable sections for different groups (e.g., BAXI S1G1, BITI S2G1)
- HTML tables with day-by-day schedules
- Course summary tables
- Additional information about language courses

### 2. Parsing: `scripts/parse_timetable.py`

The parser script (`scripts/parse_timetable.py`) performs the following:

1. **Extracts Group Headers**: 
   - Identifies undergraduate timetable sections by group codes (e.g., "1 BAXIS1G1", "2 BAXI S1G2")
   - Identifies master program sections (e.g., "MAXD-FULL TIME", "BRIDGING FULL TIME / PART TIME")
2. **Detects Format Type**: Automatically detects whether timetable uses time-based or week-based format
3. **Parses HTML Tables**: Extracts schedule information from HTML tables using a custom HTML parser (handles colspan and rowspan)
4. **Extracts Course Information**: 
   - For time-based: Parses course codes, types (LEC/LAB), rooms, lecturers, and times
   - For week-based: Parses course codes, weeks (W1-W18), rooms, and time slots
5. **Structures Data**: Converts raw timetable data into structured JSON format

### 3. Output: JSON Schedule Data

The parsed data is saved in two locations:

1. **`data/timetable_data.json`**: Standalone timetable data file
2. **`data/faix_json_data.json`**: Main FAIX data file (schedule section updated)

### 4. Integration: Chatbot Knowledge Base

The schedule data is integrated into the chatbot through:

- **`src/knowledge_base.py`**: Added `_get_schedule_answer()` method to handle schedule queries
- **`src/agents.py`**: Schedule agent already configured to use schedule documents
- **`django_app/views.py`**: Routes schedule queries to the schedule agent

## Schedule Data Structure

Each schedule entry contains:

```json
{
  "title": "BAXIS1G1 - Semester 1 2025/2026",
  "description": "Courses and schedule summary",
  "time": "Semester 1 2025/2026",
  "group": "BAXIS1G1",
  "semester": "1",
  "academic_year": "2025/2026",
  "schedule": "Formatted timetable text...",
  "courses": ["BITI 1113 ARTIFICIAL INTELLIGENCE", ...],
  "raw": {
    "schedule": {
      "Monday": [
        {
          "course_code": "BITP 1323",
          "course_type": "LEC",
          "room": "DK 6",
          "lecturer": "DR NAJMA",
          "time": "08:00 - 09:00"
        }
      ]
    }
  }
}
```

## How to Use

### Running the Parser

To process a new timetable file:

```bash
python scripts/parse_timetable.py
```

**Note**: Update the `input_file` path in the script to point to your markdown file.

### Querying Schedules

Users can ask questions like:

- **Group-specific**: "What is my timetable for BAXI S1G1?"
- **Course-specific**: "When is BITP 1323 class?"
- **General**: "What schedules are available?"

The chatbot will:
1. Detect `academic_schedule` intent
2. Extract group name or course code from the query
3. Search schedule data for matching entries
4. Return formatted schedule information

## Supported Query Patterns

### Group Queries
- "timetable for BAXIS1G1"
- "schedule for BAXI S1G2"
- "my timetable BAXIS2G2"
- "MAXD-FULL TIME schedule"
- "BRIDGING timetable"

### Course Queries
- "when is BITP 1323"
- "BITI 1203 schedule"
- "class time for BAXU 1123"
- "MAXD 5113 schedule"
- "when is MAXZ 5463"

### General Queries
- "what is the academic schedule"
- "show me available timetables"
- "when are classes"
- "master program schedule"

## Data Updates

When updating timetable data:

1. **Convert PDF to Markdown**: Use MinerU or similar tool to extract markdown from PDF
2. **Update Parser Paths**: Modify `input_files` list in `scripts/parse_timetable.py` to include all timetable files:
   - Undergraduate timetables (BAXI, BAXZ, BITI)
   - Master program timetables (MAXD, MAXZ, BRIDGING)
3. **Run Parser**: Execute `python scripts/parse_timetable.py`
   - The parser will process all files and merge the results
4. **Verify Output**: Check `data/faix_json_data.json` to ensure schedule section is updated
5. **Test Chatbot**: Test schedule queries to verify data is accessible for both undergraduate and master programs

## Technical Details

### Parser Components

1. **TableParser**: Custom HTML parser that extracts table data, handling colspan and rowspan attributes
2. **is_week_based_timetable()**: Detects if a timetable uses week-based format (W1, W2, etc.)
3. **parse_week_based_timetable()**: Parses master program timetables with week-based schedules
4. **parse_time_slot()**: Parses time strings like "08:00 - 09:00" into start/end minutes
5. **parse_course_info()**: Extracts course code, type, room, and lecturer from course text
6. **parse_timetable_section()**: Main parsing function that processes a complete timetable section (handles both formats)
7. **convert_to_chatbot_format()**: Converts parsed data into chatbot-compatible format

### Matching Logic

The `_get_schedule_answer()` method uses:

- **Group Matching**: Regex patterns to extract group codes from queries
- **Course Code Matching**: Extracts course codes (e.g., "BITP 1323")
- **Keyword Matching**: Searches titles and descriptions for schedule-related keywords

### Response Formatting

Schedule responses are formatted as:
- **Group-specific**: Full timetable with day-by-day breakdown
- **Course-specific**: All occurrences of the course across groups
- **General**: List of available groups with instructions to specify

## Troubleshooting

### Parser Finds 0 Sections

- Check that group header pattern matches your file format
- Verify markdown file encoding (should be UTF-8)
- Check that HTML tables are properly formatted

### Schedule Data Not Appearing in Chatbot

- Verify `faix_json_data.json` has schedule section populated
- Check that `check_schedule_data_available()` returns True
- Ensure `academic_schedule` intent is properly configured

### Incorrect Course Information

- Review course parsing regex patterns in `parse_course_info()`
- Check for variations in course code formats
- Verify room and lecturer extraction logic

## Future Enhancements

Potential improvements:

1. **Semester Detection**: Automatically detect current semester
2. **Room Mapping**: Link rooms to building locations
3. **Conflict Detection**: Identify schedule conflicts
4. **Export Formats**: Generate iCal or PDF schedules
5. **Notifications**: Remind users of upcoming classes

