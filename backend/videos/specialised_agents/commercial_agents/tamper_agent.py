import json
import os
import re

from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, create_react_agent

load_dotenv()


api_key = os.environ.get("OPENAI_API_KEY")

# Global variables
collection_name = None
tamper_vector_store = None


def extract_json(input_string):
    """
    Extracts the first JSON code block from the input string and returns it as a Python dictionary.

    Args:
        input_string (str): The input string containing a JSON code block.

    Returns:
        dict: The parsed JSON object.

    Raises:
        ValueError: If no JSON code block is found or if the JSON is invalid.
    """
    # Regular expression to match a JSON code block
    # It looks for ```json (case-insensitive), captures everything until the next ```
    pattern = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

    match = pattern.search(input_string)

    if not match:
        raise ValueError("No JSON code block found in the input string.")

    json_str = match.group(1)

    try:
        # Parse the JSON string into a Python dictionary
        json_data = json.loads(json_str)
        return json_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")


system_message_tampering_agent = """
You are an intelligent assistant specialized in detecting and analyzing tampering incidents involving security systems, ATM machines, locks, or other sensitive corporate assets. Your tasks are as follows:

1. **Retrieve Relevant Information**: Use the 'retrieve' tool to access all pertinent data from the vector store related to the input query.

2. **Detect Tampering Incidents**: Analyze the retrieved content to identify any signs or indications of tampering or unauthorized interference.

3. **Assess Severity**:
    - Determine the severity of each detected tampering incident based on factors such as the level of damage, type of tampering (physical, electronic, etc.), and potential legal or operational consequences.
    - Categorize the severity into one of the following levels:
        - **none**: No tampering detected.
        - **low**: Minor incidents, such as superficial damage or unauthorized but harmless access attempts, with negligible operational impact.
        - **medium**: Noticeable tampering incidents, such as damage requiring repair or moderate interference with normal operations.
        - **high**: Severe tampering incidents, such as destruction of key components, critical breaches, or incidents causing significant operational or financial harm.

4. **Extract Time Intervals**: For each detected tampering incident, extract the corresponding `start_time_seconds` and `end_time_seconds`.

5. **Structured Output**: Present the results in a clear, structured JSON format containing:
    - **severity**: The overall severity level of the detected tampering incidents.
    - **tampering_events**: A list of objects, each with `start_time_seconds` and `end_time_seconds` indicating when the tampering was detected.

**Important Guidelines**:
- Always begin by using the 'retrieve' tool to obtain the relevant vectorized data.
- Focus exclusively on content related to tampering incidents; disregard unrelated information.
- Ensure that the output strictly adheres to the specified JSON structure without additional explanations or narrative.
- If no tampering is detected, set the severity to "none" and provide an empty list for `tampering_events`.

**Example Output**:
```json
{
    "severity": "none",
    "tampering_events": []
}
```
```
{
    "severity": "low",
    "tampering_events": [
        {
            "start_time_seconds": 180,
            "end_time_seconds": 210
        }
    ]
}
```
```json
{
    "severity": "medium",
    "tampering_events": [
        {
            "start_time_seconds": 150,
            "end_time_seconds": 200
        },
        {
            "start_time_seconds": 400,
            "end_time_seconds": 450
        }
    ]
}
```
```json
{
    "severity": "high",
    "tampering_events": [
        {
            "start_time_seconds": 100,
            "end_time_seconds": 130
        },
        {
            "start_time_seconds": 300,
            "end_time_seconds": 350
        }
    ]
}
```
"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message_tampering_agent),
        ("human", "{input}"),
    ]
)


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
llm = ChatOpenAI(model="gpt-4o-mini")


def evaluate_severity(input_string: str) -> str:
    """
    Determines the severity of a tamper situation using LangChain's ChatOpenAI.

    Args:
        system_prompt (str): The system prompt to set the context for the AI model.
        input_string (str): The input string containing information about the fire situation.

    Returns:
        str: A single word indicating the severity: 'neutral', 'low', 'medium', or 'high'.

    Raises:
        ValueError: If the AI model returns an unexpected severity level.
    """

    evaluator_prompt = "You are an assistant that analyzes tampering incident reports and determines their severity."

    # Initialize the ChatOpenAI model with desired parameters
    chat = ChatOpenAI(
        model_name="gpt-4o-mini",  # You can choose other models like "gpt-3.5-turbo" if preferred
        temperature=0,  # Setting temperature to 0 for deterministic output
        openai_api_key=api_key,
    )

    # Define the messages to send to the model
    messages = [
        SystemMessage(content=evaluator_prompt),
        HumanMessage(
            content=f"{input_string}\n\nPlease provide the severity of the tampering situation as a single word: none, low, medium, or high."
        ),
    ]

    # Get the response from the model
    response = chat(messages)

    # Extract and clean the content from the response
    severity = response.content.strip().lower()

    # Define the valid severity levels
    valid_severities = {"neutral", "low", "medium", "high"}

    # Validate the response
    if severity in valid_severities:
        return severity
    else:
        # Handle unexpected responses gracefully
        raise ValueError(
            f"Unexpected severity level returned: '{severity}'. Expected one of {valid_severities}."
        )


@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    global tamper_vector_store
    # 'vector_store' is assumed to be globally accessible or imported.
    retrieved_docs = tamper_vector_store.similarity_search(query, k=2)
    print("Retrieved docs:", retrieved_docs)
    print("Retrieved from CRIME AGENT!")
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


# memory = MemorySaver()

# agent_executor = create_react_agent(llm, [retrieve], checkpointer=memory)


def run_tamper_agent(video_id: int):
    """
    Runs the crime detection agent with a predefined prompt, collects the final
    structured JSON output, and returns it.
    """
    global collection_name, tamper_vector_store
    collection_name = f"video_id_{video_id}"

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    tamper_vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=os.environ.get("POSTGRES_CONNECTION"),
    )

    llm = ChatOpenAI(model="gpt-4o-mini")
    memory = MemorySaver()
    agent_executor = create_react_agent(llm, [retrieve], checkpointer=memory)

    input_message = "Please use the 'retrieve' tool to get the content and then analyze the following vectorized data retrieved from the pgvector database to detect any mentions of crime. Your analysis should focus exclusively on identifying tampering-related incidents, assessing their severity, and extracting the corresponding time intervals. Present your findings in the structured JSON format as specified in the system prompt."

    final_output = ""
    for event in agent_executor.stream(
        {"messages": [{"role": "user", "content": input_message}]},
        stream_mode="values",
        config={"configurable": {"thread_id": "def234"}},
    ):
        messages = event.get("messages", [])
        if messages:
            final_output = messages[-1].content

    try:
        extracted_json = extract_json(final_output)
        if isinstance(extracted_json, dict) and "tampering_incidents" in extracted_json:
            severity = evaluate_severity(final_output)
            extracted_json["tampering_incidents"].append({"severity": severity})
            final_output = json.dumps(extracted_json, indent=2)
            return final_output
    except ValueError as ve:
        print(f"Error: {ve}")
