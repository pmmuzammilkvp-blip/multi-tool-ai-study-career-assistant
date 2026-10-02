import os
from dotenv import load_dotenv
from tavily import TavilyClient
from shared import search_knowledge_base

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def document_search_tool(query):
    chunks, metadatas = search_knowledge_base(query)
    context = "\n\n".join([
        f"[Source: {meta['source']}]\n{chunk}"
        for chunk, meta in zip(chunks, metadatas)
    ])
    return context


def web_search_tool(query):
    response = tavily_client.search(query=query, max_results=3)
    results = response.get("results", [])
    formatted = "\n\n".join([
        f"[{r['title']}]\n{r['content']}"
        for r in results
    ])
    return formatted