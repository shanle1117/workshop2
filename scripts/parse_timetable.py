"""
Parser script to extract timetable data from markdown file and convert to JSON format
compatible with the FAIX chatbot schedule system.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any
from html.parser import HTMLParser
from collections import defaultdict


class TableParser(HTMLParser):
    """HTML parser to extract table data from markdown HTML tables."""
    
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.rows = []
        self.current_cell = ""
        self.colspan = 1
        self.rowspan = 1
        self.rowspan_data = {}  # Track rowspan cells
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr':
            self.in_row = True
            self.current_row = []
            # Apply rowspan data from previous rows
            for col_idx, (content, remaining) in list(self.rowspan_data.items()):
                self.current_row.append(content)
                remaining -= 1
                if remaining <= 0:
                    del self.rowspan_data[col_idx]
                else:
                    self.rowspan_data[col_idx] = (content, remaining)
        elif tag == 'td' or tag == 'th':
            self.in_cell = True
            self.current_cell = ""
            # Check for colspan and rowspan
            self.colspan = 1
            self.rowspan = 1
            for attr, value in attrs:
                if attr == 'colspan':
                    try:
                        self.colspan = int(value)
                    except ValueError:
                        self.colspan = 1
                elif attr == 'rowspan':
                    try:
                        self.rowspan = int(value)
                    except ValueError:
                        self.rowspan = 1
                        
    def handle_endtag(self, tag):
        if tag == 'td' or tag == 'th':
            self.in_cell = False
            # Add cell content, accounting for colspan
            cell_content = self.current_cell.strip()
            col_idx = len(self.current_row)
            self.current_row.append(cell_content)
            
            # Handle rowspan
            if self.rowspan > 1:
                self.rowspan_data[col_idx] = (cell_content, self.rowspan - 1)
            
            # Add empty cells for colspan > 1
            for _ in range(self.colspan - 1):
                self.current_row.append("")
        elif tag == 'tr':
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag == 'table':
            self.in_table = False
            
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data


def parse_time_slot(time_str: str) -> tuple:
    """Parse time slot string like '08:00 - 09:00' to start and end times."""
    match = re.match(r'(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})', time_str)
    if match:
        start_hour, start_min = int(match.group(1)), int(match.group(2))
        end_hour, end_min = int(match.group(3)), int(match.group(4))
        return (start_hour * 60 + start_min, end_hour * 60 + end_min)
    return None


def parse_course_info(course_text: str) -> Dict[str, str]:
    """Parse course information from text like 'BITP 1323 LEC - DK 6 BPA DR NAJMA'."""
    if not course_text or course_text.strip() == '' or course_text.upper() == 'BREAK':
        return None
    
    # Pattern: COURSE_CODE TYPE - ROOM LECTURER
    # Examples:
    # - BITP 1323 LEC - DK 6 BPA DR NAJMA
    # - BITP 1113 LAB - MP2 DR NURIDAWATI
    # - BLLW 1282 BK1 PPB DR ZAHIR
    
    parts = course_text.split(' - ')
    if len(parts) < 2:
        # Try without dash separator
        parts = [course_text]
    
    course_code_match = re.match(r'([A-Z]{2,4}\s*\d{4})', parts[0])
    if not course_code_match:
        return None
    
    course_code = course_code_match.group(1).strip()
    rest = parts[0][len(course_code):].strip()
    
    # Extract type (LEC, LAB, etc.)
    type_match = re.search(r'\b(LEC|LAB|TUT|RECAP|LEC\s*RECAP)\b', rest, re.IGNORECASE)
    course_type = type_match.group(1).upper() if type_match else "LEC"
    
    # Extract room and lecturer from remaining parts
    room = ""
    lecturer = ""
    
    if len(parts) > 1:
        room_lecturer = parts[1].strip()
        # Try to extract room (usually short codes like DK 6, BK2, MP2, etc.)
        room_match = re.search(r'\b([A-Z]{1,3}\s*\d{1,2}|[A-Z]{2,4}\s*[A-Z]{1,3}|CLEAR|CELL|MB\d+|BK\d+|MP\d+|AI\d+|MKP\d+|MSP|SVR|MR\d+|MM\d+)\b', room_lecturer)
        if room_match:
            room = room_match.group(1).strip()
            # Lecturer is usually after room, often starts with DR, PM, TS, PROF, etc.
            lecturer_match = re.search(r'\b(DR|PM|TS|PROF|EN|PN|GB)\s+([A-Z\s]+)', room_lecturer[room_match.end():])
            if lecturer_match:
                lecturer = (lecturer_match.group(1) + ' ' + lecturer_match.group(2)).strip()
            else:
                # Try to find lecturer without prefix
                remaining = room_lecturer[room_match.end():].strip()
                if remaining:
                    lecturer = remaining
        else:
            # No room found, might be lecturer only
            lecturer = room_lecturer
    
    return {
        'course_code': course_code,
        'course_type': course_type,
        'room': room,
        'lecturer': lecturer,
        'full_text': course_text
    }


def is_week_based_timetable(table_html: str) -> bool:
    """Check if table uses week-based format (W1, W2, W3...) instead of time slots."""
    return bool(re.search(r'\bW\d+\b', table_html, re.IGNORECASE))


def parse_week_based_timetable(table_html: str, group_name: str) -> Dict[str, Any]:
    """Parse week-based timetable format (used for master programs)."""
    parser = TableParser()
    parser.feed(table_html)
    
    if len(parser.rows) < 2:
        return None
    
    # First row contains week headers (W1, W2, W3, etc.)
    header_row = parser.rows[0]
    weeks = []
    time_info = None
    
    # Find week columns and time info
    for i, cell in enumerate(header_row):
        cell_upper = cell.upper().strip()
        if cell_upper.startswith('W') and cell_upper[1:].isdigit():
            week_num = int(cell_upper[1:])
            weeks.append({'index': i, 'week': week_num, 'label': cell_upper})
        elif 'time' in cell_upper.lower() or 'pm' in cell_upper.lower() or 'am' in cell_upper.lower():
            time_info = cell.strip()
    
    if not weeks:
        return None
    
    # Parse schedule by day
    schedule = {}
    days_map = {'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday', 
                'Thurs': 'Thursday', 'Thu': 'Thursday', 'Fri': 'Friday', 
                'Sat': 'Saturday', 'Sun': 'Sunday'}
    
    for row in parser.rows[1:]:
        if not row or len(row) < 2:
            continue
        
        day_abbr = row[0].strip()
        day_full = days_map.get(day_abbr, day_abbr)
        
        # Extract time info if present in this row
        row_time = time_info
        if len(row) > 1:
            # Check if second column has time info
            second_col = row[1].strip()
            if 'pm' in second_col.lower() or 'am' in second_col.lower() or 'online' in second_col.lower():
                row_time = second_col
                start_col = 2
            else:
                start_col = 1
        
        day_schedule = []
        
        # Parse courses for each week
        for week_info in weeks:
            col_idx = week_info['index']
            if col_idx < len(row):
                cell_content = row[col_idx].strip()
                if cell_content and cell_content.upper() not in ['BREAK', 'MID SEM BREAK', 'STUDY WEEK', 'EXAM WEEK']:
                    # Extract course code
                    course_match = re.search(r'\b([A-Z]{2,4}\s*\d{4})\b', cell_content)
                    if course_match:
                        course_code = course_match.group(1).strip()
                        # Extract room info if present
                        room_match = re.search(r'\(([^)]+)\)', cell_content)
                        room = room_match.group(1) if room_match else ""
                        
                        course_info = {
                            'course_code': course_code,
                            'week': week_info['week'],
                            'week_label': week_info['label'],
                            'room': room,
                            'full_text': cell_content,
                            'time': row_time or 'TBA',
                            'format': 'week-based'
                        }
                        day_schedule.append(course_info)
        
        if day_schedule:
            schedule[day_full] = day_schedule
    
    return {
        'group': group_name,
        'schedule': schedule,
        'format': 'week-based',
        'weeks': [w['week'] for w in weeks]
    }


def parse_timetable_section(content: str, group_name: str, semester: str, year: str) -> Dict[str, Any]:
    """Parse a timetable section for a specific group."""
    
    # Find the first timetable table (main schedule table)
    table_matches = list(re.finditer(r'<table>(.*?)</table>', content, re.DOTALL))
    if not table_matches:
        return None
    
    # First table is the schedule
    table_html = '<table>' + table_matches[0].group(1) + '</table>'
    
    # Check if this is a week-based timetable (master program format)
    if is_week_based_timetable(table_html):
        result = parse_week_based_timetable(table_html, group_name)
        if result:
            result['semester'] = semester
            result['academic_year'] = year
            # Extract course summary
            course_summary = []
            for match in table_matches[1:]:
                table_html2 = '<table>' + match.group(1) + '</table>'
                parser2 = TableParser()
                parser2.feed(table_html2)
                for row in parser2.rows[1:]:
                    if len(row) >= 2 and row[1].strip():
                        course_name = row[1].strip()
                        if course_name and not re.match(r'^[A-Z\s]+:\s*\d+-\d+', course_name, re.IGNORECASE):
                            course_summary.append(course_name)
            result['courses'] = course_summary
        return result
    
    # Standard time-based timetable parsing
    parser = TableParser()
    parser.feed(table_html)
    
    if len(parser.rows) < 2:
        return None
    
    # First row contains time slots
    time_row = parser.rows[0]
    time_slots = []
    for i, cell in enumerate(time_row):
        if i == 0:  # Skip "Day" header
            continue
        time_info = parse_time_slot(cell)
        if time_info:
            time_slots.append({
                'index': i - 1,
                'time': cell,
                'start_minutes': time_info[0],
                'end_minutes': time_info[1]
            })
    
    # Parse course schedule for each day
    schedule = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    for row_idx, row in enumerate(parser.rows[1:], 1):
        if not row or len(row) < 2:
            continue
        
        day = row[0].strip()
        if day not in days:
            continue
        
        day_schedule = []
        current_col = 1  # Skip day column
        
        # Track which time slot we're in
        time_slot_idx = 0
        
        while current_col < len(row) and time_slot_idx < len(time_slots):
            cell_content = row[current_col].strip()
            
            if cell_content and cell_content.upper() != 'BREAK':
                course_info = parse_course_info(cell_content)
                if course_info:
                    time_info = time_slots[time_slot_idx]
                    course_info['time'] = time_info['time']
                    course_info['start_minutes'] = time_info['start_minutes']
                    course_info['end_minutes'] = time_info['end_minutes']
                    day_schedule.append(course_info)
            
            # Move to next time slot
            current_col += 1
            time_slot_idx += 1
        
        if day_schedule:
            schedule[day] = day_schedule
    
    # Extract course summary from subsequent tables
    course_summary = []
    for match in table_matches[1:]:  # Skip first table (schedule)
        table_html2 = '<table>' + match.group(1) + '</table>'
        parser2 = TableParser()
        parser2.feed(table_html2)
        for row in parser2.rows[1:]:  # Skip header
            if len(row) >= 2 and row[1].strip():
                course_name = row[1].strip()
                # Skip entries that are just time/room info (like "TUESDAY 4-6PM")
                if not re.match(r'^[A-Z\s]+:\s*\d+-\d+', course_name, re.IGNORECASE):
                    course_summary.append(course_name)
    
    return {
        'group': group_name,
        'semester': semester,
        'academic_year': year,
        'schedule': schedule,
        'courses': course_summary,
        'format': 'time-based'
    }


def parse_markdown_file(file_path: Path) -> List[Dict[str, Any]]:
    """Parse the entire markdown file and extract all timetable sections."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    timetables = []
    
    # Extract semester and year from header (appears multiple times)
    header_match = re.search(r'SEMESTER\s+(\d+)\s+SESSION\s+(\d{4})\s*/\s*(\d{4})', content, re.IGNORECASE)
    default_semester = header_match.group(1) if header_match else "1"
    year_start = header_match.group(2) if header_match else "2025"
    year_end = header_match.group(3) if header_match else "2026"
    academic_year = f"{year_start}/{year_end}"
    
    # Find all group headers: 
    # Pattern 1: "1 BAXIS1G1" or "1 BAXI S1G2" (undergraduate)
    # Pattern 2: "BRIDGING FULL TIME / PART TIME" or "MAXD-FULL TIME" (master programs)
    group_pattern_ug = r'^(\d+)\s+([A-Z]{2,4}\s*S?\d+G\d+(?:[/-]S?\d+G\d+-DE)?(?:-DE)?)\s*$'
    group_pattern_master = r'^([A-Z]{2,4}(?:-[A-Z\s]+)?(?:\([^)]+\))?)\s*$'
    
    # Split content by lines and find group headers
    lines = content.split('\n')
    current_section_start = None
    current_semester = default_semester
    current_group = None
    section_lines = []
    found_groups = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check if this line is an undergraduate group header
        match_ug = re.match(group_pattern_ug, line_stripped)
        if match_ug:
            # Save previous section if exists
            if current_group and section_lines:
                section_content = '\n'.join(section_lines)
                timetable = parse_timetable_section(section_content, current_group, current_semester, academic_year)
                if timetable:
                    timetables.append(timetable)
            
            # Start new section
            current_semester = match_ug.group(1)
            current_group = match_ug.group(2).strip()
            found_groups.append((current_semester, current_group))
            section_lines = []
        else:
            # Check if this is a master program group header
            # Look for patterns like "MAXD-FULL TIME", "BRIDGING FULL TIME / PART TIME", "MAXZ-FULLTIME"
            is_master_header = False
            
            if line_stripped:
                # Check for master program patterns
                master_patterns = [
                    r'^[A-Z]{2,4}[- ](?:FULL|PART)\s*TIME',
                    r'^BRIDGING',
                    r'^MAX[DZ]-',
                    r'^MAX[DZ]\s+',
                ]
                
                for pattern in master_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        # Check if next line is a table (indicates this is a group header)
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if '<table>' in next_line:
                                is_master_header = True
                                break
                
                # Also check if line contains program codes followed by table
                if not is_master_header and re.match(r'^[A-Z]{2,4}', line_stripped):
                    # Look ahead a few lines for table
                    for j in range(i + 1, min(i + 3, len(lines))):
                        if '<table>' in lines[j]:
                            is_master_header = True
                            break
            
            if is_master_header:
                # Save previous section if exists
                if current_group and section_lines:
                    section_content = '\n'.join(section_lines)
                    timetable = parse_timetable_section(section_content, current_group, current_semester, academic_year)
                    if timetable:
                        timetables.append(timetable)
                
                # Start new section
                current_group = line_stripped
                found_groups.append((current_semester, current_group))
                section_lines = []
                continue
            
            # Check if this is a new semester header
            semester_match = re.search(r'^#\s*SEMESTER\s+(\d+)', line, re.IGNORECASE)
            if semester_match:
                current_semester = semester_match.group(1)
            
            # Add line to current section
            if current_group:
                section_lines.append(line)
    
    print(f"Found {len(found_groups)} group headers: {found_groups[:5]}...")
    
    # Don't forget the last section
    if current_group and section_lines:
        section_content = '\n'.join(section_lines)
        timetable = parse_timetable_section(section_content, current_group, current_semester, academic_year)
        if timetable:
            timetables.append(timetable)
    
    return timetables


def convert_to_chatbot_format(timetables: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Convert parsed timetables to chatbot schedule document format."""
    
    schedule_docs = []
    
    for timetable in timetables:
        group = timetable.get('group', '')
        semester = timetable.get('semester', '')
        academic_year = timetable.get('academic_year', '')
        schedule = timetable.get('schedule', {})
        courses = timetable.get('courses', [])
        
        # Create a comprehensive description
        description_parts = []
        
        # Add course list
        if courses:
            description_parts.append(f"Courses: {', '.join(courses[:10])}")
        
        # Add schedule summary
        schedule_summary = []
        for day, day_schedule in schedule.items():
            if day_schedule:
                courses_today = [f"{c['course_code']} ({c['time']})" for c in day_schedule[:3]]
                schedule_summary.append(f"{day}: {', '.join(courses_today)}")
        
        if schedule_summary:
            description_parts.append("Schedule: " + " | ".join(schedule_summary[:5]))
        
        # Create detailed schedule text
        schedule_text = f"Timetable for {group} - Semester {semester} {academic_year}\n\n"
        
        # Check if this is week-based format
        is_week_based = timetable.get('format') == 'week-based'
        
        if is_week_based:
            # Format for week-based schedules
            for day, day_schedule in schedule.items():
                if day_schedule:
                    schedule_text += f"{day}:\n"
                    # Group by time if available
                    time_groups = {}
                    for course in day_schedule:
                        time_key = course.get('time', 'TBA')
                        if time_key not in time_groups:
                            time_groups[time_key] = []
                        time_groups[time_key].append(course)
                    
                    for time, courses in time_groups.items():
                        schedule_text += f"  Time: {time}\n"
                        for course in courses:
                            schedule_text += f"    - {course['course_code']} "
                            if course.get('week_label'):
                                schedule_text += f"Week {course['week']} "
                            if course.get('room'):
                                schedule_text += f"Room: {course['room']} "
                            schedule_text += f"({course.get('full_text', '')})\n"
                        schedule_text += "\n"
        else:
            # Format for time-based schedules
            for day, day_schedule in schedule.items():
                if day_schedule:
                    schedule_text += f"{day}:\n"
                    for course in day_schedule:
                        schedule_text += f"  - {course['course_code']} {course.get('course_type', '')} "
                        schedule_text += f"({course['time']}) "
                        if course.get('room'):
                            schedule_text += f"Room: {course['room']} "
                        if course.get('lecturer'):
                            schedule_text += f"Lecturer: {course['lecturer']}"
                        schedule_text += "\n"
                    schedule_text += "\n"
        
        # Create document entry
        doc = {
            'title': f"{group} - Semester {semester} {academic_year}",
            'description': ' | '.join(description_parts),
            'time': f"Semester {semester} {academic_year}",
            'group': group,
            'semester': semester,
            'academic_year': academic_year,
            'schedule': schedule_text,
            'courses': courses,
            'raw': timetable
        }
        
        schedule_docs.append(doc)
        
        # Also create individual course entries for better searchability
        for course_item in courses:
            if not course_item:
                continue
            
            # Handle both string and dict formats
            if isinstance(course_item, dict):
                course_code = course_item.get('course_code', '') or course_item.get('name', '')
                course_name = course_item.get('name', course_code)
            else:
                course_code = str(course_item)
                course_name = course_code
            
            if course_code:
                # Extract course code from course name
                code_match = re.search(r'([A-Z]{2,4}\s*\d{4})', str(course_code))
                if code_match:
                    code = code_match.group(1).strip()
                    # Find all occurrences of this course in the schedule
                    course_schedule = []
                    for day, day_schedule in schedule.items():
                        for c in day_schedule:
                            if isinstance(c, dict) and c.get('course_code', '').strip() == code:
                                time_str = c.get('time', 'TBA')
                                room_str = c.get('room', 'TBA')
                                lecturer_str = c.get('lecturer', 'TBA')
                                week_str = f"Week {c.get('week', '')}" if c.get('week') else ""
                                schedule_entry = f"{day} {time_str}"
                                if week_str:
                                    schedule_entry += f" {week_str}"
                                schedule_entry += f" - {room_str}"
                                if lecturer_str != 'TBA':
                                    schedule_entry += f" - {lecturer_str}"
                                course_schedule.append(schedule_entry)
                    
                    if course_schedule:
                        course_doc = {
                            'title': f"{code} - {course_name}",
                            'description': f"Course schedule for {code} in {group}",
                            'time': f"Semester {semester} {academic_year}",
                            'group': group,
                            'course_code': code,
                            'schedule': '\n'.join(course_schedule),
                            'raw': {'course_code': code, 'group': group, 'schedule': course_schedule}
                        }
                        schedule_docs.append(course_doc)
    
    return schedule_docs


def main():
    """Main function to parse timetable and generate JSON."""
    
    # Input file paths - can process multiple files
    # Note: Update these paths to point to your markdown files
    input_files = [
        # Path(r"C:\Users\wongs\MinerU\BAXI_JadualWaktu_Sem1_Sesi_2025_2026.pdf-8d74db70-0077-47c1-af42-7c91e372be1c\full.md"),  # BAXI timetable
        # Path(r"C:\Users\wongs\MinerU\BAXZ_JadualWaktu_Sem1_Sesi_2025_2026.pdf-aa19516a-7afd-45a8-b50a-3c9a40479575\full.md"),  # BAXZ timetable
        Path(r"c:\Users\wongs\MinerU\file.html.pdf-4c439014-7cec-4804-b6d6-0f77fbc1618a\full.md"),  # Master program
    ]
    
    all_schedule_docs = []
    
    for input_file in input_files:
        if not input_file.exists():
            print(f"Warning: Input file not found: {input_file}")
            continue
        
        print(f"\nParsing timetable file: {input_file.name}")
        
        # Parse the markdown file
        timetables = parse_markdown_file(input_file)
        print(f"Found {len(timetables)} timetable sections")
        
        # Convert to chatbot format
        schedule_docs = convert_to_chatbot_format(timetables)
        print(f"Generated {len(schedule_docs)} schedule documents")
        
        all_schedule_docs.extend(schedule_docs)
    
    print(f"\nTotal schedule documents: {len(all_schedule_docs)}")
    
    # Save to JSON file
    output_file = Path(__file__).parent.parent / 'data' / 'timetable_data.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_schedule_docs, f, indent=2, ensure_ascii=False)
    
    print(f"Saved schedule data to: {output_file}")
    
    # Also update faix_json_data.json
    faix_data_file = Path(__file__).parent.parent / 'data' / 'faix_json_data.json'
    if faix_data_file.exists():
        with open(faix_data_file, 'r', encoding='utf-8') as f:
            faix_data = json.load(f)
        
        # Merge with existing schedule data (if any)
        existing_schedule = faix_data.get('schedule', [])
        if isinstance(existing_schedule, list):
            # Combine existing and new, avoiding duplicates
            existing_groups = {doc.get('group', '') for doc in existing_schedule if isinstance(doc, dict)}
            new_docs = [doc for doc in all_schedule_docs if doc.get('group', '') not in existing_groups]
            faix_data['schedule'] = existing_schedule + new_docs
        else:
            faix_data['schedule'] = all_schedule_docs
        
        # Save updated file
        with open(faix_data_file, 'w', encoding='utf-8') as f:
            json.dump(faix_data, f, indent=2, ensure_ascii=False)
        
        print(f"Updated schedule section in: {faix_data_file}")
    else:
        print(f"Warning: {faix_data_file} not found. Skipping update.")


if __name__ == '__main__':
    main()

