import os

from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, create_react_agent

load_dotenv()


api_key = os.environ.get("OPENAI_API_KEY")

# Global variables
collection_name = None
customer_behaviour_vector_store = None

system_customer_behaviour_message = """
You are an intelligent assistant specialized in analyzing user behavior based on vectorized data retrieved from a database. Your task is to:

1. First use the 'retrieve' tool to get all relevant information from the vector store.
2. Analyze the retrieved content thoroughly.
3. Identify and report patterns of user behavior, including but not limited to:
    - Areas or sections where users spend the most time.
    - Peak activity times and high-traffic zones.
    - Unusual or noteworthy behavior patterns.
    - Popular products or services based on interaction data.
4. Provide actionable insights and detailed observations based on the data.
5. Focus on trends, correlations, and anomalies that can inform strategic decisions.

Always start by using the retrieve tool to get the relevant data from the vector store before performing your analysis. Present the results in a clear, structured format with detailed insights and recommendations.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_customer_behaviour_message),
        ("human", "{input}"),
    ]
)


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4o-mini")


@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    global customer_behaviour_vector_store
    # 'vector_store' is assumed to be globally accessible or imported.
    retrieved_docs = customer_behaviour_vector_store.similarity_search(query, k=2)
    print("Retrieved docs:", retrieved_docs)
    print("Retrieved from SUMMARY AGENT!")
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


# memory = MemorySaver()

# agent_executor = create_react_agent(llm, [retrieve], checkpointer=memory)


def run_customer_behaviour_agent(video_id: int):
    """
    Runs the agent with a default prompt, collects the final
    message in a variable, and returns it.
    """
    global collection_name, customer_behaviour_vector_store
    collection_name = f"video_id_{video_id}"

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    customer_behaviour_vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=os.environ.get("POSTGRES_CONNECTION"),
    )

    llm = ChatOpenAI(model="gpt-4o-mini")
    memory = MemorySaver()
    agent_executor = create_react_agent(llm, [retrieve], checkpointer=memory)

    input_message = """
        Please use the 'retrieve' tool to get the content and then analyze the following vectorized data retrieved from a pgvector database. Your analysis should focus on user behavior patterns, including time spent in specific areas, activity trends, high-traffic zones, product/service popularity, and any unusual or noteworthy behavior. Provide a detailed, structured report with actionable insights and observations that can help in strategic decision-making.
    """

    final_output = ""
    for event in agent_executor.stream(
        {"messages": [{"role": "user", "content": input_message}]},
        stream_mode="values",
        config={"configurable": {"thread_id": "def234"}},
    ):
        messages = event.get("messages", [])
        if messages:
            final_output = messages[-1].content

    return final_output
