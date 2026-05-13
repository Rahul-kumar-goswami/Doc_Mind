import os
import sys
import logging

# Suppress Hugging Face and Transformers verbose logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import LLMChain
from dotenv import load_dotenv

load_dotenv()

# Configuration
VECTOR_DB_DIR = "faiss_index"
MODEL_CACHE_DIR = "model_cache"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Create cache directory if it doesn't exist
if not os.path.exists(MODEL_CACHE_DIR):
    os.makedirs(MODEL_CACHE_DIR)

class RAGEngine:
    def __init__(self):
        # Use cache_folder to store model locally
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_folder=MODEL_CACHE_DIR
        )
        self.vector_store = None
        self.load_vector_store()
        
        # Initialize Groq LLM - Zero temperature for maximum professionalism
        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama-3.1-8b-instant",
            temperature=0.0
        )

    def load_vector_store(self):
        if os.path.exists(VECTOR_DB_DIR):
            self.vector_store = FAISS.load_local(
                VECTOR_DB_DIR, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        else:
            self.vector_store = None

    def clean_text(self, text):
        import re
        def de_space(match):
            return match.group(0).replace(" ", "")
        cleaned = re.sub(r'(\b\w )+\w\b', de_space, text)
        cleaned = re.sub(r'(\d )+\. (\d )+\d', lambda m: m.group(0).replace(" ", ""), cleaned)
        cleaned = re.sub(r'(\d )+\d', lambda m: m.group(0).replace(" ", ""), cleaned)
        return cleaned

    def ingest_document(self, file_path):
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError("Unsupported file format.")
        documents = loader.load()
        for doc in documents:
            doc.page_content = self.clean_text(doc.page_content)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents(documents)
        if self.vector_store:
            self.vector_store.add_documents(chunks)
        else:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(VECTOR_DB_DIR)

    def delete_document(self, file_path):
        if not self.vector_store:
            return
        ids_to_delete = []
        docstore = self.vector_store.docstore
        if hasattr(docstore, '_dict'):
            for doc_id, doc in docstore._dict.items():
                if doc.metadata.get('source') == file_path:
                    ids_to_delete.append(doc_id)
        if ids_to_delete:
            self.vector_store.delete(ids_to_delete)
            self.vector_store.save_local(VECTOR_DB_DIR)
        else:
            print(f"No chunks found for {file_path}")

    def get_answer(self, question, user_memory_context="", chat_history_context=""):
        context = ""
        if self.vector_store:
            docs = self.vector_store.similarity_search(question, k=3)
            context_list = []
            for doc in docs:
                source = os.path.basename(doc.metadata.get('source', 'Unknown'))
                page = doc.metadata.get('page', 'N/A')
                if isinstance(page, int):
                    page += 1
                context_list.append(f"--- Document: {source} | Page: {page} ---\n{doc.page_content}")
            context = "\n\n".join(context_list)

        # CelestAI Core Behavior Rules - Version 10.0
        prompt_template = """
You are CelestAI, a smart, helpful, and professional AI Assistant.
Your primary goal is to provide accurate answers based on the provided document context.

========================================
CONVERSATIONAL GUIDELINES
========================================

1. NATURAL GREETINGS & ENDINGS
- Start with a warm greeting if the user starts the conversation (e.g., "Hi {name}!", "Hello!").
- End your responses politely (e.g., "Hope this helps!", "Done.", "Have a good day!", "Let me know if you need anything else.").
- If the user says something like "Good", "Thanks", or "Bye", respond naturally (e.g., "You're welcome!", "Glad I could help!", "Goodbye!").

2. ACCURATE & CONTEXTUAL ANSWERS
- Use the DOCUMENT CONTEXT to answer questions accurately.
- If the information is not in the context, politely state that you don't have that information in the current documents.
- For education details (marks, grades, etc.), use Markdown Tables.

3. SMART INTENT DETECTION
- Handle typos and casual language gracefully.
- Do NOT repeat the same information if the user is just acknowledging your previous answer.

4. SUBTLE CITATIONS
- Only include a source citation if you used the document context to answer.
- Format: 📄 Source: <filename> | Page: <page>

========================================
USER INFO: {name}
========================================

========================================
DOCUMENT CONTEXT
========================================
{context}

========================================
CHAT HISTORY
========================================
{chat_history}

========================================
USER QUESTION: {question}
========================================

FINAL ANSWER:
"""
        prompt = PromptTemplate(
            template=prompt_template, 
            input_variables=["name", "chat_history", "context", "question"]
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.invoke({
            "name": user_memory_context, # Assuming user_memory_context contains the name
            "chat_history": chat_history_context,
            "context": context,
            "question": question
        })
        return response["text"]

if os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv:
    rag_engine = RAGEngine()
else:
    rag_engine = None
