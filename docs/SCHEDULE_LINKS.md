# Schedule Timetable Links

The chatbot now includes links to official timetable pages when answering schedule-related questions.

## Supported Programs

1. **BAXI** - Bachelor of Computer Science (Artificial Intelligence)
   - Link: https://faix.utem.edu.my/en/academics/academic-resources/timetable/32-baxi-jadualwaktu-sem1-sesi-2025-2026/file.html

2. **BAXZ** - Bachelor of Computer Science (Cybersecurity)
   - Link: https://faix.utem.edu.my/en/academics/academic-resources/timetable/31-baxz-jadualwaktu-sem1-sesi-2025-2026/file.html

3. **Master Programs** - MAXD, MAXZ, BRIDGING
   - Link: https://faix.utem.edu.my/en/academics/academic-resources/timetable/30-jadual-master-sem1-2025-2026-v3-faix/file.html

## How It Works

The chatbot automatically:
1. **Detects program type** from user queries (BAXI, BAXZ, or master program)
2. **Searches schedule data** for matching timetables
3. **Includes appropriate link** at the end of the response

## Example Queries

### BAXI Queries
- "BAXI timetable"
- "BAXI S1G1 schedule"
- "When is BITP 1323 class for BAXI?"

**Response includes:** BAXI timetable link

### BAXZ Queries
- "BAXZ schedule"
- "BAXZ S2G1 timetable"
- "Show me BAXZ classes"

**Response includes:** BAXZ timetable link

### Master Program Queries
- "MAXD timetable"
- "Master program schedule"
- "MAXD-FULL TIME schedule"

**Response includes:** Master program timetable link

### General Queries
- "What timetables are available?"
- "Show me all schedules"

**Response includes:** All three timetable links

## Implementation Details

The links are added in `src/knowledge_base.py` in the `_get_schedule_answer()` method:
- Program type detection based on keywords in user query
- Link selection based on detected program or matching schedule data
- Links formatted as: `📅 **View Complete Timetable:** [link]`

## Updating Links

To update timetable links, modify the `TIMETABLE_LINKS` dictionary in `src/knowledge_base.py`:

```python
TIMETABLE_LINKS = {
    'baxi': 'https://faix.utem.edu.my/en/academics/academic-resources/timetable/32-baxi-jadualwaktu-sem1-sesi-2025-2026/file.html',
    'baxz': 'https://faix.utem.edu.my/en/academics/academic-resources/timetable/31-baxz-jadualwaktu-sem1-sesi-2025-2026/file.html',
    'master': 'https://faix.utem.edu.my/en/academics/academic-resources/timetable/30-jadual-master-sem1-2025-2026-v3-faix/file.html',
}
```

