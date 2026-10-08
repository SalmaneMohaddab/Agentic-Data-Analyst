from agents.Data_Agent import data_agent_graph_workflow
from langchain_core.messages import HumanMessage


if __name__ == "__main__":
    print("AI Data Agent")
    print("Type 'exit' to quit")
    while True:
        user_input=input("You: ")
        if user_input.lower() == "exit":
            break
        response = data_agent_graph_workflow.invoke(
            {"messages": [HumanMessage(content=user_input)]}
        )
        print(response['messages'][-1].content)