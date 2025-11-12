"""
Conversation Management Module for AI Chatbot Assistance for Students (FAIX).

This module handles conversation context, topic tracking, and user intent detection
using a rule-based approach. It manages conversation flow and provides appropriate
responses based on detected topics and fallback mechanisms.

Features:
- Conversation context and history management
- Topic detection (registration, contact, farewell)
- Fallback responses for unclear inputs
- Follow-up question handling within the same context
- Integration-ready for NLP and Knowledge Base modules
"""

from typing import Optional


def detect_intent(user_message: str) -> Optional[str]:
    """
    Detects user intent from the message content using keyword matching.
    
    This is a simple rule-based approach. In the future, this can be replaced
    with an NLP module (e.g., intent classification from Nex's NLP module).
    
    Args:
        user_message: The user's input text.
        
    Returns:
        The detected topic/intent as a string, or None if no clear intent is found.
    """
    user_message_lower = user_message.lower().strip()
    
    # Keywords for different intents
    registration_keywords = ["register", "registration", "course", "subject", "enroll", "enrollment"]
    contact_keywords = ["contact", "office", "email", "phone", "staff", "reach", "address"]
    farewell_keywords = ["thanks", "thank", "bye", "goodbye", "see you", "quit", "exit"]
    
    # Check for registration-related intent
    if any(keyword in user_message_lower for keyword in registration_keywords):
        return "registration"
    
    # Check for contact-related intent
    if any(keyword in user_message_lower for keyword in contact_keywords):
        return "contact"
    
    # Check for farewell intent
    if any(keyword in user_message_lower for keyword in farewell_keywords):
        return "farewell"
    
    # No clear intent detected
    return None


def handle_registration_query(user_message: str, context: dict) -> str:
    """
    Handles queries related to course registration and enrollment.
    
    Args:
        user_message: The user's input text.
        context: The conversation context dictionary.
        
    Returns:
        An appropriate response about registration.
    """
    user_message_lower = user_message.lower()
    
    # Check for specific sub-questions within registration topic
    if any(word in user_message_lower for word in ["when", "date", "time", "deadline"]):
        return (
            "📅 Registration typically opens at the beginning of each semester. "
            "For specific dates, please check the official FAIX schedule at our website "
            "or contact the registrar's office. Is there anything else about registration?"
        )
    elif any(word in user_message_lower for word in ["how", "form", "process", "step"]):
        return (
            "📝 To register for courses, you'll need to:\n"
            "1. Log into your student portal\n"
            "2. Navigate to 'Course Registration'\n"
            "3. Select your desired courses\n"
            "4. Confirm and submit your registration\n\n"
            "For detailed instructions, please contact the registration office. Need help?"
        )
    elif any(word in user_message_lower for word in ["requirement", "prerequisite", "condition"]):
        return (
            "✅ Course requirements vary by program. Please refer to your course catalog "
            "or speak with your academic advisor for prerequisite information."
        )
    else:
        return (
            "💡 I can help you with registration questions. "
            "Would you like to know about registration dates, the registration process, or course requirements?"
        )


def handle_contact_query(user_message: str, context: dict) -> str:
    """
    Handles queries related to contacting FAIX staff and services.
    
    Args:
        user_message: The user's input text.
        context: The conversation context dictionary.
        
    Returns:
        Contact information or appropriate guidance.
    """
    user_message_lower = user_message.lower()
    
    # Check for specific contact-related sub-questions
    if any(word in user_message_lower for word in ["email", "mail"]):
        return (
            "📧 For email inquiries, please contact the FAIX administrative office. "
            "You can find staff email addresses in our directory on the FAIX website."
        )
    elif any(word in user_message_lower for word in ["phone", "call", "number"]):
        return (
            "☎️ For phone inquiries, please call the FAIX main office. "
            "The contact number is available on our website."
        )
    elif any(word in user_message_lower for word in ["office", "location", "address", "visit"]):
        return (
            "🏢 The FAIX offices are located on the UTeM campus. "
            "For specific office locations and visiting hours, please visit the FAIX website."
        )
    else:
        return (
            "📞 I can help you find contact information for FAIX staff. "
            "Would you like email addresses, phone numbers, or office locations?"
        )


def handle_greeting(user_message: str) -> str:
    """
    Handles greeting messages from the user.
    
    Args:
        user_message: The user's input text.
        
    Returns:
        A friendly greeting response.
    """
    return (
        "👋 Hello! Welcome to FAIX AI Chatbot. I'm here to help you with questions about "
        "course registration, staff contacts, schedules, and other student inquiries. "
        "How can I assist you today?"
    )


def handle_fallback() -> str:
    """
    Provides a polite fallback response when intent cannot be determined.
    
    Returns:
        A fallback message requesting clarification.
    """
    return (
        "🤔 I'm sorry, I didn't quite understand your question. "
        "Could you please clarify what you'd like to know? "
        "I can help with registration, contact information, schedules, and more."
    )


def update_context(user_message: str, context: dict, detected_intent: Optional[str]) -> dict:
    """
    Updates the conversation context based on the detected intent and user message.
    
    This maintains conversation continuity by tracking:
    - Current topic
    - Previous messages
    - Last interaction timestamp information
    
    Args:
        user_message: The user's input text.
        context: The existing conversation context.
        detected_intent: The detected intent from the user message.
        
    Returns:
        Updated context dictionary.
    """
    updated_context = context.copy()
    
    # Track conversation history (limit to last 5 messages for memory efficiency)
    if "history" not in updated_context:
        updated_context["history"] = []
    
    updated_context["history"].append({"user": user_message})
    
    if len(updated_context["history"]) > 10:  # Keep last 10 exchanges
        updated_context["history"] = updated_context["history"][-10:]
    
    # Update current topic if intent is detected
    if detected_intent and detected_intent != "farewell":
        updated_context["current_topic"] = detected_intent
        updated_context["last_question"] = user_message
    elif detected_intent == "farewell":
        # Clear context on farewell
        updated_context = {}
    
    return updated_context


def process_conversation(user_message: str, context: dict) -> tuple[str, dict]:
    """
    Processes the user input, updates context, and returns chatbot response + updated context.
    
    This is the main function that orchestrates the conversation management module.
    
    Args:
        user_message: The latest text entered by the user.
        context: A dictionary that keeps track of current topic, last question, etc.
        
    Returns:
        A tuple containing:
        - response: The chatbot's response string.
        - updated_context: The updated conversation context dictionary.
        
    Logic Flow:
        1. Detect user intent from keywords
        2. Route to appropriate handler based on intent
        3. Update conversation context
        4. Return response and updated context
        
    Integration Notes:
        - Currently uses keyword-based intent detection
        - Can be extended with NLP intent classifier (e.g., from transformer models)
        - Can integrate with Knowledge Base module for retrieving specific information
        - Ready to be called from Django views in the web application
    """
    # Handle empty input
    if not user_message or not user_message.strip():
        return handle_fallback(), context
    
    # Detect user intent from the message
    detected_intent = detect_intent(user_message)
    
    # Route to appropriate handler based on detected intent
    if detected_intent == "registration":
        response = handle_registration_query(user_message, context)
    
    elif detected_intent == "contact":
        response = handle_contact_query(user_message, context)
    
    elif detected_intent == "farewell":
        response = (
            "👋 Thank you for using FAIX AI Chatbot! "
            "Have a great day, and feel free to reach out anytime you need help!"
        )
    
    elif detected_intent is None:
        # Check if this is a greeting-like message
        greeting_keywords = ["hi", "hello", "hey", "greetings", "help"]
        if any(keyword in user_message.lower() for keyword in greeting_keywords) and len(user_message) < 20:
            response = handle_greeting(user_message)
        else:
            # If there's a previous context and current topic, try to maintain continuity
            if context.get("current_topic"):
                if context["current_topic"] == "registration":
                    response = handle_registration_query(user_message, context)
                elif context["current_topic"] == "contact":
                    response = handle_contact_query(user_message, context)
                else:
                    response = handle_fallback()
            else:
                response = handle_fallback()
    
    else:
        # Fallback for any unhandled intent
        response = handle_fallback()
    
    # Update context with the new interaction
    updated_context = update_context(user_message, context, detected_intent)
    
    # Add response to history for reference
    if "history" not in updated_context:
        updated_context["history"] = []
    updated_context["history"][-1]["bot"] = response
    
    return response, updated_context


# ============================================================================
# Test Section - Example Conversation Flow
# ============================================================================

if __name__ == "__main__":
    """
    Demonstrates the conversation manager with example conversation flows.
    """
    print("=" * 70)
    print("FAIX AI Chatbot - Conversation Manager Test")
    print("=" * 70)
    
    # Test Case 1: Registration flow
    print("\n📌 Test Case 1: Registration Topic Flow")
    print("-" * 70)
    context = {}
    messages_1 = [
        "Hi",
        "I want to register",
        "When is registration open?",
        "How about the form?",
        "Thank you"
    ]
    
    for msg in messages_1:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print()
    
    # Test Case 2: Contact information flow
    print("\n📌 Test Case 2: Contact Information Flow")
    print("-" * 70)
    context = {}
    messages_2 = [
        "Hello",
        "Can I contact the registration office?",
        "What's their email?",
        "Bye"
    ]
    
    for msg in messages_2:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print()
    
    # Test Case 3: Unclear input handling
    print("\n📌 Test Case 3: Fallback Response for Unclear Input")
    print("-" * 70)
    context = {}
    messages_3 = [
        "What about the weather?",
        "Tell me something random",
        "How do courses work?",  # Relates to registration topic
    ]
    
    for msg in messages_3:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print()
    
    # Test Case 4: Context continuity
    print("\n📌 Test Case 4: Context Continuity Within Same Topic")
    print("-" * 70)
    context = {}
    messages_4 = [
        "I need help with registration",
        "How do I do it?",
        "What are the requirements?"
    ]
    
    for msg in messages_4:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        if "current_topic" in context:
            print(f"[Context - Current Topic: {context['current_topic']}]")
        print()
    
    print("=" * 70)
    print("Test completed!")
    print("=" * 70)
