from django.http import HttpResponse
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
from .NLPModule.query_preprocessing import QueryProcessor
from .KnowledgeModule.knowledge_base import KnowledgeBase
from .ConversationModule.conversation_manager import process_conversation
import os
processor = QueryProcessor()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Initialize the KnowledgeBase globally
# 🚨 IMPORTANT: Replace 'path/to/your/faix_data.csv' with the actual file path 
# relative to your Django project's root or a fixed path.
KB_DATA_PATH = os.path.join(BASE_DIR, 'KnowledgeModule', 'faix_data.csv')
kb = None
try:
    kb = KnowledgeBase(KB_DATA_PATH)
    print(f"KnowledgeBase initialized successfully with data from {KB_DATA_PATH}!")
except FileNotFoundError:
    print(f"ERROR: Knowledge Base CSV file not found at {KB_DATA_PATH}. Check your path.")
    kb = None # Set to None to handle errors gracefully

def homepage(request):
    #return HttpResponse("Welcome to the chatbot!")
    return render(request,'main.html')

def about(request):
    return render(request,'index.html')

@method_decorator(csrf_exempt, name='dispatch') 
# NOTE: If you are having CSRF issues, uncomment the line above to disable CSRF protection 
# for testing. For production, properly handle the CSRF token.
class ChatbotAPIView(View):
    """
    Handles POST requests, manages conversation context via session, and routes 
    messages to the NLP/KB pipeline for factual answers.
    """
    
    def post(self, request, *args, **kwargs):
        user_message = request.POST.get('message', '').strip()
        
        # 1. Input Validation
        if not user_message:
            return JsonResponse({'response': 'Please enter a message.'}, status=400)
        
        # 2. KB Availability Check
        if kb is None:
            return JsonResponse({'response': 'The knowledge base is currently unavailable. Check server logs.'}, status=503)

        # 3. Retrieve Conversation Context from Django Session
        context_dict = request.session.get('chatbot_context', {})
        response = "" # Initialize response variable

        try:
            # 4. CRITICAL: RUN NLP/KB PIPELINE TO GET DATA
            
            # --- NLP Processing ---
            processed_data = processor.process_query(user_message)
            new_intent = processed_data.get('detected_intent', 'general_query')
            confidence = processed_data.get('confidence_score', 0.0)
            
            # --- Contextual Logic ---
            context_topic = context_dict.get('current_topic')
            
            # Decide which intent to use (New Intent or Context Topic)
            if new_intent == 'general_query' and context_topic:
                intent_to_use = context_topic
            else:
                intent_to_use = new_intent

            # --- Confidence Check and Conversation Manager Call ---
            if intent_to_use == 'general_query' or confidence < 0.2:
                # If confidence is low, run through the Conversation Manager for a graceful fallback
                final_response, final_context_dict = process_conversation(user_message, context_dict)
                response = final_response
            else:
                # 5. Knowledge Retrieval (The core answer fetch)
                response = kb.get_answer(intent_to_use, user_message)
                
                # Update context for the next question (since we got a high-confidence answer)
                context_dict['current_topic'] = intent_to_use

                # Run conversation manager AFTERWARDS to check for greetings/closings in the user message
                # This call is mainly to get the final_response/final_context_dict correctly
                final_response, final_context_dict = process_conversation(user_message, context_dict)


            # --- Response Finalization ---
            
            # Coerce final_response to an empty string if it's None for safe checking
            final_response_str = final_response if final_response is not None else ""
            
            # If the manager detected a closing or greeting, use its response. Otherwise, use the KB response.
            if "Thank you for using the FAIX Chatbot!" in final_response_str or "Hello! I'm the FAIX Chatbot" in final_response_str:
                 response = final_response # Use the greeting/closing message

        except Exception as e:
            # Catch any unexpected runtime errors
            print(f"CRITICAL ERROR: {e}")
            final_context_dict = context_dict # Preserve context if possible
            response = 'An unexpected error occurred while processing your request. Please notify support.'

        # 6. Save the updated conversation context to the session
        # Use final_context_dict if available, otherwise use the initialized context_dict
        request.session['chatbot_context'] = final_context_dict if 'final_context_dict' in locals() else context_dict
        
        # 7. Return Final Response
        return JsonResponse({
            'response': response
        })