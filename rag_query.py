from groq import Groq
import os
import re
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from shared import search_knowledge_base, log_tool_use
from tool import document_search_tool, web_search_tool

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# how many earlier messages the agent can see, and how long each one can be
HISTORY_LIMIT = 8
HISTORY_CHARS = 1500

IST = timezone(timedelta(hours=5, minutes=30))

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the uploaded study documents/PDFs for information. Use this for questions about the document content.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "A complete, standalone search query"}},
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
                "properties": {"query": {"type": "string", "description": "A complete, standalone search query with names, event and date/year"}},
                "required": ["query"]
            }
        }
    }
]

TOOL_LABELS = {
    "search_documents": "Document Search",
    "search_web": "Web Search",
}


def build_system_prompt():
    now = datetime.now(IST).strftime("%A, %d %B %Y, %I:%M %p")
    return f"""You are a helpful, friendly study assistant.
Current date and time: {now} IST.

Tool use:
- Casual conversation (greetings, thanks, small talk) and simple general-knowledge questions: answer directly, no tools.
- Questions about the user's uploaded notes or documents: use search_documents.
- Current, recent, live or real-time information (news, sports, scores, prices, weather, recent events): use search_web.
- The user may ask follow-up questions such as "above matches", "that", "it" or "explain more". Use the earlier conversation to work out what they mean.
- When you call a tool, write a complete standalone search query that includes the names, event and date or year from the conversation. Never search with vague words like "above" or "that".

Answer rules:
- Base factual claims on the tool results. If the results do not contain the answer, say so plainly. Do not guess.
- Live events: if the results show something still in progress, say it is live, give the score as of the time shown in the results, say the result is not final, and suggest checking the live scoreboard from the sources. If the results show it has finished, give the final result.
- If sources disagree with each other, mention it briefly.
- You cannot check anything later or follow up on your own. Never offer to check again later or to notify the user. If they want an update, they can simply ask again.
- If you used web search and the results contain URLs, end with a short "Sources:" list of at most 3 of those URLs. Never invent a URL.
- Keep answers clear and reasonably short."""


def _clean_history(history):
    """Keep only recent user/assistant messages (drops extra keys like 'tool')."""
    cleaned = []
    for m in (history or [])[-HISTORY_LIMIT:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            cleaned.append({"role": role, "content": content[:HISTORY_CHARS]})
    return cleaned


def _strip_think(text):
    # remove <think> blocks if the model returns them
    return re.sub(r"<think>.*?(</think>|$)", "", text or "", flags=re.DOTALL).strip()


def query_rag(question, history=None):
    """
    question: the user's new message
    history:  earlier messages as [{"role": "user"|"assistant", "content": "..."}], oldest first,
              NOT including the new question. Optional, so old calls query_rag(question) still work.
    """
    messages = [{"role": "system", "content": build_system_prompt()}]
    messages += _clean_history(history)
    messages.append({"role": "user", "content": question})

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

            try:
                if func_name == "search_documents":
                    result = document_search_tool(query)
                elif func_name == "search_web":
                    result = web_search_tool(query)
                else:
                    result = "Unknown tool"
            except Exception as e:
                # a failing tool should not crash the whole app
                result = f"The tool failed: {e}. Tell the user the search did not work and to try again."

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
        answer = _strip_think(final_response.choices[0].message.content)
    else:
        answer = _strip_think(response_message.content)

    log_tool_use(tool_label, question)
    return answer, tool_label


if __name__ == "__main__":
    print("Study Assistant Ready! (type 'exit' to stop)\n")
    chat_history = []
    while True:
        question = input("Ask your question: ")
        if question.lower() == "exit":
            print("Bye!")
            break
        answer, tool = query_rag(question, history=chat_history)
        chat_history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        print(f"\n[{tool}] Answer:", answer, "\n")