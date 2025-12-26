# FAIX AI Chatbot (Brief)

This project contains the FAIX AI Chatbot for student assistance. Key points:

- Core modules are under `modules/` (conversation manager & knowledge base).
- Data files should live under `data/`.
- Frontend assets are under `frontend/`.
- Tests live under `tests/`.

Run the demo conversation manager:

```bash
python modules/conversation_manager.py
```

Simple KB test:

```bash
python tests/test_chatbot.py
```

If you want this short README to replace the main `README.md`, tell me and I will update/replace it.

## Using Llama via Ollama (Conversational Agents)

This project can use an open-source Llama model (via Ollama) as a conversational
agent with Retrieval-Augmented Generation (RAG).

- Install and run Ollama with a Llama model, for example:

```bash
ollama pull llama3.2:3b
ollama serve
```

- Configure the backend with environment variables:
  - `LLM_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://localhost:11434`
  - `OLLAMA_MODEL=llama3.2:3b` (or another model tag you have installed)
  - `LLM_ENABLED=1` (optional, defaults to enabled)

The Django chat API (`/api/chat/`) now accepts:

- `agent_id`: one of `faq`, `schedule`, `staff`
- `history`: recent turns as a list of `{ "role": "user"|"assistant", "content": "..." }`

The frontend chat widget will default to the `faq` agent and will include the
conversation history and selected `agent_id` in each request. The backend uses
the knowledge base and JSON data under `data/` as RAG context when calling Llama.