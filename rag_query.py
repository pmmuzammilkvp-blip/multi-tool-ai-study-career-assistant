from groq import Groq
import os
import json
from dotenv import load_dotenv
from shared import search_knowledge_base, log_tool_use
from tool import document_search_tool, web_search_tool

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the uploaded study documents/PDFs for information. Use this for questions about the document content.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the internet for current, real-time, or recent information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query"}},
                "required": ["query"]
            }
        }
    }
]

TOOL_LABELS = {
    "search_documents": "Document Search",
    "search_web": "Web Search",
}


def query_rag(question):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful, friendly study assistant. For casual conversation, just respond naturally without using tools. For questions needing document knowledge or current information, use the appropriate tool."
        },
        {"role": "user", "content": question}
    ]

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        tools=tools_definition,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_label = "Direct Reply"

    if response_message.tool_calls:
        messages.append(response_message)

        for tool_call in response_message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            query = func_args.get("query")
            tool_label = TOOL_LABELS.get(func_name, "Direct Reply")

            if func_name == "search_documents":
                result = document_search_tool(query)
            elif func_name == "search_web":
                result = web_search_tool(query)
            else:
                result = "Unknown tool"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        final_response = groq_client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=messages,
            max_tokens=1000
        )
        answer = final_response.choices[0].message.content
    else:
        answer = response_message.content

    log_tool_use(tool_label, question)
    return answer, tool_label


if __name__ == "__main__":
    print("Study Assistant Ready! (type 'exit' to stop)\n")
    while True:
        question = input("Ask your question: ")
        if question.lower() == "exit":
            print("Bye!")
            break
        answer, tool = query_rag(question)
        print(f"\n[{tool}] Answer:", answer, "\n")