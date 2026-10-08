import os
import re
import sys 
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from dotenv import load_dotenv
from Models.schema import ETL_Agent_Schema , RouterSchema , DataAgentSchema
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage , ToolMessage
from langgraph.graph import StateGraph, START, END 
from langchain_core.tools import tool
from utils.etl_tools import ETLTools
from IPython.display import display , Image 

from agents.ETL_Analyst import etl_analyst
from agents.sql_analyst import sql_graph_workflow as sql_analyst

llm = pick_llm("medium")

router_llm= llm.with_structured_output(RouterSchema)


def Router_node(state:DataAgentSchema):    
    message=state.messages[-1].content
    router_response_dict= router_llm.invoke(message).model_dump()
    router_response = router_response_dict["answer"]
    return {"router_response": router_response}

def etl_node(state:DataAgentSchema):

    message = state.messages[-1].content

    response = etl_analyst.invoke(
             {"messages":[HumanMessage(content=f"""
            {message}
    """)]}
        ) 
    # messages uses an `add` reducer: return only the new message(s)
    return {"messages": [response["messages"][-1]]}

    

def sql_node(state:DataAgentSchema):
    
    message = state.messages[-1].content
    input_schema= {
        "messages" : [],
        "user_question" : message,
        "curated_ques" : "",
        "prompt_query_context" : "",
        "generated_sql_query" : "",
        "is_safe" : "No",
        "comments" : "",
        "sql_query_execution_result" : "",
        "final_answer" : ""
    } 

    response = sql_analyst.invoke(input_schema)

    return {"messages": [AIMessage(content=response["final_answer"])]}
    
        
data_agent_graph = StateGraph(DataAgentSchema)
data_agent_graph.add_node("Router_node", Router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "Router_node")
def router_conditional_edge(state:DataAgentSchema):
    if state.router_response == "ETL_Agent":
        return "etl_node"
    else:
        return "sql_node"

data_agent_graph.add_conditional_edges(
    "Router_node",
    router_conditional_edge,
    {"etl_node": "etl_node", "sql_node": "sql_node"},
)
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("sql_node", END)

data_agent_graph_workflow = data_agent_graph.compile()

if __name__ == "__main__":
    img= Image(data_agent_graph_workflow.get_graph().draw_mermaid_png())
    with open("data_agent_graph.png", "wb") as f:
        f.write(img.data)
    
    response = data_agent_graph_workflow.invoke(
        {"messages": [HumanMessage(content="List all films that have a rental rate greater than $4.00, ordered by their replacement cost")]}
    )
    print(response)