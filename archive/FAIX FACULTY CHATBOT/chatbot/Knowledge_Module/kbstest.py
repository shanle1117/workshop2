import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeBase:
    def __init__(self, csv_path):
        # Load your CSV (expects columns: question, answer, category, keywords)
        self.df = pd.read_csv(csv_path)

        # Fill blanks to avoid errors
        self.df = self.df.fillna("")

        # Precompute keyword sets for fast lookup
        self.df["keywords"] = self.df["keywords"].apply(lambda x: x.lower().split(","))

        # Prepare TF-IDF vectorizer for semantic search
        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(self.df["question"])

    # ---------------------------------------------------------
    # PREPROCESS USER INPUT
    # ---------------------------------------------------------
    def preprocess(self, text):
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text.strip()

    # ---------------------------------------------------------
    # SIMPLE KEYWORD EXTRACTION (RULE-BASED)
    # ---------------------------------------------------------
    def extract_keywords(self, text):
        tokens = text.split()
        return tokens

    # ---------------------------------------------------------
    # RETRIEVAL LOGIC (INTENT + KEYWORDS + SEMANTIC)
    # ---------------------------------------------------------
    def retrieve(self, intent, user_text):
        user_clean = self.preprocess(user_text)
        user_keywords = self.extract_keywords(user_clean)

        # 1. FILTER BY INTENT
        subset = self.df[self.df["category"] == intent]

        if subset.empty:
            return None  # triggers fallback

        scores = []

        for idx, row in subset.iterrows():
            entry_keywords = row["keywords"]

            # Count how many user keywords match dataset keywords
            keyword_score = sum(1 for kw in user_keywords if kw in entry_keywords)

            scores.append((idx, keyword_score))

        # Pick highest keyword match
        best_keyword_match = max(scores, key=lambda x: x[1])
        best_keyword_idx, kw_score = best_keyword_match

        # If keyword score is weak, use semantic fallback
        if kw_score == 0:
            query_vec = self.vectorizer.transform([user_clean])
            similarity = cosine_similarity(query_vec, self.question_vectors)[0]

            best_idx = similarity.argmax()
            best_answer = self.df.iloc[best_idx]["answer"]

            return best_answer

        # Use best keyword match answer
        return self.df.iloc[best_keyword_idx]["answer"]

    # ---------------------------------------------------------
    # MAIN ENTRY POINT (CALLED BY YOUR CHATBOT)
    # ---------------------------------------------------------
    def get_answer(self, intent, user_text):
        answer = self.retrieve(intent, user_text)

        if answer is None:
            return (
                "I couldn't find the exact information. "
                "Try asking about: course info, registration, or staff contacts."
            )

        return answer
