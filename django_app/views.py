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
from src.llm_client import get_llm_client, LLMError
from src.agents import get_agent, retrieve_for_agent, check_staff_data_available, check_schedule_data_available, _get_staff_documents, _get_schedule_documents
from src.prompt_builder import build_messages

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
        "user_id": "optional user id",
        "agent_id": "optional conversational agent id (e.g., 'faq', 'schedule', 'staff')",
        "history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
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
        agent_id = data.get('agent_id')
        history = data.get('history') or []
        
        if not user_message:
            return JsonResponse({
                'error': 'Message is required'
            }, status=400)
        
        # Get or create session
        session = get_or_create_session(session_id, user_id)
        
        # Get or create conversation
        conversation = get_or_create_conversation(session, user_id)
        
        # Get context from session
        context = session.context if session.context else {}
        
        # Detect handbook-style queries for PDF handling
        pdf_url = None
        user_message_lower = user_message.lower()
        is_handbook_query = (
            'handbook' in user_message_lower or
            'academic handbook' in user_message_lower
        )

        # STEP 1: Check data availability FIRST before NLP processing
        # This ensures we route to agents that have data available
        # NOTE: Frontend may send agent_id='faq' by default, but we override if query matches staff/schedule
        print(f"DEBUG: Initial agent_id from request: {agent_id}")
        print(f"DEBUG: User message: '{user_message}'")
        print(f"DEBUG: User message (lowercase): '{user_message_lower}'")
        
        # Always check for staff/schedule keywords and override agent_id if appropriate
        # (even if frontend sent a default agent_id like 'faq')
        
        # Check for staff-related keywords and verify staff data exists
        staff_keywords = [
            'contact', 'email', 'phone', 'professor', 'lecturer', 'staff', 'faculty', 
            'who can i', 'who can', 'reach', 'get in touch', 'call', 'number', 
            'office', 'address', 'dean', 'head of', 'department head', 'ai', 'artificial intelligence',
            'cybersecurity', 'data science', 'machine learning', 'nlp', 'deep learning'
        ]
        matched_keywords = [kw for kw in staff_keywords if kw in user_message_lower]
        print(f"DEBUG: Staff keyword matching - Matched: {matched_keywords}")
        
        if matched_keywords:
            # Check if staff data actually exists
            staff_available = check_staff_data_available()
            print(f"DEBUG: Staff data available check: {staff_available}")
            if staff_available:
                staff_docs = _get_staff_documents()  # Get actual docs for logging
                agent_id = 'staff'  # OVERRIDE any default agent_id from frontend
                print(f"DEBUG: Data-first routing - Found {len(staff_docs)} staff members, OVERRIDING to staff agent")
                print(f"DEBUG: Matched keywords: {matched_keywords}")
            else:
                print(f"DEBUG: Staff keywords detected but no staff data found in data/staff_contacts.json")
        else:
            print(f"DEBUG: No staff keywords matched in query")
        
        # Check for schedule-related keywords and verify schedule data exists
        if agent_id != 'staff':  # Don't override if we already set staff
            schedule_keywords = ['schedule', 'timetable', 'calendar', 'when', 'time', 'date', 'semester', 'deadline']
            if any(kw in user_message_lower for kw in schedule_keywords):
                if check_schedule_data_available():
                    schedule_docs = _get_schedule_documents()  # Get actual docs for logging
                    agent_id = 'schedule'  # OVERRIDE any default agent_id from frontend
                    print(f"DEBUG: Data-first routing - Found schedule data, OVERRIDING to schedule agent")
        
        # STEP 2: Process query with NLP (as secondary check/confirmation)
        processed_query = query_processor.process_query(user_message)
        intent = processed_query.get('detected_intent', 'general_query')
        confidence = processed_query.get('confidence_score', 0.0)
        entities = processed_query.get('extracted_entities', {})
        
        # Use NLP intent as confirmation if agent not already set by data-first routing
        if not agent_id:
            print(f"DEBUG: No agent set from data-first routing, checking NLP intent: '{intent}'")
            # Map intents to agent IDs
            intent_to_agent = {
                'staff_contact': 'staff',
                'academic_schedule': 'schedule',
                'program_info': 'faq',  # Route program queries to FAQ (has FAIX data)
                'course_info': 'faq',   # Route course queries to FAQ (has FAIX data)
                'facility_info': 'faq', # Route facility queries to FAQ (has FAIX data)
                'fees': 'faq',          # Route fee queries to FAQ (has fee information)
                # For other intents, use 'faq' agent or keep None for fallback
            }
            agent_id = intent_to_agent.get(intent)
            
            # Check for program/admission/facility keywords and route to FAQ agent
            if not agent_id:
                faix_keywords = [
                    'program', 'programme', 'degree', 'course', 'admission', 'admit',
                    'facility', 'facilities', 'department', 'departments', 'vision', 'mission',
                    'undergraduate', 'postgraduate', 'master', 'bachelor', 'research',
                    'key highlight', 'objective', 'objectives', 'fee', 'fees', 'tuition',
                    'yuran', 'bayaran', 'diploma fee', 'degree fee', 'payment', 'cost'
                ]
                if any(kw in user_message_lower for kw in faix_keywords):
                    # Check if FAIX data is available
                    from src.agents import check_faix_data_available
                    if check_faix_data_available():
                        agent_id = 'faq'
                        print(f"DEBUG: Keyword-based routing - FAIX keywords detected, routing to FAQ agent with comprehensive FAIX data")
            
            if agent_id:
                print(f"DEBUG: NLP-based routing - Intent '{intent}' mapped to agent '{agent_id}'")
            else:
                print(f"DEBUG: No agent mapping for intent '{intent}', will use default behavior")
        
        # Final check: if still no agent_id and we have staff keywords, force staff agent
        if not agent_id and any(kw in user_message_lower for kw in ['contact', 'who can', 'email', 'phone', 'professor', 'staff']):
            if check_staff_data_available():
                agent_id = 'staff'
                print(f"DEBUG: Final fallback - Forcing staff agent based on keywords and data availability")
        
        print(f"DEBUG: Final agent_id before processing: {agent_id}")

        # Normalise history into a compact, safe format
        history_messages = []
        if isinstance(history, list):
            for turn in history[-10:]:  # keep last 10 turns at most
                if not isinstance(turn, dict):
                    continue
                role = turn.get('role')
                content = turn.get('content')
                if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
                    history_messages.append({'role': role, 'content': content.strip()})

        # Agent-based path: use LLM + RAG when an agent_id is provided
        if agent_id:
            agent = get_agent(agent_id)
            if not agent:
                return JsonResponse(
                    {'error': f"Unknown agent_id '{agent_id}'"},
                    status=400,
                )

            # Retrieve context for the agent (FAQ, schedule, staff, etc.)
            agent_context = retrieve_for_agent(
                agent_id=agent_id,
                user_text=user_message,
                knowledge_base=knowledge_base,
                intent=intent,
                top_k=3,
            )
            
            # Debug: Log staff context if available
            if agent_id == 'staff':
                staff_docs = agent_context.get('staff', [])
                print(f"DEBUG: Staff agent - Loaded {len(staff_docs)} staff members")
                if staff_docs:
                    print(f"DEBUG: First staff member: {staff_docs[0].get('name', 'N/A')}")

            # Build LLM messages and call Llama via Ollama
            messages = build_messages(
                agent=agent,
                user_message=user_message,
                history=history_messages,
                context=agent_context,
                intent=intent,
            )
            
            # Debug: Print message count and check if staff context is in messages
            if agent_id == 'staff':
                print(f"DEBUG: Built {len(messages)} messages for LLM")
                for i, msg in enumerate(messages):
                    if 'Staff Contacts Context' in msg.get('content', ''):
                        print(f"DEBUG: Staff context found in message {i}")

            try:
                # Check if this is a fee query - if so, return link directly without calling LLM
                fee_keywords = ['fee', 'fees', 'tuition', 'yuran', 'bayaran', 'diploma fee', 'degree fee', 'cost', 'payment']
                is_fee_query = intent == 'fees' or any(kw in user_message_lower for kw in fee_keywords)
                
                if is_fee_query:
                    print(f"DEBUG: Fee query detected - returning link directly")
                    answer = "https://bendahari.utem.edu.my/ms/jadual-yuran-pelajar.html"
                else:
                    llm_client = get_llm_client()
                    print(f"DEBUG: Calling LLM with agent '{agent_id}'")
                    
                    # Increased max_tokens to allow well-formatted, summarized responses with line breaks
                    max_tokens = 400 if agent_id == 'staff' else 600
                    llm_response = llm_client.chat(messages, max_tokens=max_tokens, temperature=0.3)
                    answer = llm_response.content
                    print(f"DEBUG: LLM response length: {len(answer) if answer else 0} characters")
                
                # Fallback: If LLM returns empty or very short response for staff queries, use staff data directly
                if agent_id == 'staff' and (not answer or len(answer.strip()) < 20):
                    staff_docs = agent_context.get('staff', [])
                    if staff_docs:
                        print("DEBUG: LLM response too short, generating fallback from staff data")
                        # Filter staff by query keywords if possible
                        query_words = set(user_message_lower.split())
                        relevant_staff = []
                        for staff in staff_docs:
                            staff_text = ' '.join([
                                staff.get('name', '').lower(),
                                staff.get('department', '').lower(),
                                staff.get('specialization', '').lower(),
                                staff.get('keywords', '').lower()
                            ])
                            if any(word in staff_text for word in query_words if len(word) > 2):
                                relevant_staff.append(staff)
                        
                        if not relevant_staff:
                            relevant_staff = staff_docs[:3]  # Show first 3 if no match
                        
                        answer_parts = ["Here are some staff members you can contact:\n"]
                        for staff in relevant_staff[:5]:  # Limit to 5
                            if staff.get('name'):
                                answer_parts.append(f"• {staff['name']}")
                        
                        answer_parts.append("")
                        answer_parts.append("Would you like contact information (email, phone, office) for any of these staff members?")
                        answer = '\n'.join(answer_parts)
            except LLMError as e:
                print(f"LLMError in chat_api: {e}")
                # Fallback to staff data if available
                if agent_id == 'staff':
                    staff_docs = agent_context.get('staff', [])
                    if staff_docs:
                        print("DEBUG: LLM failed, using fallback from staff data")
                        answer = "Here are some staff members you can contact:\n\n"
                        for staff in staff_docs[:5]:
                            if staff.get('name'):
                                answer += f"• {staff.get('name')}\n"
                        answer += "\nWould you like contact information (email, phone, office) for any of these staff members?"
                    else:
                        answer = (
                            "I'm having trouble reaching the AI assistant right now. "
                            "Please try again in a moment or contact the FAIX office for help."
                        )
                else:
                    answer = (
                        "I'm having trouble reaching the AI assistant right now. "
                        "Please try again in a moment or contact the FAIX office for help."
                    )
            except Exception as e:
                print(f"Unexpected error in chat_api LLM path: {e}")
                # Fallback to staff data if available
                if agent_id == 'staff':
                    staff_docs = agent_context.get('staff', [])
                    if staff_docs:
                        print("DEBUG: Exception occurred, using fallback from staff data")
                        answer = "Here are some staff members you can contact:\n\n"
                        for staff in staff_docs[:5]:
                            if staff.get('name'):
                                answer += f"• {staff.get('name')}\n"
                        answer += "\nWould you like contact information (email, phone, office) for any of these staff members?"
                    else:
                        answer = (
                            "An unexpected error occurred while generating a response. "
                            "Please try again or contact the FAIX office for assistance."
                        )
                else:
                    answer = (
                        "An unexpected error occurred while generating a response. "
                        "Please try again or contact the FAIX office for assistance."
                    )

            # For handbook queries, still attach PDF information if available
            if intent == 'program_info' or is_handbook_query:
                import os
                from django.conf import settings
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
                if os.path.exists(pdf_path):
                    pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
                else:
                    answer += (
                        "\n\n📚 The Academic Handbook contains detailed program information, "
                        "but I couldn't find a copy on this system. Please contact the FAIX "
                        "office for access to the handbook."
                    )

        else:
            # Existing non-agent behaviour (no LLM)
            # Check if this is a fee query first - return link directly
            fee_keywords = ['fee', 'fees', 'tuition', 'yuran', 'bayaran', 'diploma fee', 'degree fee', 'cost', 'payment']
            is_fee_query = intent == 'fees' or any(kw in user_message_lower for kw in fee_keywords)
            
            if is_fee_query:
                print(f"DEBUG: Fee query detected (non-agent path) - returning link directly")
                answer = "https://bendahari.utem.edu.my/ms/jadual-yuran-pelajar.html"
            elif intent and intent != 'general_query':
                answer = knowledge_base.get_answer(intent, user_message)
                
                # Validate answer is not None, empty, or invalid type
                if not answer or not isinstance(answer, str) or not answer.strip():
                    answer = (
                        "I couldn't find the exact information for your query. "
                        "Try asking about course info, registration, staff contacts, or program information."
                    )
                
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
                    # Validate answer from conversation manager
                    if not answer or not isinstance(answer, str) or not answer.strip():
                        answer = (
                            "I'm sorry, I couldn't process your query. "
                            "Could you please rephrase your question?"
                        )
        
        # Final safety check: ensure answer is never None or empty before saving
        if not answer or not isinstance(answer, str) or not answer.strip():
            answer = (
                "I apologize, but I'm having trouble processing your request. "
                "Please try rephrasing your question or contact the FAIX office for assistance."
            )
        
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
    return render(request, 'index.html')


def admin_dashboard(request):
    """Serve the admin dashboard page"""
    from django.shortcuts import render
    return render(request, 'admin.html')

