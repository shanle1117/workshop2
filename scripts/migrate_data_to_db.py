"""
Data migration script to migrate CSV/JSON files to Django database models.
Run this script after Django migrations are applied.
"""
import os
import sys
import django
import pandas as pd
import json
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()

from django_app.models import FAQEntry, Course, Staff, Schedule


def migrate_faq_entries(csv_path):
    """Migrate FAQ entries from CSV to FAQEntry model"""
    print(f"Migrating FAQ entries from {csv_path}...")
    
    if not os.path.exists(csv_path):
        print(f"Warning: CSV file not found at {csv_path}")
        return
    
    df = pd.read_csv(csv_path).fillna("")
    
    created_count = 0
    updated_count = 0
    
    for _, row in df.iterrows():
        question = str(row.get('question', '')).strip()
        answer = str(row.get('answer', '')).strip()
        category = str(row.get('category', 'general')).strip()
        keywords = str(row.get('keywords', '')).strip()
        
        if not question or not answer:
            continue
        
        # Check if entry already exists
        entry, created = FAQEntry.objects.get_or_create(
            question=question,
            defaults={
                'answer': answer,
                'category': category,
                'keywords': keywords,
                'is_active': True,
            }
        )
        
        if created:
            created_count += 1
        else:
            # Update existing entry
            entry.answer = answer
            entry.category = category
            entry.keywords = keywords
            entry.save()
            updated_count += 1
    
    print(f"✓ Migrated {created_count} new FAQ entries, updated {updated_count} existing entries")


def migrate_course_info(json_path):
    """Migrate course information from JSON to Course model"""
    print(f"Migrating course info from {json_path}...")
    
    if not os.path.exists(json_path):
        print(f"Warning: JSON file not found at {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            courses_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file at {json_path}")
        return
    
    created_count = 0
    
    # Handle both list and dict formats
    if isinstance(courses_data, dict):
        courses_data = courses_data.get('courses', [])
    
    for course_data in courses_data:
        code = course_data.get('code', '').strip()
        name = course_data.get('name', '').strip()
        
        if not code or not name:
            continue
        
        course, created = Course.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': course_data.get('description', ''),
                'credits': course_data.get('credits', 3),
                'program': course_data.get('program', ''),
            }
        )
        
        if created:
            created_count += 1
    
    print(f"✓ Migrated {created_count} courses")


def migrate_staff_contacts(json_path):
    """Migrate staff contacts from JSON to Staff model"""
    print(f"Migrating staff contacts from {json_path}...")
    
    if not os.path.exists(json_path):
        print(f"Warning: JSON file not found at {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            staff_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file at {json_path}")
        return
    
    created_count = 0
    
    # Handle both list and dict formats
    if isinstance(staff_data, dict):
        staff_data = staff_data.get('staff', [])
    
    for staff_info in staff_data:
        name = staff_info.get('name', '').strip()
        
        if not name:
            continue
        
        staff, created = Staff.objects.get_or_create(
            name=name,
            defaults={
                'title': staff_info.get('title', ''),
                'email': staff_info.get('email', ''),
                'phone': staff_info.get('phone', ''),
                'office': staff_info.get('office', ''),
                'department': staff_info.get('department', ''),
            }
        )
        
        if created:
            created_count += 1
    
    print(f"✓ Migrated {created_count} staff members")


def migrate_schedule(json_path):
    """Migrate schedule information from JSON to Schedule model"""
    print(f"Migrating schedule from {json_path}...")
    
    if not os.path.exists(json_path):
        print(f"Warning: JSON file not found at {json_path}")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON file at {json_path}")
        return
    
    created_count = 0
    
    # Handle both list and dict formats
    if isinstance(schedule_data, dict):
        schedule_data = schedule_data.get('events', [])
    
    for event in schedule_data:
        title = event.get('title', '').strip()
        
        if not title:
            continue
        
        # Parse dates if provided
        start_date = None
        end_date = None
        
        if event.get('start_date'):
            try:
                from datetime import datetime
                start_date = datetime.strptime(event['start_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        if event.get('end_date'):
            try:
                from datetime import datetime
                end_date = datetime.strptime(event['end_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        schedule, created = Schedule.objects.get_or_create(
            title=title,
            semester=event.get('semester', ''),
            defaults={
                'description': event.get('description', ''),
                'start_date': start_date,
                'end_date': end_date,
                'event_type': event.get('event_type', ''),
            }
        )
        
        if created:
            created_count += 1
    
    print(f"✓ Migrated {created_count} schedule events")


def main():
    """Main migration function"""
    print("=" * 70)
    print("FAIX Chatbot - Data Migration Script")
    print("=" * 70)
    print()
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    data_dir = BASE_DIR / 'data'
    
    # Migrate FAQ entries from CSV
    faix_csv = data_dir / 'faix_data.csv'
    migrate_faq_entries(faix_csv)
    print()
    
    # Migrate course info
    course_json = data_dir / 'course_info.json'
    migrate_course_info(course_json)
    print()
    
    # Migrate staff contacts
    staff_json = data_dir / 'staff_contacts.json'
    migrate_staff_contacts(staff_json)
    print()
    
    # Migrate schedule
    schedule_json = data_dir / 'schedule.json'
    migrate_schedule(schedule_json)
    print()
    
    print("=" * 70)
    print("Migration completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()

