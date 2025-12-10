---
name: Database NLP UI Enhancement
overview: Enhance the FAIX chatbot with Django + Firebase database integration, transformer-based NLP model for query processing, and a complete UI overhaul including modern chat interface, responsive design, and admin dashboard.
todos:
  - id: db_models
    content: Create Django models (FAQEntry, Conversation, Message, Course, Staff, Schedule) in django_app/models.py
    status: completed
  - id: db_migration
    content: Create database migrations and data import script to migrate CSV/JSON to database
    status: completed
    dependencies:
      - db_models
  - id: kb_database
    content: Update KnowledgeBase class to query database instead of CSV files
    status: completed
    dependencies:
      - db_migration
  - id: chat_ui_template
    content: Create chatbot widget HTML template with message display and input field
    status: completed
  - id: chat_api_endpoint
    content: Implement Django view for chat API endpoint that processes messages and returns responses
    status: completed
    dependencies:
      - kb_database
  - id: chat_javascript
    content: Create JavaScript for real-time chat interaction with AJAX calls to chat API
    status: completed
    dependencies:
      - chat_ui_template
      - chat_api_endpoint
  - id: chat_styling
    content: Add CSS styling for chatbot widget with modern design and responsive layout
    status: completed
    dependencies:
      - chat_ui_template
  - id: nlp_semantic_search
    content: Implement semantic search using sentence-transformers for better query matching
    status: completed
  - id: nlp_intent_classifier
    content: Enhance intent classification with ML model (DistilBERT or transformers pipeline)
    status: completed
  - id: nlp_integration
    content: Integrate NLP models into query_preprocessing.py and knowledge_base.py
    status: completed
    dependencies:
      - nlp_semantic_search
      - nlp_intent_classifier
---

# Database, NLP, and UI Enhancement Plan

## Overview

This plan covers three major enhancements:

1. **Database Integration**: Set up Django ORM models and Firebase Firestore for hybrid data storage
2. **NLP Model Integration**: Replace keyword-based intent detection with transformer-based models (BERT/RoBERTa)
3. **UI Overhaul**: Modern chat interface, responsive design, and admin dashboard

---

## 1. Database Setup (Django + Firebase)

### 1.1 Django Database Models

Create Django models in `django_app/models.py`:

- **Conversation**: Store conversation sessions (user_id, session_id, created_at, updated_at)
- **Message**: Store individual messages (conversation FK, role, content, timestamp, intent, confidence)
- **KnowledgeBaseEntry**: Migrate CSV/JSON data to database (category, question, answer, keywords)
- **UserSession**: Track user sessions and context

### 1.2 Django Database Configuration

- Update `django_app/settings.py` with PostgreSQL/MySQL configuration (or keep SQLite for development)
- Create migrations: `python manage.py makemigrations` and `python manage.py migrate`
- Create admin interface for managing knowledge base entries

### 1.3 Firebase Integration

- Install `firebase-admin` and `python-firebase` packages
- Create `src/firebase_service.py` for Firebase operations:
  - Real-time conversation updates
  - User analytics and metrics
  - Live knowledge base updates
- Add Firebase configuration file (`.env` for credentials)
- Integrate Firebase with Django views for real-time features

### 1.4 Data Migration

- Create `scripts/migrate_data_to_db.py` to migrate existing CSV/JSON files to Django models
- Set up data seeding script for initial knowledge base population

**Files to modify/create:**

- `django_app/models.py` (create)
- `django_app/settings.py` (update database config)
- `django_app/admin.py` (create admin interface)
- `src/firebase_service.py` (create)
- `scripts/migrate_data_to_db.py` (create)
- `requirements.txt` (add firebase-admin, python-firebase, psycopg2)

---

## 2. NLP Model Integration (Transformer-based)

### 2.1 Model Selection & Setup

- Use pre-trained transformer model: **DistilBERT** (lighter than BERT, faster inference)
- Alternative: **RoBERTa** for better accuracy
- Install: `transformers`, `torch`, `sentence-transformers`

### 2.2 Intent Classification Module

Create `src/nlp_intent_classifier.py`:

- Load pre-trained model (DistilBERT/RoBERTa fine-tuned on intent classification)
- Create intent classification pipeline
- Map model outputs to existing intent categories (registration, contact, course_info, etc.)
- Add confidence scoring

### 2.3 Entity Extraction

Enhance `src/query_preprocessing.py`:

- Integrate transformer-based NER (Named Entity Recognition)
- Extract: course codes, dates, staff names, email addresses
- Use spaCy or transformer-based NER model

### 2.4 Integration with Query Processor

- Update `src/query_preprocessing.py` to use transformer model instead of keyword matching
- Replace `detect_intent()` in `src/conversation_manager.py` to call NLP module
- Add fallback to keyword-based detection if NLP confidence is low

### 2.5 Model Training (Optional)

- Create `scripts/train_intent_model.py` for fine-tuning on FAIX-specific data
- Prepare training dataset from existing conversations
- Fine-tune DistilBERT on custom intents

**Files to modify/create:**

- `src/nlp_intent_classifier.py` (create)
- `src/query_preprocessing.py` (enhance with transformer integration)
- `src/conversation_manager.py` (update intent detection)
- `scripts/train_intent_model.py` (optional, for fine-tuning)
- `requirements.txt` (add transformers, torch, sentence-transformers, spacy)

---

## 3. UI Overhaul (Chat Interface + Responsive + Admin)

### 3.1 Modern Chat Interface

Update `frontend/main.html` and `frontend/style.css`:

- Chat bubble design (user messages on right, bot on left)
- Typing indicators when bot is processing
- Message timestamps
- Smooth scrolling and animations
- Message history persistence (load from database)
- Send button and input field improvements

### 3.2 Responsive Design

- Mobile-first CSS approach
- Media queries for tablets and phones
- Touch-friendly buttons and inputs
- Collapsible navigation for mobile
- Optimize chat interface for small screens

### 3.3 Frontend JavaScript

Create `frontend/chat.js`:

- AJAX calls to Django API endpoints
- Real-time message updates (using Firebase or WebSockets)
- Session management
- Error handling and retry logic
- Loading states and animations

### 3.4 Admin Dashboard

Create `frontend/admin.html` and `frontend/admin.css`:

- Dashboard overview (total conversations, active users, popular queries)
- Conversation viewer (browse and search conversations)
- Knowledge base management (CRUD operations)
- Analytics charts (query types, user satisfaction, response times)
- User management (if authentication added)

### 3.5 Django API Endpoints

Update `django_app/views.py`:

- `chat_api()`: Handle chat messages (POST)
- `get_conversation_history()`: Retrieve message history (GET)
- `admin_dashboard_data()`: Analytics data for dashboard (GET)
- `manage_knowledge_base()`: CRUD operations for KB entries (GET/POST/PUT/DELETE)

### 3.6 Django URL Routing

Update `django_app/urls.py`:

- `/api/chat/` - Chat API endpoint
- `/api/conversations/` - Conversation history
- `/api/admin/dashboard/` - Admin dashboard data
- `/api/admin/kb/` - Knowledge base management
- `/admin/` - Admin dashboard page

**Files to modify/create:**

- `frontend/main.html` (complete redesign)
- `frontend/style.css` (modern styling)
- `frontend/chat.js` (create)
- `frontend/admin.html` (create)
- `frontend/admin.css` (create)
- `django_app/views.py` (implement API endpoints)
- `django_app/urls.py` (add URL routes)
- `requirements.txt` (add django-cors-headers for API)

---

## Implementation Order

1. **Phase 1: Database Setup** (Foundation)

   - Django models and migrations
   - Data migration scripts
   - Basic admin interface

2. **Phase 2: NLP Integration** (Core functionality)

   - Transformer model setup
   - Intent classification integration
   - Entity extraction enhancement

3. **Phase 3: Firebase Integration** (Real-time features)

   - Firebase service setup
   - Real-time conversation updates

4. **Phase 4: UI Enhancement** (User experience)

   - Chat interface redesign
   - Responsive design
   - Admin dashboard

5. **Phase 5: Integration & Testing** (Polish)

   - Connect all components
   - End-to-end testing
   - Performance optimization

---

## Dependencies to Add

```txt
# Database
firebase-admin>=6.0.0
python-firebase>=1.2

# NLP
transformers>=4.30.0
torch>=2.0.0
sentence-transformers>=2.2.0
spacy>=3.5.0

# Django
django-cors-headers>=4.0.0
psycopg2-binary>=2.9.0  # For PostgreSQL (optional)

# Existing
django>=4.0
pandas
scikit-learn
```

---

## Key Integration Points

1. **Query Processing Flow:**
   ```
   User Input → NLP Intent Classifier → Query Preprocessor → 
   Knowledge Base (DB) → Conversation Manager → Response
   ```

2. **Data Storage:**

   - Structured data (conversations, messages) → Django DB
   - Real-time updates, analytics → Firebase
   - Knowledge base → Django DB (with Firebase sync for live updates)

3. **UI Flow:**

   - User sends message → JavaScript → Django API → NLP Processing → 

Response → Firebase update → UI update