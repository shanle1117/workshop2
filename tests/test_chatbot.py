from src.knowledge_base import KnowledgeBase

# Replace this with your actual CSV filename (path relative to project root)
kb = KnowledgeBase("data/faix_data.csv")

# Example: test question + intent
intent = "programs"   # example category
user_question = "What program does FAIX offer?"

answer = kb.get_answer(intent, user_question)

print("User:", user_question)
print("Bot :", answer)
