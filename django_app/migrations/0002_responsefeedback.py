# Generated migration for ResponseFeedback model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResponseFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feedback_type', models.CharField(choices=[('good', 'Good'), ('bad', 'Bad')], max_length=10)),
                ('user_message', models.TextField(help_text='The original user message that prompted this response')),
                ('bot_response', models.TextField(help_text='The bot response that received feedback')),
                ('intent', models.CharField(blank=True, help_text='Detected intent for the user message', max_length=50, null=True)),
                ('user_comment', models.TextField(blank=True, help_text='Optional user comment explaining the feedback', null=True)),
                ('session_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedbacks', to='django_app.conversation')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedbacks', to='django_app.message')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='responsefeedback',
            index=models.Index(fields=['message', 'feedback_type'], name='django_app__message_f12345_idx'),
        ),
        migrations.AddIndex(
            model_name='responsefeedback',
            index=models.Index(fields=['intent', 'feedback_type'], name='django_app__intent_f_abc123_idx'),
        ),
        migrations.AddIndex(
            model_name='responsefeedback',
            index=models.Index(fields=['session_id'], name='django_app__session_xyz789_idx'),
        ),
        migrations.AddIndex(
            model_name='responsefeedback',
            index=models.Index(fields=['created_at'], name='django_app__created_def456_idx'),
        ),
    ]

