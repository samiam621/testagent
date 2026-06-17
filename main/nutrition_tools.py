import json

from ddgs import DDGS
from langchain.tools import tool


from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re


@tool
def search_tool(query: str) -> str:
    """
    Search DuckDuckGo for detailed nutrition information about a specific food item.
    Appends 'nutrition facts calories protein fat carbs' to the query for better results.
    Returns the top 5 result snippets as plain text.
    """
    enriched_query = f"{query} nutrition facts calories protein fat carbs"
 
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(enriched_query, max_results=5))
    except Exception as e:
        return f"Search failed: {e}"
 
    if not results:
        return "No search results found."
 
    snippets = [
        f"Source: {r.get('href', 'N/A')}\n{r.get('body', '').strip()}"
        for r in results
    ]
    return "\n\n---\n\n".join(snippets)


@tool
def scrape_tool(query: str) -> str:
    """
    Scrape the top DuckDuckGo result for the given query to identify food items.
    Use this first to discover a list of foods to research. Returns page text content
    (up to 3000 characters). Falls back to DuckDuckGo snippets if scraping is blocked.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
    except Exception as e:
        return f"Search for scraping failed: {e}"
 
    if not results:
        return "No results found for the query."
 
    top_url = results[0].get("href", "")
 
    if top_url:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            response = requests.get(top_url, headers=headers, timeout=10)
            response.raise_for_status()
 
            soup = BeautifulSoup(response.text, "html.parser")
 
            # Strip boilerplate tags before extracting text
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
 
            text = soup.get_text(separator="\n", strip=True)
            # Trim to a reasonable size to avoid overwhelming the context window
            return text[:3000]
 
        except Exception:
            pass  # Fall through to snippet fallback below
 
    # Fallback: return DuckDuckGo result snippets if scraping failed or was blocked
    snippets = [r.get("body", "").strip() for r in results if r.get("body")]
    return "\n\n---\n\n".join(snippets)
 

@tool
def save_tool(content: str) -> str:
    """
    Save the structured nutrition data to a timestamped .txt file in JSON format.
    Pass the JSON-formatted string of all nutrition results as the 'content' argument.
    Pretty-prints valid JSON automatically; saves plain text as a fallback.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nutrition_results_{timestamp}.txt"
 
    try:
        parsed = json.loads(content)
        output = json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, ValueError):
        # Content isn't valid JSON — save as-is
        output = content
 
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output)
        return f"Successfully saved nutrition data to '{filename}'."
    except OSError as e:
        return f"Failed to save file: {e}"