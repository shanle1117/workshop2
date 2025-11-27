"""
Conversation Management Module for FAIX AI Chatbot

This module manages conversation context, detects user intent through rule-based
topic detection, and maintains conversation continuity for follow-up questions.
It uses a simple rule-based approach with placeholder comments for future NLP
integration (e.g., from the NLP module).

Author: FAIX Chatbot Team
Date: November 2025
"""

from typing import Optional


class ConversationContext:
    """
    Manages conversation context including topic, history, and conversation state.
    """

    def __init__(self):
        """Initialize conversation context with default values."""
        self.current_topic: Optional[str] = None
        self.last_question: Optional[str] = None
        self.conversation_history: list[dict] = []
        self.session_active: bool = True

    def update_topic(self, new_topic: str) -> None:
        """Update the current conversation topic."""
        self.current_topic = new_topic

    def update_last_question(self, question: str) -> None:
        """Store the last user question for context continuity."""
        self.last_question = question

    def add_to_history(self, user_msg: str, bot_response: str) -> None:
        """Add exchange to conversation history."""
        self.conversation_history.append({
            "user": user_msg,
            "bot": bot_response
        })

    def clear_context(self) -> None:
        """Clear conversation context (used for goodbye or session end)."""
        self.current_topic = None
        self.last_question = None
        self.conversation_history = []
        self.session_active = False

    def to_dict(self) -> dict:
        """Convert context to dictionary for serialization or Django integration."""
        return {
            "current_topic": self.current_topic,
            "last_question": self.last_question,
            "conversation_history": self.conversation_history,
            "session_active": self.session_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationContext":
        """Create ConversationContext from dictionary (e.g., from Django session)."""
        context = cls()
        context.current_topic = data.get("current_topic")
        context.last_question = data.get("last_question")
        context.conversation_history = data.get("conversation_history", [])
        context.session_active = data.get("session_active", True)
        return context


def detect_topic(user_message: str) -> Optional[str]:
    """
    Detect user intent/topic from message using rule-based keyword matching.

    This is a simple rule-based approach. In the future, this can be replaced
    with NLP intent detection (e.g., from an NLP module with intent classifiers).

    Args:
        user_message: The user's input text.

    Returns:
        Detected topic (e.g., "registration", "contact") or None if unclear.
    """
    # Normalize message to lowercase for case-insensitive matching
    message_lower = user_message.lower()

    # Define keyword patterns for each topic
    registration_keywords = ["register", "course", "subject", "enrollment", "registration"]
    contact_keywords = ["contact", "office", "email", "phone", "address", "staff"]
    general_keywords = ["hi", "hello", "hey", "help"]

    # Topic detection logic
    # TODO: Replace with NLP intent classification when NLP module is integrated
    if any(keyword in message_lower for keyword in registration_keywords):
        return "registration"

    if any(keyword in message_lower for keyword in contact_keywords):
        return "contact"

    if any(keyword in message_lower for keyword in general_keywords):
        return "general"

    return None


def is_closing_message(user_message: str) -> bool:
    """
    Check if the user message indicates end of conversation.

    Args:
        user_message: The user's input text.

    Returns:
        True if message contains closing keywords, False otherwise.
    """
    closing_keywords = ["thanks", "thank you", "bye", "goodbye", "see you"]
    message_lower = user_message.lower()
    return any(keyword in message_lower for keyword in closing_keywords)


def get_response_for_topic(topic: str, user_message: str) -> str:
    """
    Generate a contextual response based on detected topic.

    This function can be extended to integrate with the Knowledge Base module
    for retrieving dynamic responses.

    Args:
        topic: The detected conversation topic.
        user_message: The original user message (for context).

    Returns:
        A relevant response string.
    """
    # TODO: Integrate with Knowledge Base module (knowledge_base.py)
    # to fetch dynamic responses based on topic and context

    if topic == "registration":
        # Check if it's a follow-up or initial question
        if any(word in user_message.lower() for word in ["when", "time", "date", "open"]):
            return (
                "📅 Registration details vary by semester. "
                "Please check the course information or contact the Student Affairs Office for exact dates. "
                "Is there a specific course or deadline you're asking about?"
            )
        else:
            return (
                "🎓 For course registration, you'll need to access the student portal with your credentials. "
                "Do you have questions about specific courses or registration procedures?"
            )

    elif topic == "contact":
        # Provide contact information (can be integrated with staff_contacts.json)
        return (
            "📞 You can reach FAIX administration:\n"
            "• Email: contact@faix.utem.edu.my\n"
            "• Office: Building A, Room 305\n"
            "• Phone: +60-3-8312-5250 ext. 305\n"
            "What specific information do you need?"
        )

    elif topic == "general":
        return (
            "👋 Hello! I'm the FAIX Chatbot Assistant. "
            "I can help you with course registration, contact information, FAQs, and schedules. "
            "What would you like to know?"
        )

    return None


def get_fallback_response() -> str:
    """
    Generate a polite fallback response for unclear inputs.

    Returns:
        A helpful fallback message prompting for clarification.
    """
    return (
        "I'm sorry, I didn't quite understand your question. 🤔\n"
        "Could you please clarify what you need help with? "
        "I can assist with:\n"
        "• Course registration\n"
        "• Contact information\n"
        "• FAQs and schedules\n"
        "• General information"
    )


def get_closing_response() -> str:
    """
    Generate a polite closing message.

    Returns:
        A friendly goodbye message.
    """
    return (
        "Thank you for using the FAIX Chatbot! 😊\n"
        "If you have more questions later, feel free to reach out. Have a great day!"
    )


def process_conversation(
    user_message: str,
    context: Optional[dict] = None
) -> tuple[str, dict]:
    """
    Process user input, detect intent, maintain context, and generate response.

    This is the main entry point for conversation processing. It handles:
    1. Topic detection from user message
    2. Context maintenance for follow-up questions
    3. Fallback handling for unclear inputs
    4. Conversation closure

    Args:
        user_message: The latest text entered by the user.
        context: A dictionary with conversation state (topic, history, etc.).
                If None, a new context is created.

    Returns:
        tuple: (chatbot_response, updated_context_dict)
               - response: String containing the chatbot's reply
               - updated_context: Dictionary with updated conversation state

    Example:
        >>> context = {}
        >>> response, context = process_conversation("Hi", context)
        >>> response, context = process_conversation("I want to register", context)
        >>> print(response)
    """
    # Initialize or convert context to ConversationContext object
    if isinstance(context, dict):
        if not context:
            conversation_context = ConversationContext()
        else:
            conversation_context = ConversationContext.from_dict(context)
    else:
        conversation_context = ConversationContext()

    # Validate input
    if not user_message or not user_message.strip():
        response = "I didn't receive your message. Could you please try again?"
        return response, conversation_context.to_dict()

    # Store the current question for context continuity
    conversation_context.update_last_question(user_message)

    # Check if user is closing the conversation
    if is_closing_message(user_message):
        response = get_closing_response()
        conversation_context.clear_context()
        conversation_context.add_to_history(user_message, response)
        return response, conversation_context.to_dict()

    # Detect topic from current message
    detected_topic = detect_topic(user_message)

    # Handle topic detection and context management
    if detected_topic:
        # Update or maintain conversation topic
        conversation_context.update_topic(detected_topic)
        response = get_response_for_topic(detected_topic, user_message)
    else:
        # If no topic detected, check if we're in an active conversation
        if conversation_context.current_topic:
            # User might be asking a follow-up within the same topic
            response = get_response_for_topic(
                conversation_context.current_topic,
                user_message
            )
        else:
            # No context and no clear intent → use fallback
            response = get_fallback_response()

    # Add exchange to conversation history
    conversation_context.add_to_history(user_message, response)

    # Return response and updated context
    return response, conversation_context.to_dict()


# ============================================================================
# Test Section: Example Conversation Flow
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("FAIX AI Chatbot - Conversation Manager Test")
    print("=" * 70)
    print()

    # Test Case 1: Basic conversation flow
    print("📝 Test Case 1: Basic Conversation Flow")
    print("-" * 70)
    context = {}
    test_messages = [
        "Hi",
        "I want to register for a course",
        "When is registration open?",
        "Thank you so much"
    ]

    for msg in test_messages:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print()

    # Test Case 2: Contact inquiry
    print("\n📝 Test Case 2: Contact Inquiry")
    print("-" * 70)
    context = {}
    test_messages = [
        "Can I get contact information?",
        "What's the phone number?",
        "Bye"
    ]

    for msg in test_messages:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print()

    # Test Case 3: Unclear input with fallback
    print("\n📝 Test Case 3: Unclear Input (Fallback)")
    print("-" * 70)
    context = {}
    test_messages = [
        "xyz123abc",
        "Um... I'm not sure",
        "Actually, I need to register"
    ]

    for msg in test_messages:
        reply, context = process_conversation(msg, context)
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print()

    # Test Case 4: Context continuity
    print("\n📝 Test Case 4: Context Continuity (Follow-up Questions)")
    print("-" * 70)
    context = {}
    test_messages = [
        "What courses are available?",
        "What about the deadlines?",
        "And the registration form?",
        "Thanks!"
    ]

    for msg in test_messages:
        reply, context = process_conversation(msg, context)
        current_topic = context.get("current_topic", "None")
        print(f"User: {msg}")
        print(f"Bot: {reply}")
        print(f"[Current Topic: {current_topic}]")
        print()

    print("=" * 70)
    print("✅ All test cases completed!")
    print("=" * 70)
