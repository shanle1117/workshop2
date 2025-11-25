import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeBase:
    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path).fillna("")

        self.df["keywords"] = self.df["keywords"].apply(
            lambda x: [kw.strip().lower() for kw in x.split(",")]
        )

        # Preprocess all questions before vectorizing
        clean_questions = self.df["question"].apply(self.preprocess)
        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)

    def preprocess(self, text):
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text.strip()

    def extract_keywords(self, text):
        return text.split()

    def retrieve(self, intent, user_text):
        if not intent or not isinstance(intent, str):
            return None

        intent = intent.lower()

        user_clean = self.preprocess(user_text)
        user_keywords = self.extract_keywords(user_clean)

        # Filter with case insensitivity
        subset = self.df[self.df["category"].str.lower() == intent]

        if subset.empty:
            return None

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

    def get_answer(self, intent, user_text):
        answer = self.retrieve(intent, user_text)
        if answer is None:
            return (
                "I couldn't find the exact information. "
                "Try asking about course info, registration, or staff contacts."
            )
        return answer
