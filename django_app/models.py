from django.db import models
from django.utils import timezone
import uuid


def generate_session_id():
    """Generate a unique session ID"""
    return str(uuid.uuid4())


class UserSession(models.Model):
    """Track user sessions and context"""
    session_id = models.CharField(max_length=100, unique=True, default=generate_session_id)
    user_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    context = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"Session {self.session_id}"


class Conversation(models.Model):
    """Store conversation sessions"""
    user_id = models.CharField(max_length=100, blank=True, null=True)
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='conversations', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Untitled'}"


class Message(models.Model):
    """Store individual messages in conversations"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    intent = models.CharField(max_length=50, blank=True, null=True)
    confidence = models.FloatField(default=0.0, null=True, blank=True)
    entities = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['intent']),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class FAQEntry(models.Model):
    """Knowledge base entries migrated from CSV/JSON"""
    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(max_length=100, db_index=True)
    keywords = models.TextField(help_text="Comma-separated keywords")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['category', 'question']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "FAQ Entry"
        verbose_name_plural = "FAQ Entries"

    def __str__(self):
        return f"{self.category}: {self.question[:50]}..."

    def get_keywords_list(self):
        """Return keywords as a list"""
        return [kw.strip().lower() for kw in self.keywords.split(',') if kw.strip()]


class Course(models.Model):
    """Store course information"""
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    credits = models.IntegerField(default=3)
    program = models.CharField(max_length=100, blank=True)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='required_for')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['program']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Staff(models.Model):
    """Store staff contact information"""
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    office = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['department']),
        ]
        verbose_name_plural = "Staff"

    def __str__(self):
        return f"{self.name} - {self.title or 'Staff'}"


class Schedule(models.Model):
    """Store schedule and academic calendar information"""
    SEMESTER_CHOICES = [
        ('fall', 'Fall'),
        ('spring', 'Spring'),
        ('summer', 'Summer'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    event_type = models.CharField(max_length=50, blank=True, help_text="e.g., registration, classes, exams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['semester']),
            models.Index(fields=['start_date']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"{self.title} - {self.semester or 'N/A'}"


class ResponseFeedback(models.Model):
    """Store user feedback on bot responses for reinforcement learning"""
    FEEDBACK_CHOICES = [
        ('good', 'Good'),
        ('bad', 'Bad'),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedbacks')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='feedbacks')
    feedback_type = models.CharField(max_length=10, choices=FEEDBACK_CHOICES)
    user_message = models.TextField(help_text="The original user message that prompted this response")
    bot_response = models.TextField(help_text="The bot response that received feedback")
    intent = models.CharField(max_length=50, blank=True, null=True, help_text="Detected intent for the user message")
    user_comment = models.TextField(blank=True, null=True, help_text="Optional user comment explaining the feedback")
    session_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message', 'feedback_type']),
            models.Index(fields=['intent', 'feedback_type']),
            models.Index(fields=['session_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Feedback on Message {self.message.id}: {self.feedback_type}"
