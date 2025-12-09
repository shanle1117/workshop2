from knowledge_base import KnowledgeBase

# Replace this with your actual CSV filename
kb = KnowledgeBase("faix_data.csv")

# Example: test question + intent
intent = "programs"   # example category
user_question = "What course does FAIX offer?"

answer = kb.get_answer(intent, user_question)

print("User:", user_question)
print("Bot :", answer)
