import os
import sys
import json
import uuid
from pathlib import Path
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

# Setup paths for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from django_app.models import (
    UserSession, Conversation, Message, FAQEntry
)
from src.query_preprocessing import QueryProcessor
from src.knowledge_base import KnowledgeBase
from src.conversation_manager import process_conversation

# Initialize global instances
query_processor = QueryProcessor()
knowledge_base = KnowledgeBase(use_database=True)


def get_or_create_session(session_id=None, user_id=None):
    """Get or create a user session"""
    if session_id:
        try:
            session = UserSession.objects.get(session_id=session_id, is_active=True)
            return session
        except UserSession.DoesNotExist:
            pass
    
    # Create new session
    session = UserSession.objects.create(
        session_id=str(uuid.uuid4()),
        user_id=user_id or None,
    )
    return session


def get_or_create_conversation(session, user_id=None):
    """Get or create a conversation for the session"""
    # Get the most recent active conversation or create a new one
    conversation = Conversation.objects.filter(
        session=session,
        is_active=True
    ).order_by('-created_at').first()
    
    if not conversation:
        conversation = Conversation.objects.create(
            session=session,
            user_id=user_id or None,
            title="New Conversation",
        )
    
    return conversation


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """
    Chat API endpoint that processes user messages and returns bot responses.
    
    Expected JSON payload:
    {
        "message": "user message text",
        "session_id": "optional session id",
        "user_id": "optional user id"
    }
    
    Returns:
    {
        "response": "bot response text",
        "session_id": "session id",
        "conversation_id": "conversation id",
        "intent": "detected intent",
        "confidence": 0.85,
        "timestamp": "2024-01-01T12:00:00Z"
    }
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        
        if not user_message:
            return JsonResponse({
                'error': 'Message is required'
            }, status=400)
        
        # Get or create session
        session = get_or_create_session(session_id, user_id)
        
        # Get or create conversation
        conversation = get_or_create_conversation(session, user_id)
        
        # Process query with NLP
        processed_query = query_processor.process_query(user_message)
        intent = processed_query.get('detected_intent', 'general_query')
        confidence = processed_query.get('confidence_score', 0.0)
        entities = processed_query.get('extracted_entities', {})
        
        # Get context from session
        context = session.context if session.context else {}
        
        # Get answer from knowledge base
        pdf_url = None
        user_message_lower = user_message.lower()
        is_handbook_query = (
            'handbook' in user_message_lower or
            'academic handbook' in user_message_lower
        )
        
        if intent and intent != 'general_query':
            answer = knowledge_base.get_answer(intent, user_message)
            
            # Check if user is asking about academic handbook
            if intent == 'program_info' or is_handbook_query:
                # Check if Academic_Handbook.pdf exists
                import os
                from django.conf import settings
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
                if os.path.exists(pdf_path):
                    pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
        else:
            # Use conversation manager for general queries
            # BUT check for handbook first
            if is_handbook_query:
                import os
                from django.conf import settings
                answer = (
                    "📚 The Academic Handbook contains comprehensive information about "
                    "programs, courses, academic policies, graduation requirements, and more. "
                    "You can view the complete handbook PDF below."
                )
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
                if os.path.exists(pdf_path):
                    pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
                else:
                    answer = (
                        "📚 The Academic Handbook contains comprehensive information about "
                        "programs, courses, academic policies, and graduation requirements. "
                        "Please contact the FAIX office for access to the handbook."
                    )
            else:
                answer, context = process_conversation(user_message, context)
        
        # Update session context
        session.context = context
        session.save(update_fields=['context', 'updated_at'])
        
        # Save messages to database
        with transaction.atomic():
            # Save user message
            user_msg = Message.objects.create(
                conversation=conversation,
                role='user',
                content=user_message,
                intent=intent,
                confidence=confidence,
                entities=entities,
            )
            
            # Save bot response
            bot_msg = Message.objects.create(
                conversation=conversation,
                role='bot',
                content=answer,
                intent=intent,
                confidence=confidence,
            )
            
            # Update conversation
            conversation.updated_at = timezone.now()
            if not conversation.title or conversation.title == "New Conversation":
                # Set title from first user message
                conversation.title = user_message[:50] + ("..." if len(user_message) > 50 else "")
            conversation.save()
        
        return JsonResponse({
            'response': answer,
            'session_id': session.session_id,
            'conversation_id': conversation.id,
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'timestamp': timezone.now().isoformat(),
            'pdf_url': pdf_url,  # Add PDF URL to response
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_conversation_history(request):
    """
    Get conversation history for a session or conversation.
    
    Query parameters:
    - session_id: Get all conversations for a session
    - conversation_id: Get messages for a specific conversation
    - limit: Limit number of messages (default: 50)
    """
    session_id = request.GET.get('session_id')
    conversation_id = request.GET.get('conversation_id')
    limit = int(request.GET.get('limit', 50))
    
    if conversation_id:
        # Get messages for specific conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            messages = Message.objects.filter(conversation=conversation).order_by('timestamp')[:limit]
            
            messages_data = [{
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'intent': msg.intent,
                'confidence': msg.confidence,
            } for msg in messages]
            
            return JsonResponse({
                'conversation_id': conversation.id,
                'title': conversation.title,
                'messages': messages_data,
            })
        except Conversation.DoesNotExist:
            return JsonResponse({
                'error': 'Conversation not found'
            }, status=404)
    
    elif session_id:
        # Get all conversations for session
        try:
            session = UserSession.objects.get(session_id=session_id)
            conversations = Conversation.objects.filter(session=session).order_by('-created_at')
            
            conversations_data = [{
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'message_count': conv.messages.count(),
            } for conv in conversations]
            
            return JsonResponse({
                'session_id': session_id,
                'conversations': conversations_data,
            })
        except UserSession.DoesNotExist:
            return JsonResponse({
                'error': 'Session not found'
            }, status=404)
    
    else:
        return JsonResponse({
            'error': 'session_id or conversation_id is required'
        }, status=400)


@require_http_methods(["GET"])
def admin_dashboard_data(request):
    """
    Get analytics data for admin dashboard.
    
    Returns:
    {
        "total_conversations": 100,
        "total_messages": 500,
        "active_users": 25,
        "popular_queries": [...],
        "intent_distribution": {...}
    }
    """
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Get date range (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Total conversations
    total_conversations = Conversation.objects.count()
    
    # Total messages
    total_messages = Message.objects.count()
    
    # Active users (sessions with activity in last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    active_users = UserSession.objects.filter(
        updated_at__gte=seven_days_ago
    ).count()
    
    # Popular queries (most common intents)
    intent_distribution = Message.objects.filter(
        role='user',
        intent__isnull=False
    ).values('intent').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Popular queries (most frequent user messages)
    popular_queries = Message.objects.filter(
        role='user',
        timestamp__gte=thirty_days_ago
    ).values('content').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return JsonResponse({
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'active_users': active_users,
        'popular_queries': [
            {'query': item['content'], 'count': item['count']}
            for item in popular_queries
        ],
        'intent_distribution': {
            item['intent']: item['count']
            for item in intent_distribution
        },
    })


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def manage_knowledge_base(request):
    """
    CRUD operations for knowledge base entries.
    
    GET: List all FAQ entries (with optional filters)
    POST: Create new FAQ entry
    PUT: Update existing FAQ entry (requires id in body)
    DELETE: Delete FAQ entry (requires id in query params)
    """
    if request.method == 'GET':
        # List entries
        category = request.GET.get('category')
        search = request.GET.get('search')
        
        entries = FAQEntry.objects.filter(is_active=True)
        
        if category:
            entries = entries.filter(category=category)
        
        if search:
            entries = entries.filter(
                Q(question__icontains=search) |
                Q(answer__icontains=search) |
                Q(keywords__icontains=search)
            )
        
        entries_data = [{
            'id': entry.id,
            'question': entry.question,
            'answer': entry.answer,
            'category': entry.category,
            'keywords': entry.keywords,
            'view_count': entry.view_count,
            'helpful_count': entry.helpful_count,
        } for entry in entries[:100]]  # Limit to 100
        
        return JsonResponse({
            'entries': entries_data,
            'count': len(entries_data),
        })
    
    elif request.method == 'POST':
        # Create entry
        try:
            data = json.loads(request.body)
            entry = FAQEntry.objects.create(
                question=data.get('question'),
                answer=data.get('answer'),
                category=data.get('category', 'general'),
                keywords=data.get('keywords', ''),
            )
            
            # Refresh knowledge base
            knowledge_base.refresh()
            
            return JsonResponse({
                'id': entry.id,
                'message': 'FAQ entry created successfully',
            }, status=201)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    elif request.method == 'PUT':
        # Update entry
        try:
            data = json.loads(request.body)
            entry_id = data.get('id')
            
            if not entry_id:
                return JsonResponse({
                    'error': 'id is required'
                }, status=400)
            
            entry = FAQEntry.objects.get(id=entry_id)
            entry.question = data.get('question', entry.question)
            entry.answer = data.get('answer', entry.answer)
            entry.category = data.get('category', entry.category)
            entry.keywords = data.get('keywords', entry.keywords)
            entry.save()
            
            # Refresh knowledge base
            knowledge_base.refresh()
            
            return JsonResponse({
                'id': entry.id,
                'message': 'FAQ entry updated successfully',
            })
        except FAQEntry.DoesNotExist:
            return JsonResponse({
                'error': 'FAQ entry not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    elif request.method == 'DELETE':
        # Delete entry (soft delete)
        entry_id = request.GET.get('id')
        
        if not entry_id:
            return JsonResponse({
                'error': 'id is required'
            }, status=400)
        
        try:
            entry = FAQEntry.objects.get(id=entry_id)
            entry.is_active = False
            entry.save()
            
            # Refresh knowledge base
            knowledge_base.refresh()
            
            return JsonResponse({
                'message': 'FAQ entry deleted successfully',
            })
        except FAQEntry.DoesNotExist:
            return JsonResponse({
                'error': 'FAQ entry not found'
            }, status=404)


def index(request):
    """Serve the main HTML page"""
    from django.shortcuts import render
    return render(request, 'main.html')


def admin_dashboard(request):
    """Serve the admin dashboard page"""
    from django.shortcuts import render
    return render(request, 'admin.html')

