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
        
        # Initialize Groq LLM
        self.llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama-3.1-8b-instant",
            temperature=0.2
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
        """
        Fixes 'spaced out' text where characters are separated by spaces.
        Example: 'C G P A  -  8 . 7 7' -> 'CGPA - 8.77'
        """
        import re
        
        # Heuristic: If there are many single characters followed by a space, it's likely spaced out
        # We look for patterns like 'A B C ' and join them
        # This regex matches a single character followed by a space, repeatedly
        # and joins them together.
        
        def de_space(match):
            return match.group(0).replace(" ", "")

        # Join single characters that are separated by a single space
        # Pattern: (Character followed by Space) repeated 2+ times, ending with a Character
        cleaned = re.sub(r'(\b\w )+\w\b', de_space, text)
        
        # Also handle specific cases like '8 . 7 7' -> '8.77'
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
        
        # Clean the text in each document
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

        # Find IDs of documents with the matching source metadata
        ids_to_delete = []
        docstore = self.vector_store.docstore
        
        if hasattr(docstore, '_dict'):
            for doc_id, doc in docstore._dict.items():
                if doc.metadata.get('source') == file_path:
                    ids_to_delete.append(doc_id)
        
        if ids_to_delete:
            self.vector_store.delete(ids_to_delete)
            self.vector_store.save_local(VECTOR_DB_DIR)
            print(f"Deleted {len(ids_to_delete)} chunks for {file_path}")
        else:
            print(f"No chunks found for {file_path}")

    def get_answer(self, question, user_memory_context="", chat_history_context=""):
        # Retrieve relevant context from vector store
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

        # DocuMind Enterprise Prompt
        prompt_template = """
You are DocuMind Enterprise, a warm, friendly, and highly helpful assistant. Your goal is to make the user feel comfortable and supported while providing accurate information from their documents.

Follow these rules strictly:

1. Greeting & Personality:
- Be cheerful and welcoming! Use a friendly tone that makes people enjoy talking to you.
- Use occasional friendly emojis (like 😊, ✨, 📄) to keep the conversation lively.
- If the user says "hi", "hello", or similar greetings:
  → Respond with a warm, personalized greeting.
  → Example: "Hello there! 😊 I'm DocuMind Enterprise, your friendly document assistant. How can I help you today?"

2. Context-Based Answers:
- Only answer using the provided context.
- If context is available, provide a clear, helpful, and naturally phrased answer.
- Always include the source information in a clean format:
  📄 Source: <document_name> | Page: <page_number>

3. Strict Guardrails:
- If the answer is NOT found in the context:
  → Say something like: "I'm sorry, I couldn't find that information in the documents I have. I can only help with what's in your uploaded files! Is there anything else I can look up for you? ✨"

4. Conversational Flow:
- Do not repeat greetings if you've already greeted the user in the chat history.
- Keep answers concise but friendly.
- If you're using the user's name, use it naturally.

---
Chat History:
{chat_history}

---
Context:
{context}

---
User Question:
{question}

---
Final Answer:
"""

        prompt = PromptTemplate(
            template=prompt_template, 
            input_variables=["chat_history", "context", "question"]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.invoke({
            "chat_history": chat_history_context,
            "context": context,
            "question": question
        })

        return response["text"]

# Singleton instance initialization
# We check RUN_MAIN to ensure it only loads once in the worker process, not the reloader parent.
if os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv:
    print("Initializing RAG Engine (Loading Embeddings Model)...")
    rag_engine = RAGEngine()
else:
    # In the reloader parent process, we provide a placeholder
    rag_engine = None
