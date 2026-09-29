"""Web search and web content fetching tools with dynamic pagination and sanitization."""

import json
import re
from typing import Any, Dict, Optional
import httpx
from locallm.core.tools.base import tool


def decode_bing_url(u: str) -> str:
    """Decode real destination URL from Bing redirect link."""
    match = re.search(r"[?&]u=a1([a-zA-Z0-9_\-]+)", u)
    if not match:
        return u
    raw = match.group(1)
    pad = 4 - (len(raw) % 4)
    if pad < 4:
        raw += "=" * pad
    try:
        import base64

        decoded = base64.urlsafe_b64decode(raw).decode("utf-8", errors="replace")
        return decoded if decoded.startswith(("http://", "https://")) else u
    except Exception:
        return u


def perform_web_search(
    query: str,
    max_results: int = 5,
    provider: Optional[str] = None,
    custom_api_url: Optional[str] = None,
) -> str:
    """Perform real-time web search and return formatted markdown results with titles, links, and snippets.

    Multi-tier fallback architecture: SearXNG/Custom -> DuckDuckGo -> Bing.
    """
    clean_query = query.strip()
    if not clean_query:
        return "Error: Search query cannot be empty."

    try:
        from locallm.config import load_config

        cfg = load_config()
        chosen_provider = (provider or getattr(cfg, "search_provider", "auto")).strip().lower()
        custom_url = (custom_api_url or getattr(cfg, "search_api_url", "")).strip()
    except Exception:
        chosen_provider = (provider or "auto").strip().lower()
        custom_url = (custom_api_url or "").strip()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # 1. Custom / SearXNG endpoint if configured
    if custom_url or chosen_provider == "custom":
        if not custom_url:
            return "Error: Custom search provider chosen but no search_api_url is configured."
        target_url = custom_url.replace("{query}", clean_query)
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                res = client.get(target_url)
                if res.status_code == 200:
                    try:
                        data = res.json()
                        results_list = data.get("results", []) if isinstance(data, dict) else []
                        items = []
                        for item in results_list[:max_results]:
                            t = item.get("title", "")
                            u = item.get("url", "")
                            s = item.get("content", "") or item.get("snippet", "")
                            items.append(f"- **[{t}]({u})**\n  {s}")
                        if items:
                            return f"Web Search Results for '{clean_query}':\n\n" + "\n\n".join(items)
                    except Exception:
                        return f"Custom Search Response:\n{res.text[:3500]}"
        except Exception as exc:
            if chosen_provider == "custom":
                return f"Error contacting custom search endpoint: {exc}"

    # 2. DuckDuckGo Search
    if chosen_provider in ("duckduckgo", "auto"):
        try:
            with httpx.Client(timeout=6.0, follow_redirects=True, headers=headers) as client:
                resp = client.post("https://html.duckduckgo.com/html/", data={"q": clean_query})
                if resp.status_code == 200 and "result__snippet" in resp.text:
                    blocks = re.findall(r'<div class="result__body"[^>]*>([\s\S]*?)</div>', resp.text)
                    items = []
                    for b in blocks[:max_results]:
                        link_m = re.search(r'<a[^>]+class="result__url"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', b)
                        title_m = re.search(r'<a[^>]+class="result__snippet"[^>]*>([\s\S]*?)</a>', b)
                        if link_m:
                            url = link_m.group(1).strip()
                            title = re.sub(r"<[^>]+>", "", link_m.group(2)).strip()
                            snip = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""
                            items.append(f"- **[{title}]({url})**\n  {snip}")
                    if items:
                        return f"Web Search Results for '{clean_query}' (DuckDuckGo):\n\n" + "\n\n".join(items)
        except Exception:
            pass

    # 3. Bing Search (Fast, robust, globally accessible without ISP blocking)
    try:
        url = f"https://www.bing.com/search?q={clean_query}&setlang=en"
        with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
            res = client.get(url)
            if res.status_code == 200:
                blocks = re.findall(r'<li class="b_algo"[^>]*>([\s\S]*?)</li>', res.text)
                items = []
                import html

                for b in blocks:
                    h2_m = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>\s*</h2>', b)
                    if not h2_m:
                        continue
                    raw_url = html.unescape(h2_m.group(1))
                    real_url = decode_bing_url(raw_url)
                    title = re.sub(r"<[^>]+>", "", h2_m.group(2)).strip()
                    p_m = re.search(r'<p[^>]*>([\s\S]*?)</p>', b)
                    snippet = re.sub(r"<[^>]+>", "", p_m.group(1)).strip() if p_m else ""
                    if title and real_url:
                        items.append(f"- **[{title}]({real_url})**\n  {snippet}")
                    if len(items) >= max_results:
                        break

                if items:
                    return f"Web Search Results for '{clean_query}':\n\n" + "\n\n".join(items)
    except Exception:
        pass

    return f"No search results found or web search failed for query: '{clean_query}'."


def fetch_web_fn(
    url: str,
    offset: int = 0,
    max_chars: int = 4000,
) -> str:
    """Fetch webpage content with specialized GitHub API integration and dynamic pagination."""
    clean_url = url.strip()
    if not clean_url:
        return "Error: URL is required."
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    }

    full_text = ""

    # 1. GitHub Releases / Tags URL
    gh_rel_match = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)/(?:releases|tags)/?$", clean_url)
    if gh_rel_match:
        owner, repo = gh_rel_match.group(1), gh_rel_match.group(2)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=5"
        gh_headers = dict(headers)
        gh_headers["Accept"] = "application/vnd.github.v3+json"
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=gh_headers) as client:
                api_res = client.get(api_url)
                if api_res.status_code == 200:
                    releases = api_res.json()
                    if isinstance(releases, list) and releases:
                        lines = [f"GitHub Releases for {owner}/{repo} (Latest {len(releases)} releases):"]
                        for idx, rel in enumerate(releases):
                            tag = rel.get("tag_name", "unknown")
                            rel_name = rel.get("name") or tag
                            pub_at = rel.get("published_at", "")[:10]
                            prerelease = " [Pre-release]" if rel.get("prerelease") else ""
                            body = (rel.get("body") or "").strip()
                            body_snip = re.sub(r"[\r\n]+", " ", body)[:250]
                            if idx == 0:
                                lines.append(f"\n★ Latest Release: {tag} ({rel_name}){prerelease} - Published: {pub_at}")
                                if body_snip:
                                    lines.append(f"  Notes: {body_snip}...")
                            else:
                                lines.append(f"- {tag} ({rel_name}){prerelease} - {pub_at}")
                        full_text = "\n".join(lines)

                if not full_text:
                    tags_url = f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=5"
                    tags_res = client.get(tags_url)
                    if tags_res.status_code == 200:
                        tags_data = tags_res.json()
                        if isinstance(tags_data, list) and tags_data:
                            tag_names = [t.get("name") for t in tags_data if t.get("name")]
                            full_text = f"GitHub Tags for {owner}/{repo}:\nLatest tags: " + ", ".join(tag_names)
        except Exception:
            pass

    # 2. Specific GitHub release tag URL
    if not full_text:
        gh_tag_match = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)/releases/tag/([^/#?]+)/?$", clean_url)
        if gh_tag_match:
            owner, repo, tag = gh_tag_match.group(1), gh_tag_match.group(2), gh_tag_match.group(3)
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
            gh_headers = dict(headers)
            gh_headers["Accept"] = "application/vnd.github.v3+json"
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True, headers=gh_headers) as client:
                    api_res = client.get(api_url)
                    if api_res.status_code == 200:
                        rel = api_res.json()
                        rel_name = rel.get("name") or tag
                        pub_at = rel.get("published_at", "")[:10]
                        body = (rel.get("body") or "").strip()[:1000]
                        full_text = f"GitHub Release {tag} ({rel_name}) for {owner}/{repo} (Published: {pub_at}):\n\n{body}"
            except Exception:
                pass

    # 3. GitHub repository root URL -> Direct README fetch
    if not full_text:
        gh_match = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)/?$", clean_url)
        if gh_match:
            owner, repo = gh_match.group(1), gh_match.group(2)
            raw_readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
            try:
                with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
                    gh_res = client.get(raw_readme_url)
                    if gh_res.status_code == 200 and gh_res.text.strip():
                        full_text = f"GitHub Repository: {owner}/{repo}\nREADME Content:\n" + gh_res.text
            except Exception:
                pass

    # 4. GitHub repository details API URL -> Compact repo stats
    if not full_text:
        gh_repo_api = re.match(r"^https?://api\.github\.com/repos/([^/]+)/([^/#?]+)/?$", clean_url)
        if gh_repo_api:
            owner, repo = gh_repo_api.group(1), gh_repo_api.group(2)
            gh_headers = dict(headers)
            gh_headers["Accept"] = "application/vnd.github.v3+json"
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True, headers=gh_headers) as client:
                    api_res = client.get(clean_url)
                    if api_res.status_code == 200:
                        data = api_res.json()
                        if isinstance(data, dict):
                            compact = {
                                "name": data.get("full_name") or f"{owner}/{repo}",
                                "description": data.get("description", ""),
                                "stars": data.get("stargazers_count", 0),
                                "forks": data.get("forks_count", 0),
                                "open_issues": data.get("open_issues_count", 0),
                                "license": data.get("license", {}).get("name") if isinstance(data.get("license"), dict) else data.get("license"),
                                "language": data.get("language", ""),
                                "created_at": data.get("created_at", ""),
                                "updated_at": data.get("updated_at", ""),
                            }
                            full_text = f"GitHub Repository Data for {owner}/{repo}:\n" + json.dumps(compact, indent=2)
            except Exception:
                pass

    # 5. General Web / API Scraping with high-signal content extraction
    if not full_text:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                res = client.get(clean_url)
                if res.status_code != 200:
                    return f"HTTP {res.status_code}: Unable to access {clean_url}"

                raw_text = res.text
                content_type = res.headers.get("content-type", "").lower()
                if "application/json" in content_type or (raw_text.strip().startswith(("{", "[")) and raw_text.strip().endswith(("}", "]"))):
                    try:
                        parsed_json = json.loads(raw_text)
                        full_text = json.dumps(parsed_json, indent=2)
                    except Exception:
                        full_text = raw_text
                else:
                    raw_html = raw_text
                    # Remove boilerplate blocks (scripts, styles, navigation, headers, footers)
                    clean = re.sub(r"<(script|style|nav|header|footer|aside)[^>]*>[\s\S]*?</\1>", " ", raw_html, flags=re.IGNORECASE)
                    # Keep line breaks around paragraphs and headings
                    clean = re.sub(r"</?(?:p|div|h[1-6]|li|br)[^>]*>", "\n", clean, flags=re.IGNORECASE)
                    # Strip remaining tags
                    clean = re.sub(r"<[^>]+>", " ", clean)
                    # Normalize line breaks and spaces
                    clean = re.sub(r"[ \t]+", " ", clean)
                    clean = re.sub(r"\n\s*\n+", "\n\n", clean).strip()
                    full_text = clean if clean else "(Empty or non-text content retrieved)"
        except Exception as exc:
            return f"Error fetching URL '{clean_url}': {exc}"

    if not full_text:
        return f"Unable to retrieve content from {clean_url}."

    # Dynamic Pagination & Truncation
    total_len = len(full_text)
    safe_offset = max(0, int(offset))
    safe_max = max(1, int(max_chars)) if max_chars else 4000

    if safe_offset >= total_len and total_len > 0:
        return f"Error: Offset {safe_offset} is beyond the total content length ({total_len} characters)."

    chunk = full_text[safe_offset : safe_offset + safe_max]
    next_offset = safe_offset + len(chunk)

    if total_len > next_offset:
        notice = (
            f"[Showing characters {safe_offset} to {next_offset} of {total_len}. "
            f"To read the next chunk, call fetch_web with offset={next_offset}]\n\n"
        )
        return notice + chunk
    elif safe_offset > 0:
        notice = f"[Showing characters {safe_offset} to {next_offset} of {total_len} (End of content)]\n\n"
        return notice + chunk
    return chunk


# Register tools
tool(
    name="search_web",
    description="Search the live internet for real-time information, documentation, news, or answers to unknown questions. Returns top search results with titles, snippets, and URLs.",
    parameters={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query keywords (e.g. 'latest python release', 'fastapi tutorial', 'company news')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return (default is 5)",
            },
        },
    },
    is_mutating=False,
    categories={"assistant", "telegram", "whatsapp"},
)(perform_web_search)

tool(
    name="fetch_web",
    description="Fetch and read text content from a web page, GitHub repository, or URL with optional offset pagination.",
    parameters={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "description": "HTTP or HTTPS URL to fetch (e.g. https://github.com/owner/repo or article link)",
            },
            "offset": {
                "type": "integer",
                "description": "Character offset to start reading from (default is 0)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return in this chunk (default is 4000)",
            },
        },
    },
    is_mutating=False,
    categories={"assistant", "telegram", "whatsapp"},
)(fetch_web_fn)
