from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
load_dotenv()

def pick_llm(Level : str):
    """
    Picking the LLM to use based on the user choice    
    """
    if Level.lower()=="low":
        llm= ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")
    elif Level.lower()=="medium":
        llm= ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")
    elif Level.lower()=="high":
        llm= ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite")
    else:
        raise ValueError("Invalid Level. Please choose from 'low', 'medium', or 'high'.")    

    return llm 

