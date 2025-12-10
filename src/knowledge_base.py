import os
import sys
import django
from pathlib import Path
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional, List, Dict

# Import semantic search
try:
    from .nlp_semantic_search import get_semantic_search
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    try:
        from nlp_semantic_search import get_semantic_search
        SEMANTIC_SEARCH_AVAILABLE = True
    except ImportError:
        SEMANTIC_SEARCH_AVAILABLE = False
        print("Warning: Semantic search not available. Using TF-IDF fallback.")

# Setup Django if not already configured
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
    django.setup()
    from django_app.models import FAQEntry
    DJANGO_AVAILABLE = True
except Exception as e:
    print(f"Warning: Django not available, falling back to CSV mode: {e}")
    DJANGO_AVAILABLE = False
    import pandas as pd


class KnowledgeBase:
    """
    Knowledge Base module that retrieves answers from database or CSV.
    Supports both database-backed and CSV-based modes.
    """
    
    def __init__(self, csv_path: Optional[str] = None, use_database: bool = True, use_semantic_search: bool = True):
        """
        Initialize KnowledgeBase.
        
        Args:
            csv_path: Path to CSV file (fallback if database unavailable)
            use_database: Whether to use database (default: True)
            use_semantic_search: Whether to use semantic search (default: True)
        """
        self.use_database = use_database and DJANGO_AVAILABLE
        self.csv_path = csv_path
        self.use_semantic_search = use_semantic_search and SEMANTIC_SEARCH_AVAILABLE
        self.semantic_search = None
        
        # Initialize semantic search if available
        if self.use_semantic_search:
            try:
                self.semantic_search = get_semantic_search()
                if self.semantic_search.is_available():
                    print("✓ Semantic search enabled")
                else:
                    self.use_semantic_search = False
            except Exception as e:
                print(f"Warning: Could not initialize semantic search: {e}")
                self.use_semantic_search = False
        
        if self.use_database:
            self._init_database()
        else:
            if csv_path:
                self._init_csv(csv_path)
            else:
                # Try default path
                default_path = Path(__file__).parent.parent / 'data' / 'faix_data.csv'
                if default_path.exists():
                    self._init_csv(str(default_path))
                else:
                    raise FileNotFoundError("No CSV file provided and default not found")
    
    def _init_database(self):
        """Initialize database-backed knowledge base"""
        print("Initializing Knowledge Base from database...")
        
        try:
            # Load all FAQ entries from database
            entries = FAQEntry.objects.filter(is_active=True)
            
            if not entries.exists():
                print("Warning: No FAQ entries found in database. Consider running migration script.")
                self.entries = []
                self.vectorizer = TfidfVectorizer()
                self.question_vectors = None
                return
        except Exception as e:
            # Handle case where table doesn't exist yet (migrations not run)
            if 'no such table' in str(e).lower() or 'does not exist' in str(e).lower():
                print(f"Warning: Database table not found. This is normal before running migrations. Error: {e}")
                print("Initializing with empty entries. Run migrations and migrate data to populate.")
            else:
                print(f"Warning: Database error during initialization: {e}")
            self.entries = []
            self.vectorizer = TfidfVectorizer()
            self.question_vectors = None
            return
        
        # Convert to list of dicts for processing
        self.entries = []
        questions = []
        
        for entry in entries:
            entry_dict = {
                'id': entry.id,
                'question': entry.question,
                'answer': entry.answer,
                'category': entry.category,
                'keywords': entry.get_keywords_list(),
            }
            self.entries.append(entry_dict)
            questions.append(entry.question)
        
        # Preprocess and vectorize questions
        clean_questions = [self.preprocess(q) for q in questions]
        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)
        
        print(f"✓ Loaded {len(self.entries)} FAQ entries from database")
    
    def _init_csv(self, csv_path: str):
        """Initialize CSV-backed knowledge base (fallback mode)"""
        print(f"Initializing Knowledge Base from CSV: {csv_path}")
        
        import pandas as pd
        self.df = pd.read_csv(csv_path).fillna("")
        
        self.df["keywords"] = self.df["keywords"].apply(
            lambda x: [kw.strip().lower() for kw in str(x).split(",") if kw.strip()]
        )
        
        # Preprocess all questions before vectorizing
        clean_questions = self.df["question"].apply(self.preprocess)
        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)
        
        print(f"✓ Loaded {len(self.df)} entries from CSV")
    
    def preprocess(self, text: str) -> str:
        """Clean and normalize text"""
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text.strip()
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        return text.split()
    
    def retrieve(self, intent: Optional[str], user_text: str) -> Optional[str]:
        """
        Retrieve answer based on intent and user text.
        
        Args:
            intent: Detected intent/category
            user_text: User's query text
            
        Returns:
            Answer string or None if not found
        """
        if not intent or not isinstance(intent, str):
            return None
        
        intent = intent.lower()
        user_clean = self.preprocess(user_text)
        user_keywords = self.extract_keywords(user_clean)
        
        if self.use_database:
            return self._retrieve_from_database(intent, user_text, user_keywords, user_clean)
        else:
            return self._retrieve_from_csv(intent, user_text, user_keywords, user_clean)
    
    def _retrieve_from_database(self, intent: str, user_text: str, 
                                user_keywords: List[str], user_clean: str) -> Optional[str]:
        """Retrieve answer from database"""
        # Filter entries by category/intent
        matching_entries = [
            entry for entry in self.entries
            if entry['category'].lower() == intent
        ]
        
        if not matching_entries:
            # Fallback: semantic search across all entries
            return self._semantic_search(user_text, user_clean)
        
        # Try semantic search first if available
        if self.use_semantic_search and self.semantic_search and self.semantic_search.is_available():
            try:
                # Use semantic search on matching entries
                results = self.semantic_search.find_similar_with_metadata(
                    user_text,
                    matching_entries,
                    text_field='question',
                    top_k=3,
                    threshold=0.3
                )
                
                if results:
                    best_entry, score = results[0]
                    # Update view count
                    try:
                        entry_obj = FAQEntry.objects.get(id=best_entry['id'])
                        entry_obj.view_count += 1
                        entry_obj.save(update_fields=['view_count'])
                    except FAQEntry.DoesNotExist:
                        pass
                    return best_entry['answer']
            except Exception as e:
                print(f"Warning: Semantic search failed, using keyword matching: {e}")
        
        # Fallback to keyword matching
        scores = []
        for entry in matching_entries:
            entry_keywords = entry['keywords']
            keyword_score = sum(1 for kw in user_keywords if kw in entry_keywords)
            scores.append((entry, keyword_score))
        
        if not scores:
            return self._semantic_search(user_text, user_clean)
        
        # Get best match
        best_entry, kw_score = max(scores, key=lambda x: x[1])
        
        # If no keyword match, use semantic search
        if kw_score == 0:
            return self._semantic_search(user_text, user_clean)
        
        # Update view count in database
        try:
            entry_obj = FAQEntry.objects.get(id=best_entry['id'])
            entry_obj.view_count += 1
            entry_obj.save(update_fields=['view_count'])
        except FAQEntry.DoesNotExist:
            pass
        
        return best_entry['answer']
    
    def _retrieve_from_csv(self, intent: str, user_text: str,
                           user_keywords: List[str], user_clean: str) -> Optional[str]:
        """Retrieve answer from CSV (fallback mode)"""
        # Filter with case insensitivity
        subset = self.df[self.df["category"].str.lower() == intent]
        
        if subset.empty:
            # Semantic fallback
            query_vec = self.vectorizer.transform([user_clean])
            similarity = cosine_similarity(query_vec, self.question_vectors)[0]
            best_idx = similarity.argmax()
            return self.df.iloc[best_idx]["answer"]
        
        scores = []
        for idx, row in subset.iterrows():
            entry_keywords = row["keywords"]
            keyword_score = sum(1 for kw in user_keywords if kw in entry_keywords)
            scores.append((idx, keyword_score))
        
        if not scores:
            return None
        
        best_keyword_idx, kw_score = max(scores, key=lambda x: x[1])
        
        # Semantic fallback if no keyword match
        if kw_score == 0:
            query_vec = self.vectorizer.transform([user_clean])
            similarity = cosine_similarity(query_vec, self.question_vectors)[0]
            best_idx = similarity.argmax()
            return self.df.iloc[best_idx]["answer"]
        
        return self.df.iloc[best_keyword_idx]["answer"]
    
    def _semantic_search(self, user_text: str, user_clean: str) -> Optional[str]:
        """Perform semantic search across all entries"""
        # Try transformer-based semantic search first
        if self.use_semantic_search and self.semantic_search and self.semantic_search.is_available():
            try:
                if self.use_database:
                    results = self.semantic_search.find_similar_with_metadata(
                        user_text,
                        self.entries,
                        text_field='question',
                        top_k=1,
                        threshold=0.3
                    )
                    if results:
                        entry, score = results[0]
                        # Update view count
                        try:
                            entry_obj = FAQEntry.objects.get(id=entry['id'])
                            entry_obj.view_count += 1
                            entry_obj.save(update_fields=['view_count'])
                        except FAQEntry.DoesNotExist:
                            pass
                        return entry['answer']
                else:
                    # For CSV mode, convert to list of dicts
                    questions = self.df['question'].tolist()
                    results = self.semantic_search.find_similar(
                        user_text,
                        questions,
                        top_k=1,
                        threshold=0.3
                    )
                    if results:
                        question, score = results[0]
                        matching_row = self.df[self.df['question'] == question]
                        if not matching_row.empty:
                            return matching_row.iloc[0]['answer']
            except Exception as e:
                print(f"Warning: Semantic search failed, using TF-IDF: {e}")
        
        # Fallback to TF-IDF cosine similarity
        if self.question_vectors is None or len(self.question_vectors) == 0:
            return None
        
        query_vec = self.vectorizer.transform([user_clean])
        similarity = cosine_similarity(query_vec, self.question_vectors)[0]
        best_idx = similarity.argmax()
        
        if self.use_database:
            if best_idx < len(self.entries):
                entry = self.entries[best_idx]
                # Update view count
                try:
                    entry_obj = FAQEntry.objects.get(id=entry['id'])
                    entry_obj.view_count += 1
                    entry_obj.save(update_fields=['view_count'])
                except FAQEntry.DoesNotExist:
                    pass
                return entry['answer']
        else:
            return self.df.iloc[best_idx]["answer"]
        
        return None
    
    def get_answer(self, intent: Optional[str], user_text: str) -> str:
        """
        Get answer for the query, with fallback message if not found.
        
        Args:
            intent: Detected intent/category
            user_text: User's query text
            
        Returns:
            Answer string
        """
        answer = self.retrieve(intent, user_text)
        if answer is None:
            return (
                "I couldn't find the exact information. "
                "Try asking about course info, registration, or staff contacts."
            )
        
        # Add handbook note for program_info queries
        user_text_lower = user_text.lower()
        if intent == 'program_info' or 'handbook' in user_text_lower:
            answer += "\n\n📚 The complete Academic Handbook PDF is available below with detailed program information."
        
        return answer
    
    def refresh(self):
        """Refresh knowledge base from database (useful after updates)"""
        if self.use_database:
            self._init_database()
        else:
            if self.csv_path:
                self._init_csv(self.csv_path)
