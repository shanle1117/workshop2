# 🤖 FAIX AI Chatbot Assistance for Students

An intelligent conversational AI system designed to assist students at the Faculty of Artificial Intelligence and Cyber Security (FAIX), UTeM. The chatbot handles inquiries about course registration, staff contacts, schedules, and other student services.

---

## 📑 Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Module Documentation](#module-documentation)
- [Usage Examples](#usage-examples)
- [Architecture](#architecture)
- [Integration Guide](#integration-guide)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

---

## 📋 Project Overview

The FAIX AI Chatbot is a multi-module system that provides intelligent student assistance through conversational interactions. It combines natural language processing, knowledge base retrieval, and conversation management to deliver relevant and helpful responses to student inquiries.

### Key Goals:
- ✅ Reduce student support burden on staff
- ✅ Provide 24/7 availability for student inquiries
- ✅ Maintain conversation context and continuity
- ✅ Integrate seamlessly with existing university systems
- ✅ Handle various student query types (registration, contacts, schedules)

---

## 🎯 Features

### Core Features:
- **Conversation Management**: Maintains context and topic tracking across multiple turns
- **Intent Detection**: Rule-based keyword detection (easily replaceable with NLP)
- **Multi-Topic Support**: 
  - 📚 Course Registration
  - 📞 Staff Contacts
  - 📅 Schedules & Deadlines
  - 👋 Polite Farewells
- **Fallback Handling**: Gracefully handles unclear or ambiguous inputs
- **Context Continuity**: Remembers previous topics and questions
- **Django Integration**: Ready-to-use with Django web framework
- **Extensible Architecture**: Easy to integrate NLP modules and knowledge base systems

---

## 📂 Project Structure

```
workshop2/
├── README.md                          # 📖 Project documentation (this file)
├── conversation_manager.py            # 💬 Conversation Management Module
├── knowledge_base.py                  # 🧠 Knowledge Base Module
├── test_chatbot.py                    # ✅ Test Suite
│
├── main.html                          # 🌐 Frontend UI
├── style.css                          # 🎨 Styling
│
├── course_info.json                   # 📚 Course Information Data
├── schedule.json                      # 📅 Schedule Data
├── faqs.json                          # ❓ FAQ Data
├── staff_contacts.json                # 📇 Staff Contact Data
├── faix_data.csv                      # 📊 FAIX General Data
│
└── [Django App Structure - To be added]
    ├── views.py                       # Django views
    ├── urls.py                        # URL routing
    └── settings.py                    # Configuration
```

### File Descriptions:

| File | Purpose |
|------|---------|
| `conversation_manager.py` | Manages conversation flow, context, and intent detection |
| `knowledge_base.py` | Stores and retrieves information from JSON/CSV data files |
| `test_chatbot.py` | Unit tests for chatbot functionality |
| `main.html` | Web interface for the chatbot |
| `style.css` | CSS styling for the web interface |
| `course_info.json` | Course details and information |
| `schedule.json` | Academic schedules and deadlines |
| `faqs.json` | Frequently asked questions and answers |
| `staff_contacts.json` | Staff directory and contact information |
| `faix_data.csv` | General FAIX faculty information |

---

## 🚀 Installation & Setup

### Prerequisites:
- Python 3.10 or higher
- pip (Python package manager)
- Django 4.0+ (for web deployment)

### Steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shanle1117/workshop2.git
   cd workshop2
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install django
   pip install requests    # For API calls if needed
   ```

4. **Run tests:**
   ```bash
   python test_chatbot.py
   python conversation_manager.py
   ```

5. **Start Django development server (when ready):**
   ```bash
   python manage.py runserver
   ```

---

## 📚 Module Documentation

### 1. Conversation Manager (`conversation_manager.py`)

The core module that handles conversation flow and user intent detection.

#### Main Function:
```python
def process_conversation(user_message: str, context: dict) -> tuple[str, dict]
```

**Parameters:**
- `user_message` (str): User input text
- `context` (dict): Conversation context dictionary

**Returns:**
- `tuple`: (chatbot_response, updated_context)

#### Key Functions:
- `detect_intent()` - Identifies user intent from keywords
- `handle_registration_query()` - Processes registration-related queries
- `handle_contact_query()` - Handles contact information requests
- `handle_greeting()` - Provides friendly greeting
- `handle_fallback()` - Returns clarification request for unclear input
- `update_context()` - Updates conversation context and history

#### Supported Intents:
| Intent | Keywords | Response Type |
|--------|----------|---------------|
| registration | register, course, subject, enroll | Course registration info |
| contact | contact, office, email, phone | Staff contact information |
| farewell | thanks, bye, goodbye | Polite goodbye |
| greeting | hi, hello, hey | Welcome message |
| unclear | (other) | Request for clarification |

### 2. Knowledge Base (`knowledge_base.py`)

Manages data retrieval from JSON and CSV files (existing module).

### 3. Test Suite (`test_chatbot.py`)

Unit tests for validating chatbot functionality (existing module).

---

## 💡 Usage Examples

### Basic Usage:

```python
from conversation_manager import process_conversation

# Initialize context
context = {}

# Process user message
user_message = "I want to register for courses"
response, context = process_conversation(user_message, context)

print(f"Bot: {response}")
```

### Conversation Flow:

```python
# Simulate a multi-turn conversation
context = {}
messages = [
    "Hi, I need help",
    "I want to register for courses",
    "When does registration open?",
    "How do I submit the form?",
    "Thanks for your help!"
]

for msg in messages:
    response, context = process_conversation(msg, context)
    print(f"User: {msg}")
    print(f"Bot: {response}\n")
```

### Django Integration:

```python
# In Django views.py
from django.http import JsonResponse
from conversation_manager import process_conversation

def chat(request):
    user_message = request.POST.get('message')
    context = request.session.get('chat_context', {})
    
    response, updated_context = process_conversation(user_message, context)
    request.session['chat_context'] = updated_context
    
    return JsonResponse({
        'response': response,
        'context': updated_context
    })
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│            Web Interface (main.html + style.css)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            Django Views (Integration Layer)             │
│  - Handle HTTP requests/responses                       │
│  - Manage session context                               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│        Conversation Manager (conversation_manager.py)   │
│  - Intent Detection                                     │
│  - Context Management                                   │
│  - Response Routing                                     │
└─────┬─────────────────────────────────────────────┬─────┘
      │                                             │
┌─────▼──────────────────────┐    ┌────────────────▼─────┐
│   Handler Functions        │    │ Knowledge Base Module  │
│ - Registration             │    │ (knowledge_base.py)    │
│ - Contact                  │    │                        │
│ - Greeting/Fallback        │    │ Data Sources:          │
└────────────────────────────┘    │ - course_info.json     │
                                  │ - schedule.json        │
                                  │ - faqs.json            │
                                  │ - staff_contacts.json  │
                                  │ - faix_data.csv        │
                                  └────────────────────────┘
```

---

## 🔌 Integration Guide

### With Django Views:

1. **In `settings.py`:**
```python
INSTALLED_APPS = [
    # ...
    'chatbot',  # Your app name
]
```

2. **In `urls.py`:**
```python
from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.chat_api, name='chat_api'),
]
```

3. **In `views.py`:**
```python
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from conversation_manager import process_conversation

@require_POST
def chat_api(request):
    user_message = request.POST.get('message', '')
    context = request.session.get('chat_context', {})
    
    response, updated_context = process_conversation(user_message, context)
    request.session['chat_context'] = updated_context
    
    return JsonResponse({'response': response})
```

### With NLP Module (Future Enhancement):

```python
# In conversation_manager.py, replace detect_intent() with:
from npl_module import classify_intent  # When NLP module is ready

def detect_intent(user_message: str) -> Optional[str]:
    # Use NLP classifier instead of keyword matching
    intent = classify_intent(user_message)
    return intent
```

---

## ✅ Testing

### Run All Tests:
```bash
python conversation_manager.py
```

### Run Specific Tests:
```bash
python test_chatbot.py
```

### Test Cases Included:

1. **Registration Topic Flow** - Tests conversation context for registration
2. **Contact Information Flow** - Tests contact-related queries
3. **Fallback Response** - Tests unclear input handling
4. **Context Continuity** - Tests topic memory across turns

### Expected Output:
```
======================================================================
FAIX AI Chatbot - Conversation Manager Test
======================================================================

📌 Test Case 1: Registration Topic Flow
----------------------------------------------------------------------
User: Hi
Bot: 👋 Hello! Welcome to FAIX AI Chatbot...

User: I want to register
Bot: 💡 I can help you with registration questions...

[Additional test cases...]
```

---

## 🔮 Future Enhancements

### Phase 2 (NLP Integration):
- [ ] Integrate transformer-based intent classification (e.g., BERT, RoBERTa)
- [ ] Add entity recognition for extracting course names, dates, etc.
- [ ] Implement semantic similarity for better query matching
- [ ] Multi-language support (Malay, English)

### Phase 3 (Advanced Features):
- [ ] User authentication and personalization
- [ ] Integration with university database systems
- [ ] Email notification capabilities
- [ ] Analytics dashboard for admin
- [ ] Sentiment analysis for feedback

### Phase 4 (Deployment):
- [ ] Docker containerization
- [ ] CI/CD pipeline setup
- [ ] Performance optimization
- [ ] Load balancing for high traffic
- [ ] Mobile app integration

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style:
- Follow PEP 8 guidelines
- Add docstrings to all functions
- Include type hints for function parameters
- Add inline comments for complex logic

---

## 📝 License

This project is developed for FAIX, UTeM. All rights reserved.

---

## 📞 Contact & Support

- **Project Owner**: Le (shanle1117)
- **Faculty**: Faculty of Artificial Intelligence and Cyber Security (FAIX), UTeM
- **Repository**: https://github.com/shanle1117/workshop2

For questions or issues, please open a GitHub issue or contact the project maintainers.

---

## 📚 Additional Resources

- [Python Type Hints Documentation](https://docs.python.org/3/library/typing.html)
- [Django Documentation](https://docs.djangoproject.com/)
- [Natural Language Processing Basics](https://www.nlp.org/)
- [Chatbot Design Best Practices](https://www.chatbotdesignpatterns.com/)

---

**Last Updated**: November 12, 2025  
**Project Status**: 🟢 Active Development
