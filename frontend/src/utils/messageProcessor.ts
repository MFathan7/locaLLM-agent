import type { SourceItem } from '../types';

/**
 * Known domain brand mappings for beautiful source badge rendering.
 */
const BRAND_NAMES: Record<string, string> = {
  'reddit.com': 'Reddit',
  'arxiv.org': 'arXiv',
  'github.com': 'GitHub',
  'youtube.com': 'YouTube',
  'twitter.com': 'X (Twitter)',
  'x.com': 'X',
  'medium.com': 'Medium',
  'dev.to': 'DEV Community',
  'stackoverflow.com': 'Stack Overflow',
  'wikipedia.org': 'Wikipedia',
  'google.com': 'Google',
  'huggingface.co': 'Hugging Face',
  'openai.com': 'OpenAI',
  'anthropic.com': 'Anthropic',
  'microsoft.com': 'Microsoft',
  'amazon.com': 'Amazon',
  'docs.python.org': 'Python Docs',
  'lowcode.agency': 'LowCode Agency',
  'toolbrain.com': 'ToolBrain',
  'aiforcode.io': 'aiforcode.io',
  'andrew.ooo': 'andrew.ooo',
};

/**
 * Extract clean hostname without www prefix.
 */
export function getDomain(urlStr: string): string {
  try {
    const parsed = new URL(urlStr);
    return parsed.hostname.replace(/^www\./i, '').toLowerCase();
  } catch {
    const match = urlStr.match(/https?:\/\/(?:www\.)?([^/\s?#]+)/i);
    return match ? match[1].toLowerCase() : urlStr;
  }
}

/**
 * Format friendly human-readable publisher/site name.
 */
export function getSiteName(domain: string, title?: string): string {
  const cleanDomain = domain.toLowerCase();
  if (BRAND_NAMES[cleanDomain]) {
    return BRAND_NAMES[cleanDomain];
  }

  // Check if title has source prefix like "ToolBrain - Title" or "Title | LowCode Agency"
  if (title) {
    const barMatch = title.match(/(?:^|\s*\|\s*|\s*-\s*)([A-Z][a-zA-Z0-9\s]{2,20})$/);
    if (barMatch) {
      return barMatch[1].trim();
    }
  }

  // Derive from domain parts
  const parts = cleanDomain.split('.');
  if (parts.length >= 2) {
    const first = parts[0];
    return first.charAt(0).toUpperCase() + first.slice(1);
  }

  return cleanDomain;
}

export interface ProcessedMessageContent {
  thinking: string;
  response: string;
  isThinking: boolean;
}

/**
 * Remove directives, web search raw dumps, and JSON tool call artifacts from final text.
 */
function cleanDirectivesAndArtifacts(text: string): string {
  if (!text) return '';
  let cleaned = text;

  // 1. Remove [Web Search Results for '...']: block dumps
  cleaned = cleaned.replace(
    /(?:\[?Web Search Results for '[^']+']?:?|\[Web Search Notice[^\]]*\]:?)\s*[\s\S]*?(?=(?:\n\n|\r?\n)(?:Based on|According to|Here (?:are|is)|Summary|In summary|Tentu|Baik|Berdasarkan|[A-Z#]))/gi,
    ''
  );

  // 2. Remove system directive leaks e.g. "Directives: ..." or "Directives (Tools Enabled): ..."
  cleaned = cleaned.replace(
    /(?:^|\n\n)Directives(?:\s*\([^)]*\))?:\s*[\s\S]*?(?=(?:\n\n|\r?\n)(?:[A-Z#]|Based on|Tentu|Baik|$))/gi,
    ''
  );

  // 3. Remove standalone JSON tool call blocks (e.g. ```json {"tool": ...} ``` or raw { "command": "search_web", ... })
  cleaned = cleaned.replace(/```(?:json|tool_calls?)?\s*\{[\s\S]*?"(?:tool|action|name|command|function)":[\s\S]*?\}\s*```/gi, '');
  cleaned = cleaned.replace(/\{[\s\S]*?"(?:command|tool|action|function)"\s*:[\s\S]*?"(?:parameters|arguments|query)"[\s\S]*?\}/gi, '');
  cleaned = cleaned.replace(/\{[\s\S]*?"reasoning"\s*:[\s\S]*?"command"\s*:[\s\S]*?\}/gi, '');

  // 4. Remove dangling tool preambles (e.g. "I'll search for ... for you.")
  cleaned = cleaned.replace(/^(?:I(?:'ll| will)\s+(?:search|look up|check|browse)\s+[\s\S]*?(?:for you|online)\.?\s*)$/gim, '');

  // 5. Clean leading response labels like "Response:", "**Response:**", "**Answer:**"
  cleaned = cleaned.replace(/^(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer|Jawaban|Hasil)(?:\*\*|\*|:|\s)*\n?/i, '');

  return cleaned.trim();
}

/**
 * Robustly extract thinking / chain of thought and clean response for both XML tags and prose-based models (Gemma, Qwen, etc.).
 */
export function extractThinkingAndResponse(rawText: string): ProcessedMessageContent {
  if (!rawText) return { thinking: '', response: '', isThinking: false };

  const text = rawText.trim();

  // Case 1: Tag-based reasoning (<think>...</think> or <thought>...</thought>)
  const closedTagMatch = text.match(/<(?:think|thought)>([\s\S]*?)<\/(?:think|thought)>/i);
  if (closedTagMatch) {
    const thinking = closedTagMatch[1].trim();
    const rawResponse = text.replace(/<(?:think|thought)>[\s\S]*?<\/(?:think|thought)>/i, '').trim();
    return {
      thinking,
      response: cleanDirectivesAndArtifacts(rawResponse),
      isThinking: false
    };
  }

  // Unclosed <think> or <thought> tag (currently streaming thinking tokens)
  const unclosedTagMatch = text.match(/<(?:think|thought)>([\s\S]*)$/i);
  if (unclosedTagMatch) {
    return {
      thinking: unclosedTagMatch[1].trim(),
      response: '',
      isThinking: true
    };
  }

  // Case 2: Prose-based thinking headers (e.g. Gemma, Llama, Qwen outputting markdown or labeled thinking)
  const proseThinkHeaderRegex = /^(?:(?:\*\*|\*|#+\s*)?(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning|Internal Thought|Plan)(?:\*\*|\*|:|\s)*|Here(?:'s| is) a thinking process(?: that leads to[^\n:]*)?:?|Let(?:'s| us) think step by step:?)(?:\r?\n)?/i;

  if (proseThinkHeaderRegex.test(text)) {
    const startMatch = text.match(proseThinkHeaderRegex);
    const startLen = startMatch ? startMatch[0].length : 0;
    const afterHeader = text.slice(startLen);

    // Look for transition to final response:
    // **Response:**, **Answer:**, **Final Answer:**, Response:, Answer:, Final Answer:, ### Response, etc.
    const responseTransitionRegex = /(?:\r?\n|\n\n)(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer|Output|Hasil|Jawaban|Kesimpulan)(?:\*\*|\*|:|\s)*(?:\r?\n|$)/i;
    const transMatch = afterHeader.match(responseTransitionRegex);

    if (transMatch && transMatch.index !== undefined) {
      const thinking = afterHeader.slice(0, transMatch.index).trim();
      const rawResponse = afterHeader.slice(transMatch.index + transMatch[0].length).trim();
      return {
        thinking,
        response: cleanDirectivesAndArtifacts(rawResponse),
        isThinking: false
      };
    }

    // ReAct style Final Answer:
    const finalAnswerMatch = afterHeader.match(/(?:\r?\n)(?:Final Answer|Jawaban Akhir):\s*/i);
    if (finalAnswerMatch && finalAnswerMatch.index !== undefined) {
      const thinking = afterHeader.slice(0, finalAnswerMatch.index).trim();
      const rawResponse = afterHeader.slice(finalAnswerMatch.index + finalAnswerMatch[0].length).trim();
      return {
        thinking,
        response: cleanDirectivesAndArtifacts(rawResponse),
        isThinking: false
      };
    }

    // Still streaming thinking or no transition tag yet
    return {
      thinking: afterHeader.trim(),
      response: '',
      isThinking: true
    };
  }

  // Case 3: Embedded think block within text
  const embeddedMatch = text.match(/(?:(?:\n\n|\r?\n)(?:\*\*|\*|#+\s*)?(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning)(?:\*\*|\*|:|\s)*)([\s\S]*?)(?=(?:\n\n|\r?\n)(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer)(?:\*\*|\*|:|\s)*|$)/i);
  if (embeddedMatch && embeddedMatch.index !== undefined) {
    const thinking = embeddedMatch[1].trim();
    let rawResponse = (text.slice(0, embeddedMatch.index) + text.slice(embeddedMatch.index + embeddedMatch[0].length)).trim();
    rawResponse = rawResponse.replace(/^(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer)(?:\*\*|\*|:|\s)*/i, '').trim();
    return {
      thinking,
      response: cleanDirectivesAndArtifacts(rawResponse),
      isThinking: false
    };
  }

  // Case 4: No thinking detected
  return {
    thinking: '',
    response: cleanDirectivesAndArtifacts(text),
    isThinking: false
  };
}

/**
 * Remove thinking blocks, intermediate tool calls, search queries, and agent steps from displayed content.
 */
export function cleanAssistantContent(rawText: string): string {
  if (!rawText) return '';
  const parsed = extractThinkingAndResponse(rawText);
  return parsed.response;
}

/**
 * Returns true if the message currently contains only thinking tokens and no final answer yet.
 */
export function isOnlyThinking(rawText: string): boolean {
  if (!rawText) return false;
  const parsed = extractThinkingAndResponse(rawText);
  return parsed.isThinking || (parsed.thinking.length > 0 && parsed.response.length === 0);
}

/**
 * Extract active thinking step, reasoning status, or search status from intermediate stream.
 * Returns clean generic statuses without leaking internal CoT text.
 */
export function extractCurrentThinkingStep(rawText: string): string {
  if (!rawText) return 'Generating...';

  // 1. Tool execution & search progress indicators
  if (/Searching (?:the )?web/i.test(rawText) || /"query"\s*:/i.test(rawText)) {
    return 'Searching...';
  }

  if (/Executing tool|Running (?:tool|python|bash|script)/i.test(rawText)) {
    if (/python/i.test(rawText)) return 'Running Python...';
    return 'Running tool...';
  }

  // 2. CoT reasoning tags
  if (/<(?:think|thought)>/i.test(rawText) || /thinking process|thought:/i.test(rawText)) {
    return 'Thinking...';
  }

  return 'Generating...';
}

/**
 * Extract external sources, web search citations, and reference links from message text.
 */
export function extractSourcesFromText(content: string, existingSources?: SourceItem[]): SourceItem[] {
  const items: SourceItem[] = existingSources ? [...existingSources] : [];
  const seenUrls = new Set<string>(items.map(s => s.url.toLowerCase().replace(/\/$/, '')));

  if (!content) return items;

  // 1. Extract markdown links: [Title](https://...)
  const mdLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)"'>]+)\)/g;
  let match: RegExpExecArray | null;

  while ((match = mdLinkRegex.exec(content)) !== null) {
    const rawTitle = match[1].trim();
    const rawUrl = match[2].trim();
    const cleanUrlKey = rawUrl.toLowerCase().replace(/\/$/, '');

    // Skip local anchors, image files or already processed URLs
    if (seenUrls.has(cleanUrlKey) || rawUrl.startsWith('#')) continue;
    seenUrls.add(cleanUrlKey);

    const domain = getDomain(rawUrl);
    const siteName = getSiteName(domain, rawTitle);

    items.push({
      id: `src-${items.length}-${Math.random().toString(36).slice(2, 7)}`,
      title: rawTitle,
      url: rawUrl,
      domain: siteName,
      snippet: rawUrl,
      favicon: `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
    });
  }

  // 2. Extract Web Search structured blocks: - **[Title](url)** \n snippet
  const searchItemRegex = /-\s+\*\*\[([^\]]+)\]\((https?:\/\/[^\s)"'>]+)\)\*\*\s*(?:\n\s+([^\n]+))?/g;
  while ((match = searchItemRegex.exec(content)) !== null) {
    const title = match[1].trim();
    const url = match[2].trim();
    const snippet = match[3]?.trim();
    const cleanUrlKey = url.toLowerCase().replace(/\/$/, '');

    const existingIdx = items.findIndex(i => i.url.toLowerCase().replace(/\/$/, '') === cleanUrlKey);
    if (existingIdx !== -1) {
      if (snippet && !items[existingIdx].snippet) {
        items[existingIdx].snippet = snippet;
      }
      continue;
    }

    seenUrls.add(cleanUrlKey);
    const domain = getDomain(url);
    const siteName = getSiteName(domain, title);

    items.push({
      id: `src-${items.length}-${Math.random().toString(36).slice(2, 7)}`,
      title,
      url,
      domain: siteName,
      snippet,
      favicon: `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
    });
  }

  // 3. Extract raw URLs if not already matched
  const rawUrlRegex = /(https?:\/\/[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=%]+)/g;
  while ((match = rawUrlRegex.exec(content)) !== null) {
    const url = match[1].replace(/[.,;)]$/, '');
    const cleanUrlKey = url.toLowerCase().replace(/\/$/, '');

    if (seenUrls.has(cleanUrlKey)) continue;
    seenUrls.add(cleanUrlKey);

    const domain = getDomain(url);
    const siteName = getSiteName(domain);

    // Form title from path or domain
    let autoTitle = domain;
    try {
      const u = new URL(url);
      const pathSegments = u.pathname.split('/').filter(Boolean);
      if (pathSegments.length > 0) {
        autoTitle = `${siteName}: ${pathSegments[pathSegments.length - 1].replace(/[-_]/g, ' ')}`;
      }
    } catch {
      // Ignore URL parsing errors for non-standard schemes
    }

    items.push({
      id: `src-${items.length}-${Math.random().toString(36).slice(2, 7)}`,
      title: autoTitle,
      url,
      domain: siteName,
      snippet: url,
      favicon: `https://www.google.com/s2/favicons?domain=${domain}&sz=32`
    });
  }

  return items;
}

/**
 * Sanitize a chat title to ensure no <think> or <thought> tags, markdown or quotes leak into UI.
 */
export function sanitizeChatTitle(rawTitle: string, fallback: string = 'New conversation'): string {
  if (!rawTitle) return fallback;
  let cleaned = rawTitle
    .replace(/<(?:think|thought)>[\s\S]*?(?:<\/(?:think|thought)>|$)/gi, '')
    .replace(/^["'«»“”\s*#`_-]+|["'«»“”\s*#`_-]+$/g, '')
    .replace(/^(?:Title|Judul|Topic|Subjek)\s*:\s*/i, '')
    .trim();

  // If unclosed tag or leftover think remains
  if (!cleaned || cleaned.toLowerCase().includes('<think') || cleaned.toLowerCase().includes('</think') || cleaned.toLowerCase().includes('<thought')) {
    return fallback;
  }
  const firstLine = cleaned.split('\n')[0].trim();
  return firstLine.slice(0, 48) || fallback;
}

/**
 * Generate a smart heuristic title from user prompt by stripping conversational filler words.
 */
export function generateSmartTitleFallback(rawPrompt: string): string {
  if (!rawPrompt || !rawPrompt.trim()) return 'New conversation';

  let cleaned = rawPrompt
    .replace(/<(?:think|thought)>[\s\S]*?(?:<\/(?:think|thought)>|$)/gi, '')
    .trim();

  if (!cleaned) return 'New conversation';

  // Strip common conversational openings in Indonesian & English
  const conversationalPrefixes = [
    /^(?:halo|hai|hey|hello|hi)\s*(?:locallm|bot|ai)?[\s,:-]*/i,
    /^(?:tolong|bisa|coba|mohon|harap)\s*(?:kamu|anda|bantu|buatkan|jelaskan|tuliskan|carikan)?\s*/i,
    /^(?:bantu\s+(?:saya|aku)\s+(?:untuk)?\s*)/i,
    /^(?:bagaimana\s+cara(?:nya)?\s*(?:untuk)?\s*)/i,
    /^(?:apa\s+(?:itu|yang\s+dimaksud\s+dengan)\s*)/i,
    /^(?:can\s+you\s+(?:please\s+)?(?:help\s+me\s+)?(?:to\s+)?(?:write|code|create|explain|summarize)?\s*)/i,
    /^(?:please\s+(?:help\s+me\s+)?(?:to\s+)?(?:write|code|create|explain)?\s*)/i,
    /^(?:how\s+to\s+)/i,
    /^(?:what\s+is\s+)/i
  ];

  for (const regex of conversationalPrefixes) {
    cleaned = cleaned.replace(regex, '').trim();
  }

  // Capitalize first character
  if (cleaned.length > 0) {
    cleaned = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }

  // Take the first 5-8 words or max 36 chars
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length > 6) {
    cleaned = words.slice(0, 6).join(' ');
  }

  if (cleaned.length > 38) {
    cleaned = cleaned.slice(0, 38).trim() + '...';
  }

  return cleaned || 'New conversation';
}

