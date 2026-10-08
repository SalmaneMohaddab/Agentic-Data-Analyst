import os
import re
import sys 
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from dotenv import load_dotenv
from Models.schema import ETL_Agent_Schema
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage , ToolMessage
from langgraph.graph import StateGraph, START, END 
from langchain_core.tools import tool
from utils.etl_tools import ETLTools
from IPython.display import display , Image 

@tool
def extract_load(url:str, dest_folder:str, format:str):
    """
    Extracts data from an api (url) source and loads it into the desired Location (destination) .
    Args:
        url(str): The url of the api
        dest_folder(str): The path to the destination folder 
        format(str): The format of the data to be loaded (json, csv, or parquet)
    Return:
        message(str): A message indicating the status of the extraction and loading process.
    """
    etl_tools = ETLTools()
    return etl_tools.extract_load(url, dest_folder, format)

@tool
def transforme_load_context(file_path:str, dest_folder:str, format:str, user_question:str):
    """
    Transformes data from a file and loads it into the desired format.
    Args:
        file_path(str): The path to the file to be transformed
        dest_folder(str): The path to the destination folder 
        format(str): The format of the data to be loaded (json, csv, or parquet)
        user_question(str): The question asked by the user
    Return:
        message(str): A message indicating the status of the transformation and loading process.
    """
    etl_tools = ETLTools()
    top_5_rows = etl_tools.transforme_load_context(file_path, dest_folder, format)
    llm= pick_llm("high")
    prompt = f"""
            You are a Python Data Analyst who uses Pandas to analyze data. 
            You need to provide only the Pandas Code that will help to perform the right ETL operations on the data stored in the file : {file_path}
            as per the user's question. Do not provide any explanation or comments, only
            the code should be provided. The code should be in a format that can be executed 
            in a Python environment with Pandas installed. 
            Don't write anything else than Pandas Code. \n
            
            Create the Pandas Dataframe from the data stored in the file : {file_path} and then 
            write the code to transform and save the data at {dest_folder}.
            Here's the user's question: {user_question}\n
            Here's the context of the data you will be analyzing: {top_5_rows}\n

        """

    content = llm.invoke(prompt).content
    # Gemini (newer langchain-google-genai) may return a list of content blocks instead of a str
    if isinstance(content, list):
        llm_response = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    else:
        llm_response = content
    # Extract code from a ```python ... ``` fence if present
    match = re.search(r"```(?:python)?\s*\n(.*?)```", llm_response, re.DOTALL)
    pandas_code = (match.group(1) if match else llm_response).strip()  
    result = etl_tools.execute_code(pandas_code)
    return f"The pandas code is: {pandas_code}\n The result of the execution is: {result}"
    
tools=[
    extract_load,
    transforme_load_context
]   

llm = pick_llm("high")
llm_binding= llm.bind_tools(tools)

def llm_node(state:ETL_Agent_Schema):
    messages = state.messages
    prompt = f"""
            You are a Python Data Analyst who has access to tools that can extract and load, 
            transform and load data. You will be provided with a user's question 
            and you would need to perform the right ETL operations as per the user's question. 
            If the operation is performed then inform the user and end the coversation.
            Here's the chat history: {messages}\n
    """

    final_answer = llm_binding.invoke(prompt)

    state.messages = messages + [final_answer]

    return state


def tool_node(state:ETL_Agent_Schema):
    """
    This node is used to execute the tools.
    """
    tool_results = []
    tool_calls = state.messages[-1].tool_calls
    tools_by_name = {tool.name: tool for tool in tools}
    for tool_call in tool_calls:
        tool = tools_by_name.get(tool_call['name'])
        observation = tool.invoke(tool_call['args'])
        tool_results.append(ToolMessage(content=observation,tool_call_id=tool_call['id']))
    state.messages += tool_results


# -------------------- 
        
etl_analyst_graph= StateGraph(ETL_Agent_Schema)
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node)

etl_analyst_graph.add_edge(START, "llm_node")

def is_tool_call(state:ETL_Agent_Schema):
    tool_calls = state.messages[-1].tool_calls

    if tool_calls:
        return "tool_node"
    else:
        return "end"

etl_analyst_graph.add_conditional_edges(
    "llm_node",is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END
    }
)

etl_analyst_graph.add_edge("tool_node", "llm_node")

etl_analyst = etl_analyst_graph.compile()
etl_analyst_graph_workflow = etl_analyst_graph.compile()

if __name__ == "__main__":
    img= Image(etl_analyst_graph_workflow.get_graph().draw_mermaid_png())
    with open("etl_analyst_graph.png", "wb") as f:
        f.write(img.data)
    #response = etl_analyst.invoke(
    #    {"messages":[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv format")]}
    #)
    #print(response["messages"][-1].content)
