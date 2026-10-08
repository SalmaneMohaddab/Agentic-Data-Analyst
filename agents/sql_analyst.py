
import os
import sys 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from dotenv import load_dotenv
from Models.schema import AgentSchema, JudgeSchema
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from IPython.display import display , Image 




load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "agent_db")  

def _get_text(response) -> str:
    """Extract text from a ChatModel response, handling both str and list content."""
    content = response.content
    if isinstance(content, list):
        return "".join(block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text")
    return str(content)

##                                     AI Agent                                     ##
def curate_question(state : AgentSchema) -> AgentSchema:
    """
    Curates the user's question based on the database schema.
    
    Args:
        state (AgentSchema): The state of the agent.
        
    Returns:
        AgentSchema: The updated state of the agent.
    """
    user_question= state.user_question
    
    llm = pick_llm("low")
    response = llm.invoke(f"curate the following question: {user_question}")
    state.curated_ques=_get_text(response)
    state.messages= state.messages + [HumanMessage(content=state.curated_ques)]
    return state
    
def prompt_query_context(state : AgentSchema) -> AgentSchema:
    """
    Generates the prompt for the SQL query generation based on the curated question and database schema.
    
    Args:
        state (AgentSchema): The state of the agent.
        
    Returns:
        AgentSchema: The updated state of the agent.
    """
    curated_ques = state.curated_ques
    db_obj = DatabaseUtil(
        db_config={
            "host" : DB_HOST,
            "port" : DB_PORT,
            "user" : DB_USER,
            "password" : DB_PASSWORD,
            "database" : DB_NAME
        }
    )
    schema = db_obj.schema_details("public")
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.  
    
    User's Original Query: {curated_ques}

    Database Schema Details:
    {schema}
    
    """
    state.prompt_query_context = prompt
    return state

def generate_sql(state: AgentSchema) -> AgentSchema:    
    prompt= state.prompt_query_context
    llm= pick_llm("medium")
    response = llm.invoke(prompt)
    
    # Strip markdown formatting if present
    query = _get_text(response).strip()
    if query.startswith("```sql"):
        query = query[6:]
    elif query.startswith("```"):
        query = query[3:]
    if query.endswith("```"):
        query = query[:-3]
    
    state.generated_sql_query=query.strip()
    return state

def is_safe_sql(state: AgentSchema) -> AgentSchema:
    sql_query= state.generated_sql_query
    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)
    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate:
    {sql_query}"""

    response= llm_judge.invoke(prompt)
    state.is_safe = response.answer
    state.comments = response.comments

    return state 
  
def canceled_sql(state: AgentSchema) -> AgentSchema:
     
    comments= state.comments
    state.final_answer= f" Your query has been cancelled due to the following reasons: {comments} "
    state.messages = state.messages + [AIMessage(content=state.final_answer)]  # Append the final answer to the messages list
    return state 

def execute_sql(state: AgentSchema) -> AgentSchema:
    sql_query= state.generated_sql_query
    db_obj = DatabaseUtil(
        db_config={
            "host" : DB_HOST,
            "port" : DB_PORT,
            "user" : DB_USER,
            "password" : DB_PASSWORD,
            "database" : DB_NAME
        }
    )
    execution_result= db_obj.execute_sql(sql_query)
    state.sql_query_execution_result = execution_result
    return state
    
def represent_final_answer(state: AgentSchema) -> AgentSchema:
    execution_result= state.sql_query_execution_result
    curate_question = state.curated_ques
    llm= pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curate_question}
    """
    llm_response = _get_text(llm.invoke(prompt))  # Get the final answer from the LLM

    state.final_answer = llm_response
    state.messages = state.messages + [AIMessage(content=f"{llm_response}")]  # Append the final answer to the messages list

    return state
    

##                                   GRAPHQL AGENT                                      ##


sql_agent_graph= StateGraph(AgentSchema)

## Nodes
sql_agent_graph.add_node("curate_question", curate_question)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_sql)
sql_agent_graph.add_node("is_safe_sql", is_safe_sql)
sql_agent_graph.add_node("canceled_sql", canceled_sql)
sql_agent_graph.add_node("execute_sql", execute_sql)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)


## Edges
sql_agent_graph.add_edge(START, "curate_question")
sql_agent_graph.add_edge("curate_question","prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context","generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")

sql_agent_graph.add_conditional_edges(
    "is_safe_sql",
    lambda x: x.is_safe, 
    {
        "Yes" : "execute_sql",
        "No" : "canceled_sql"
    }
)
sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)
sql_graph_workflow = sql_agent_graph.compile()

if __name__ == "__main__":
    img= Image(sql_graph_workflow.get_graph().draw_mermaid_png())
    with open("sql_agent_graph.png", "wb") as f:
        f.write(img.data)
