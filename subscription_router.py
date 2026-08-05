import os
import logging
from typing import Dict, Any, Optional
from cachetools import TTLCache, cached
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 30-day TTL Cache
vendor_cache = TTLCache(maxsize=500, ttl=2592000)

# Static dictionary for major known vendors
KNOWN_VENDOR_URLS = {
    "amazon": {
        "url": "https://www.amazon.com/mc/pipelines/cancellation",
        "auth_required": True
    },
    "amazon prime": {
        "url": "https://www.amazon.com/mc/pipelines/cancellation",
        "auth_required": True
    },
    "netflix": {
        "url": "https://www.netflix.com/youraccount",
        "auth_required": True
    },
    "hulu": {
        "url": "https://secure.hulu.com/account",
        "auth_required": True
    },
    "spotify": {
        "url": "https://www.spotify.com/account/overview/",
        "auth_required": True
    },
    "disney+": {
        "url": "https://www.disneyplus.com/account",
        "auth_required": True
    },
    "apple": {
        "url": "https://support.apple.com/HT202039",
        "auth_required": True
    }
}

def _search_tavily(vendor_name: str) -> Dict[str, Any]:
    """Tier 2 fallback search using TavilySearchResults or TavilyClient."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    query = f"How to cancel {vendor_name} subscription link billing page"
    
    if not tavily_api_key:
        logger.warning("TAVILY_API_KEY not set. Using basic fallback search instructions.")
        return {
            "target_vendor": vendor_name,
            "action_mode": "tavily_search",
            "requires_auth": False,
            "target_url": f"https://www.google.com/search?q={vendor_name}+cancel+subscription",
            "instructions": f"Navigate to your {vendor_name} account settings or search online to locate the cancellation link."
        }

    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tool = TavilySearchResults(max_results=2)
        results = tool.invoke({"query": query})
        
        target_url = None
        instructions_parts = []

        if isinstance(results, list):
            for res in results:
                if isinstance(res, dict):
                    if not target_url and "url" in res:
                        target_url = res["url"]
                    if "content" in res:
                        instructions_parts.append(res["content"])
        
        instructions = " ".join(instructions_parts)[:300] if instructions_parts else f"Search web results for {vendor_name} cancellation."
        if not target_url:
            target_url = f"https://www.google.com/search?q={vendor_name}+cancel+subscription"

        return {
            "target_vendor": vendor_name,
            "action_mode": "tavily_search",
            "requires_auth": False,
            "target_url": target_url,
            "instructions": instructions
        }
    except Exception as e:
        logger.error(f"Tavily search failed for vendor '{vendor_name}': {e}")
        return {
            "target_vendor": vendor_name,
            "action_mode": "tavily_search",
            "requires_auth": False,
            "target_url": f"https://www.google.com/search?q={vendor_name}+cancel+subscription",
            "instructions": f"Visit {vendor_name} account management settings to cancel your recurring plan."
        }

@cached(cache=vendor_cache)
def resolve_cancel_link(vendor_name: str) -> Dict[str, Any]:
    """Resolves subscription cancellation details using direct match or Tavily search."""
    if not vendor_name or not isinstance(vendor_name, str):
        return None

    clean_vendor = vendor_name.strip().lower()

    # Tier 1: Check known static vendors
    for known_key, data in KNOWN_VENDOR_URLS.items():
        if known_key in clean_vendor or clean_vendor in known_key:
            return {
                "target_vendor": vendor_name,
                "action_mode": "playwright_auto",
                "requires_auth": data["auth_required"],
                "target_url": data["url"],
                "instructions": None
            }

    # Tier 2: Search via Tavily
    return _search_tavily(vendor_name)
