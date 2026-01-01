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
- **Advanced Intent Detection**: 
  - Rule-based keyword detection (fallback)
  - Transformer-based NLP intent classification (DistilBERT/RoBERTa)
  - Dynamic configuration via JSON files
- **Speech-to-Text**: Web Speech API integration for voice input
- **Semantic Search**: Sentence-transformers for improved query matching
- **RAG with Open LLMs**: Optional integration with open-source Llama models via Ollama, using Retrieval-Augmented Generation (RAG) over the existing knowledge base
- **Conversational Agents**: Specialized agents (FAQ, Schedule, Staff) with agent-specific prompts and context retrieval
- **Enhanced Response Formatting**: Automatic URL linking, line break preservation, and structured responses
- **Comprehensive FAIX Data**: Rich JSON data source covering programs, admission, facilities, departments, vision/mission, and more
- **Fee Query Handling**: Special handling for fee-related queries with direct link responses to official fee schedules
- **Multi-Topic Support**: 
  - 📚 Course Registration
  - 📞 Staff Contacts
  - 📅 Schedules & Deadlines
  - 👋 Polite Farewells
- **Fallback Handling**: Gracefully handles unclear or ambiguous inputs
- **Context Continuity**: Remembers previous topics and questions
- **Database Integration**: Django models for sessions, conversations, and message history
- **Django Integration**: Production-ready Django web framework integration
- **Extensible Architecture**: Easy to integrate additional NLP modules and knowledge base systems

---

## 📂 Project Structure

```
workshop2/
├── README.md                          # 📖 Project documentation
├── requirements.txt                   # 📦 Dependencies
├── .gitignore                        # 🚫 Git ignore rules
│
├── src/                              # 💻 Source code
│   ├── __init__.py
│   ├── chatbot_cli.py                # 💬 CLI interface
│   ├── conversation_manager.py       # 💬 Conversation Management Module
│   ├── knowledge_base.py             # 🧠 Knowledge Base Module
│   ├── nlp_intent_classifier.py      # 🤖 Transformer-based Intent Classification
│   ├── nlp_semantic_search.py        # 🔍 Semantic Search using Sentence Transformers
│   ├── agents.py                     # 🤖 Conversational Agents (FAQ, Schedule, Staff)
│   ├── prompt_builder.py             # 📝 RAG Prompt Construction
│   ├── query_preprocessing.py        # 🔤 NLP preprocessing
│   ├── query_preprocessing_v2.py     # 🔤 Enhanced NLP preprocessing
│   ├── firebase_service.py           # 🔥 Firebase integration
│   └── kbstest.py                    # 🧪 Knowledge base test
│
├── data/                             # 📊 Data files
│   ├── course_info.json              # 📚 Course Information Data
│   ├── schedule.json                 # 📅 Schedule Data
│   ├── faqs.json                     # ❓ FAQ Data
│   ├── staff_contacts.json           # 📇 Staff Contact Data
│   ├── faix_data.csv                 # 📊 FAIX General Data (CSV format)
│   ├── faix_json_data.json           # 📊 FAIX Comprehensive Data (JSON: programs, admission, facilities, etc.)
│   └── intent_config.json            # ⚙️ Intent classification configuration
│
├── frontend/                         # 🌐 Frontend files
│   ├── main.html                     # 🌐 Frontend UI
│   ├── chat.js                       # 💬 Chat functionality & Speech-to-Text
│   ├── style.css                     # 🎨 Styling
│   ├── admin.html                    # 👤 Admin interface
│   ├── admin.js                      # 👤 Admin functionality
│   └── admin.css                     # 🎨 Admin styling
│
├── tests/                            # ✅ Test files
│   ├── __init__.py
│   ├── test_chatbot.py               # ✅ Core chatbot tests
│   ├── test_speech_to_text.py        # 🎤 Speech-to-Text tests
│   ├── test_dynamic_features.py      # 🔄 Dynamic features tests
│   ├── test_static_vs_dynamic.py     # ⚖️ Static vs Dynamic comparison
│   ├── demo_static_vs_dynamic.py     # 📊 Demo script
│   └── SPEECH_TO_TEXT_TESTING_GUIDE.md  # 📖 Testing guide
│
├── django_app/                       # 🐍 Django app
│   ├── __init__.py
│   ├── views.py                      # Django views & API endpoints
│   ├── urls.py                       # URL routing
│   ├── settings.py                   # Configuration
│   ├── models.py                     # Database models (Session, Conversation, Message)
│   ├── admin.py                      # Django admin configuration
│   └── migrations/                   # Database migrations
│
├── docs/                             # 📚 Documentation
│   └── README_BRIEF.md
│
└── archive/                          # 📦 Old structure (archived)
    └── FAIX FACULTY CHATBOT/
```

### File Descriptions:

| File | Purpose |
|------|---------|
| `src/conversation_manager.py` | Manages conversation flow, context, and intent detection |
| `src/nlp_intent_classifier.py` | Transformer-based intent classification using DistilBERT/RoBERTa |
| `src/nlp_semantic_search.py` | Semantic search using sentence-transformers for better query matching |
| `src/agents.py` | Conversational agent definitions (FAQ, Schedule, Staff) with RAG support |
| `src/prompt_builder.py` | Constructs RAG prompts with context from knowledge base and FAIX data |
| `src/knowledge_base.py` | Stores and retrieves information from JSON/CSV data files and database |
| `src/query_preprocessing.py` | NLP preprocessing utilities |
| `frontend/main.html` | Web interface for the chatbot |
| `frontend/chat.js` | Chat functionality with Speech-to-Text support and enhanced formatting |
| `frontend/style.css` | CSS styling for the web interface with line break preservation |
| `django_app/views.py` | Django API endpoints for chat, sessions, and conversations |
| `django_app/models.py` | Database models for sessions, conversations, and messages |
| `tests/test_chatbot.py` | Core unit tests for chatbot functionality |
| `tests/test_speech_to_text.py` | Tests for Speech-to-Text feature |
| `tests/test_dynamic_features.py` | Tests for dynamic NLP features |
| `data/course_info.json` | Course details and information |
| `data/schedule.json` | Academic schedules and deadlines |
| `data/faqs.json` | Frequently asked questions and answers |
| `data/staff_contacts.json` | Staff directory and contact information |
| `data/faix_data.csv` | General FAIX faculty information (CSV format) |
| `data/faix_json_data.json` | Comprehensive FAIX data: programs, admission, facilities, departments, vision/mission |
| `data/intent_config.json` | Configuration for intent classification (includes 'fees' intent) |

---

## 🚀 Installation & Setup

### Prerequisites:
- Python 3.10 or higher
- pip (Python package manager)
- Django 4.0+ (for web deployment)
- Chrome or Edge browser (for Speech-to-Text feature)
- PostgreSQL (optional, for production database)
- Firebase account (optional, for cloud storage)

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
   pip install -r requirements.txt
   ```
   
   **Note**: For NLP features, you may need to download spaCy models:
   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Set up environment variables (optional):**
   Create a `.env` file in the root directory for Firebase credentials:
   ```
   FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Run tests:**
   ```bash
   python tests/test_chatbot.py
   python tests/test_speech_to_text.py
   python tests/test_dynamic_features.py
   python src/conversation_manager.py
   ```

7. **Start Django development server:**
   ```bash
   python manage.py runserver
   ```
   
   The chatbot will be available at `http://localhost:8000`

---

## 📚 Module Documentation

### 1. Conversation Manager (`src/conversation_manager.py`)

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

### 2. NLP Intent Classifier (`src/nlp_intent_classifier.py`)

Transformer-based intent classification using pre-trained models (DistilBERT/RoBERTa).

#### Main Class:
```python
class IntentClassifier:
    def __init__(self, model_name: str = None, use_zero_shot: bool = None, config_path: str = None)
    def classify(self, text: str) -> Tuple[str, float]
```

**Features:**
- Zero-shot classification support
- Fine-tuned model support
- Dynamic configuration loading from JSON
- Keyword pattern matching fallback
- Confidence scoring

### 3. Semantic Search (`src/nlp_semantic_search.py`)

Semantic search using sentence-transformers for improved query matching.

#### Main Class:
```python
class SemanticSearch:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2')
    def search(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[str, float]]
```

**Features:**
- Dense vector embeddings
- Similarity-based document retrieval
- Caching for performance
- Configurable model selection

### 4. Conversational Agents (`src/agents.py`)

Specialized conversational agents using RAG (Retrieval-Augmented Generation) with open LLMs.

#### Available Agents:
- **FAQ Agent**: Answers general questions using FAQ knowledge base and comprehensive FAIX data
- **Schedule Agent**: Handles academic calendar, class times, and deadlines
- **Staff Agent**: Provides staff and faculty contact information

#### Main Functions:
- `AgentRegistry` - Manages available agents
- `retrieve_for_agent()` - Retrieves relevant context for each agent
- `check_faix_data_available()` - Checks if comprehensive FAIX data is available

**Features:**
- Agent-specific system prompts
- Context-aware retrieval from knowledge base
- Integration with FAIX comprehensive data (programs, admission, facilities)
- Special handling for fee queries with direct link responses
- Enhanced response formatting with line breaks and URL preservation

### 5. Prompt Builder (`src/prompt_builder.py`)

Constructs RAG prompts with context from multiple sources.

#### Main Function:
```python
def build_messages(agent: Agent, user_message: str, context: dict, intent: Optional[str] = None) -> List[Dict]
```

**Features:**
- Formats context from FAQ, schedule, staff contacts, and FAIX data
- Agent-specific prompt customization
- Intent-aware prompt construction
- URL and link preservation in responses
- Enhanced formatting instructions for structured responses

### 6. Knowledge Base (`src/knowledge_base.py`)

Manages data retrieval from JSON/CSV files and database.

**Features:**
- JSON/CSV file support
- Database integration
- Multi-source data retrieval
- Query preprocessing
- Support for comprehensive FAIX JSON data

### 7. Test Suite

Multiple test modules for comprehensive validation:
- `tests/test_chatbot.py` - Core chatbot functionality
- `tests/test_speech_to_text.py` - Speech-to-Text feature tests
- `tests/test_dynamic_features.py` - Dynamic NLP features
- `tests/test_static_vs_dynamic.py` - Performance comparison

---

## 💡 Usage Examples

### Basic Usage:

```python
from src.conversation_manager import process_conversation

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
from src.conversation_manager import process_conversation

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
┌─────────────────────────────────────────────────────────────┐
│  Web Interface (frontend/main.html + chat.js)              │
│  - Speech-to-Text (Web Speech API)                         │
│  - Real-time chat UI                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Django Views (django_app/views.py)                        │
│  - HTTP request/response handling                          │
│  - Session & conversation management                       │
│  - Database operations (UserSession, Conversation, Message)│
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Conversation Manager (src/conversation_manager.py)        │
│  - Context Management                                      │
│  - Response Routing                                        │
└─────┬───────────────────────────────────────────────┬──────┘
      │                                               │
┌─────▼──────────────────────┐    ┌───────────────────▼────────┐
│  Intent Detection Layer    │    │  Knowledge Base Module     │
│  ┌──────────────────────┐  │    │  (src/knowledge_base.py)  │
│  │ NLP Intent Classifier│  │    │  - JSON/CSV files         │
│  │ (Transformer-based)  │  │    │  - Database queries       │
│  └──────────────────────┘  │    │  - Firebase (optional)    │
│  ┌──────────────────────┐  │    └──────────────────────────┘
│  │ Keyword Fallback     │  │
│  └──────────────────────┘  │
└─────┬──────────────────────┘
      │
┌─────▼──────────────────────┐    ┌───────────────────────────┐
│  Handler Functions        │    │  Semantic Search          │
│  - Registration            │    │  (src/nlp_semantic_search.py)│
│  - Contact                 │    │  - Sentence transformers │
│  - Greeting/Fallback       │    │  - Vector embeddings     │
└────────────────────────────┘    └───────────────────────────┘
```

---

## 🔌 Integration Guide

### Using Llama via Ollama (Conversational Agents)

This project uses open-source Llama models (via Ollama) as conversational
agents with Retrieval-Augmented Generation (RAG) on top of the existing
knowledge base and comprehensive FAIX JSON data.

#### Setup:

1. **Install and run Ollama with a Llama model:**
   ```bash
   ollama pull llama3.2:3b
   ollama serve
   ```

2. **Configure the backend with environment variables:**
   - `LLM_PROVIDER=ollama`
   - `OLLAMA_BASE_URL=http://localhost:11434`
   - `OLLAMA_MODEL=llama3.2:3b` (or another model tag you have installed)
   - `LLM_ENABLED=1` (optional, defaults to enabled)

#### Available Agents:

- **`faq`** (FAQ Assistant): Answers general questions using FAQ knowledge base and comprehensive FAIX data (programs, admission, facilities, departments, fees, etc.)
- **`schedule`** (Schedule Assistant): Handles academic calendar, class times, and important deadlines
- **`staff`** (Staff Contact Assistant): Provides staff and faculty contact information

#### API Usage:

The Django chat API (`/api/chat/`) accepts:

- `agent_id`: one of `faq`, `schedule`, `staff` (selects a specialized conversational agent)
- `history`: recent conversation turns as a list of `{ "role": "user"|"assistant", "content": "..." }`

The frontend chat widget defaults to the `faq` agent and includes the selected
`agent_id` and recent `history` in each request. When `agent_id` is provided,
the backend routes the request through the Llama-based conversational agent with
RAG context; when it is omitted, it falls back to the previous rules/KB-based behaviour.

#### Features:

- **Automatic Intent Routing**: NLP-based intent detection routes queries to appropriate agents
- **Context Retrieval**: Each agent retrieves relevant context from knowledge base and FAIX data
- **Enhanced Formatting**: Responses include proper line breaks, bullet points, and preserved URLs
- **Fee Query Handling**: Fee-related queries automatically return direct links to official fee schedules
- **Comprehensive Data**: FAQ agent has access to rich FAIX data including programs, admission requirements, facilities, and more

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
from src.conversation_manager import process_conversation

@require_POST
def chat_api(request):
    user_message = request.POST.get('message', '')
    context = request.session.get('chat_context', {})
    
    response, updated_context = process_conversation(user_message, context)
    request.session['chat_context'] = updated_context
    
    return JsonResponse({'response': response})
```

### With NLP Intent Classifier:

```python
# In conversation_manager.py or views.py:
from src.nlp_intent_classifier import IntentClassifier

# Initialize classifier
classifier = IntentClassifier(
    model_name='distilbert-base-uncased',
    use_zero_shot=True,
    config_path='data/intent_config.json'
)

# Classify intent
intent, confidence = classifier.classify(user_message)
```

### With Semantic Search:

```python
# For improved query matching:
from src.nlp_semantic_search import SemanticSearch

search = SemanticSearch(model_name='all-MiniLM-L6-v2')
results = search.search(
    query="course registration",
    documents=knowledge_base.get_all_documents(),
    top_k=5
)
```

---

## ✅ Testing

### Latest Test Results (January 2026)

| Metric | Value |
|--------|-------|
| **Total Tests** | 85 |
| **Successful** | 81 |
| **Failed** | 4 |
| **Success Rate** | 95.29% |
| **Avg Response Time** | 12.39s |
| **Min Response Time** | 2.05s |
| **Max Response Time** | 32.06s |

#### Results by Category:

| Category | Success Rate | Notes |
|----------|--------------|-------|
| Greeting | 5/5 (100%) | ✅ |
| Program Info | 5/5 (100%) | ✅ |
| Admission | 5/5 (100%) | ✅ |
| Fees | 5/5 (100%) | ✅ |
| Career | 5/5 (100%) | ✅ |
| About FAIX | 5/5 (100%) | ✅ |
| Course Info | 5/5 (100%) | ✅ |
| Registration | 5/5 (100%) | ✅ |
| Academic Schedule | 5/5 (100%) | ✅ |
| Farewell | 5/5 (100%) | ✅ |
| Multi-language | 5/5 (100%) | ✅ |
| Edge Cases | 5/5 (100%) | ✅ |
| Academic Resources | 5/5 (100%) | ✅ |
| Staff Contact | 3/5 (60%) | ⚠️ Timeouts |
| Facility Info | 4/5 (80%) | ⚠️ Timeout |
| Research | 4/5 (80%) | ⚠️ Timeout |

> **Note**: Failed tests are due to API request timeouts (30s limit), not incorrect responses.

### Run All Tests:
```bash
# Core functionality
python src/conversation_manager.py

# Speech-to-Text tests
python tests/test_speech_to_text.py

# Dynamic features
python tests/test_dynamic_features.py

# Static vs Dynamic comparison
python tests/test_static_vs_dynamic.py
```

### Run Specific Test Suites:
```bash
# Core chatbot tests
python tests/test_chatbot.py

# Speech-to-Text feature
python tests/test_speech_to_text.py

# NLP features
python tests/test_dynamic_features.py
```

### Run CLI Interface:
```bash
python -X utf8 src/chatbot_cli.py
```

### Manual Testing:

For Speech-to-Text, refer to the comprehensive guide:
```bash
# See tests/SPEECH_TO_TEXT_TESTING_GUIDE.md
```

### Test Cases Included:

1. **Registration Topic Flow** - Tests conversation context for registration
2. **Contact Information Flow** - Tests contact-related queries
3. **Fallback Response** - Tests unclear input handling
4. **Context Continuity** - Tests topic memory across turns
5. **Speech-to-Text** - Tests voice input functionality
6. **NLP Intent Classification** - Tests transformer-based intent detection
7. **Semantic Search** - Tests query matching with embeddings
8. **Static vs Dynamic** - Performance and accuracy comparison

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

### Phase 2 (NLP Enhancements):
- [x] ✅ Integrate transformer-based intent classification (DistilBERT/RoBERTa)
- [x] ✅ Implement semantic similarity for better query matching
- [ ] Add entity recognition for extracting course names, dates, etc.
- [ ] Multi-language support (Malay, English)
- [ ] Fine-tune models on domain-specific data

### Phase 3 (Advanced Features):
- [x] ✅ Speech-to-Text integration
- [x] ✅ Database integration for conversation history
- [ ] User authentication and personalization
- [ ] Integration with university database systems
- [ ] Email notification capabilities
- [ ] Analytics dashboard for admin
- [ ] Sentiment analysis for feedback
- [ ] Multi-modal support (images, documents)

### Phase 4 (Deployment):
- [ ] Docker containerization
- [ ] CI/CD pipeline setup
- [ ] Performance optimization
- [ ] Load balancing for high traffic
- [ ] Mobile app integration
- [ ] API rate limiting and security enhancements

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

- **Project Owner**:
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

**Last Updated**: January 2026  
**Project Status**: 🟢 Active Development

---

## 🎤 Speech-to-Text Feature

The chatbot includes a Speech-to-Text feature using the Web Speech API for voice input.

### Browser Support:
- ✅ Chrome/Edge (full support)
- ✅ Safari (limited support)
- ❌ Firefox (not supported)

### Usage:
1. Click the microphone button in the chat interface
2. Grant microphone permission when prompted
3. Speak your question clearly
4. The transcribed text will appear in the input field
5. The message is automatically sent when you stop speaking

### Testing:
See `tests/SPEECH_TO_TEXT_TESTING_GUIDE.md` for comprehensive testing instructions.

---

## 🤖 NLP Features

### Intent Classification
The system supports both static (keyword-based) and dynamic (transformer-based) intent classification:

- **Static Mode**: Fast keyword matching for basic intents
- **Dynamic Mode**: Transformer-based classification using DistilBERT/RoBERTa
- **Hybrid Mode**: Combines both approaches for optimal performance

### Semantic Search
Enhanced query matching using sentence-transformers:
- Dense vector embeddings for semantic similarity
- Improved retrieval of relevant information
- Configurable model selection (all-MiniLM-L6-v2, all-mpnet-base-v2)

### Configuration
Intent classification can be configured via `data/intent_config.json`:
- Custom intent categories (including `fees` intent)
- Keyword patterns
- Model selection
- Confidence thresholds

### Conversational Agents with RAG
The system uses specialized conversational agents that combine:
- **Retrieval**: Context from knowledge base, FAIX comprehensive data, and specialized data sources
- **Augmentation**: Agent-specific system prompts and formatting instructions
- **Generation**: Open LLM models (via Ollama) for natural language responses

### Response Formatting
Enhanced response formatting includes:
- Automatic URL detection and linking
- Line break preservation (`\n` converted to `<br>`)
- Structured bullet points and sections
- HTML escaping for security
- Special handling for fee queries (direct link responses)
