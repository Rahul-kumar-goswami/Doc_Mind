from assistant.rag_engine import rag_engine
import os

print(f"GROQ_API_KEY set: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")
try:
    print("Testing RAG Engine with a simple question...")
    answer = rag_engine.get_answer("Hi")
    print(f"Assistant: {answer}")
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
