from django.contrib import admin
from .models import (
    UserSession, Conversation, Message, FAQEntry,
    Course, Staff, Schedule
)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user_id', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id', 'user_id']
    readonly_fields = ['session_id', 'created_at', 'updated_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user_id', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'user_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'intent', 'confidence', 'timestamp']
    list_filter = ['role', 'intent', 'timestamp']
    search_fields = ['content', 'intent']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'question', 'view_count', 'helpful_count', 'is_active']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['question', 'answer', 'category', 'keywords']
    readonly_fields = ['created_at', 'updated_at', 'view_count', 'helpful_count']
    fieldsets = (
        ('Content', {
            'fields': ('question', 'answer', 'category', 'keywords')
        }),
        ('Metadata', {
            'fields': ('is_active', 'view_count', 'helpful_count', 'created_at', 'updated_at')
        }),
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'credits', 'program', 'created_at']
    list_filter = ['program', 'created_at']
    search_fields = ['code', 'name', 'description']
    filter_horizontal = ['prerequisites']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'email', 'department', 'phone']
    list_filter = ['department', 'title']
    search_fields = ['name', 'email', 'title', 'department']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['title', 'semester', 'event_type', 'start_date', 'end_date']
    list_filter = ['semester', 'event_type', 'start_date']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'

