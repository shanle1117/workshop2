from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Import your modules
from chatbot.NLP_Module.query_preprocessing import QueryProcessor
from chatbot.Conversation_Module.conversation_manager import process_conversation
from chatbot.Knowledge_Module.knowledge_base import KnowledgeBase


# Initialize chatbot modules (only once)
kb = KnowledgeBase("chatbot/Knowledge_Module/faix_data.csv")

qp = QueryProcessor()

# Render the interface
def chatbot_view(request):
    return render(request, 'chatbot/main.html')


# API endpoint for AJAX
@csrf_exempt
def chatbot_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        # Here we pass the user message to process_conversation
        response, context = process_conversation(user_message)

        return JsonResponse({"reply": response})

    return JsonResponse({"error": "Invalid request"}, status=400)
