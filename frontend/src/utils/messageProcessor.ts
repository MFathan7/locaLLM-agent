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

  // 5. Clean leading response labels like "Response:", "**Response:**", "**Answer:**" or "(Proceeds to generate output)."
  cleaned = cleaned.replace(/^(?:\*+\s*(?:Okay,?\s*)?(?:ready to write|let's write|let us draft|drafting) the response\.?\*+\s*)/i, '');
  cleaned = cleaned.replace(/^(?:\((?:Proceeds to )?(?:generate|write|draft) (?:output|response)\)\.?\s*)/i, '');
  cleaned = cleaned.replace(/^(?:Let's write it\.(?:[a-z]{0,4}\s*)?)/i, '');
  cleaned = cleaned.replace(/^(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer|Jawaban|Hasil)(?:\*\*|\*|:|\s)*\n?/i, '');

  return cleaned.trim();
}

/**
 * Extract thinking / chain of thought and clean response for both XML tags and prose-based models (Gemma, Qwen, etc.).
 */
export function extractThinkingAndResponse(rawText: string): ProcessedMessageContent {
  if (!rawText) return { thinking: '', response: '', isThinking: false };

  // 0. Pre-clean web search dumps and directives so thinking headers at the stream beginning can be detected accurately
  const text = cleanDirectivesAndArtifacts(rawText).trim();
  if (!text) return { thinking: '', response: '', isThinking: false };

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

  // Case 2: Prose-based thinking headers (e.g. Gemma outputting "Here's a thinking process that leads to the suggested response:")
  const proseThinkHeaderRegex = /^(?:(?:\*\*|\*|#+\s*|>+\s*)?(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning|Internal Thought|Plan)(?:\*\*|\*|:|\s)*|(?:\*\*|\*|>+\s*)?Here(?:'s| is) a thinking process(?: that leads to[^\n:]*)?:?(?:\*\*|\*)?|Let(?:'s| us) think step by step:?)(?:\r?\n)?/i;

  if (proseThinkHeaderRegex.test(text)) {
    const startMatch = text.match(proseThinkHeaderRegex);
    const startLen = startMatch ? startMatch[0].length : 0;
    const afterHeader = text.slice(startLen);

    // Comprehensive transition to final response:
    // - Explicit procedural markers: (Proceeds to generate output). / *Okay, ready to write...* / Let's write it.
    // - Header labels: Response:, Answer:, Final Answer:, Jawaban:, Output:, etc.
    // - Horizontal dividers: ---, ___, ***
    // - Natural prose openings: Berikut adalah, Tentu, Baik, Berdasarkan, Secara umum, Kesimpulannya, etc.
    // - Markdown headers: #, ##, ###
    const proseTransitionRegex = /(?:(?:\((?:Proceeds to )?(?:generate|write|draft) (?:output|response)\)\.?|\*+(?:Okay,?\s*)?(?:ready to write|let's write|let us draft|drafting) (?:the response|it)\.?\*+|Let's write it\.(?:[a-z]{0,4})?)(?:\s*)|(?:\r?\n|\n\n)(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer|Output|Hasil|Jawaban|Kesimpulan|Summary)(?:\*\*|\*|:|\s)*(?:\r?\n|$)|(?:\r?\n\r?\n)(?:---|___|\*\*\*)\s*(?:\r?\n|$)|(?:\r?\n\r?\n)(?=(?:Berikut (?:adalah|ini|merupakan)|Tentu,?\s+|Baik,?\s+|Berdasarkan |Secara umum,?\s+|Kesimpulannya,?\s+|Secara keseluruhan,?\s+|Untuk menjawab pertanyaan|Perbandingan |Di bawah ini|Jawaban singkatnya))|(?:\r?\n\r?\n)(?=#{1,4}\s+))/i;
    const transMatch = afterHeader.match(proseTransitionRegex);

    if (transMatch && transMatch.index !== undefined) {
      const thinking = afterHeader.slice(0, transMatch.index).trim();
      const rawResponse = afterHeader.slice(transMatch.index + transMatch[0].length).trim();
      return {
        thinking,
        response: cleanDirectivesAndArtifacts(rawResponse),
        isThinking: false
      };
    }

    // Secondary transition: structured markdown numbered items denoting response start (\n\n### 1. or \n\n**1. )
    const headingTransition = afterHeader.match(/(?:\r?\n\r?\n)(?=###?\s+\d+\.|\*\*1\.\s+)/i);
    if (headingTransition && headingTransition.index !== undefined) {
      const thinking = afterHeader.slice(0, headingTransition.index).trim();
      const rawResponse = afterHeader.slice(headingTransition.index).trim();
      return {
        thinking,
        response: cleanDirectivesAndArtifacts(rawResponse),
        isThinking: false
      };
    }

    // If started explicitly with "Here's a thinking process" and no transition marker has appeared yet,
    // it is actively streaming thinking tokens.
    if (/^(?:(?:\*\*|\*|>+\s*)?Here(?:'s| is) a thinking process)/i.test(text)) {
      return {
        thinking: afterHeader.trim(),
        response: '',
        isThinking: true
      };
    }
  }

  // Case 3: Embedded think block
  const embeddedMatch = text.match(/(?:(?:\n\n|\r?\n)(?:\*\*|\*|#+\s*)?(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning)(?:\*\*|\*|:|\s)*)([\s\S]*?)(?=(?:\n\n|\r?\n)(?:\*\*|\*|#+\s*)?(?:Response|Answer|Final Answer)(?:\*\*|\*|:|\s)*|$)/i);
  if (embeddedMatch && embeddedMatch.index !== undefined) {
    const thinking = embeddedMatch[1].trim();
    let rawResponse = (text.slice(0, embeddedMatch.index) + text.slice(embeddedMatch.index + embeddedMatch[0].length)).trim();
    return {
      thinking,
      response: cleanDirectivesAndArtifacts(rawResponse),
      isThinking: false
    };
  }

  // Default: no thinking detected
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
 * Sanitize a chat title to ensure no <think> or <thought> tags, prose thinking headers, markdown or quotes leak into UI.
 */
export function sanitizeChatTitle(rawTitle: string, fallback: string = 'New conversation'): string {
  if (!rawTitle) return fallback;

  // 1. If rawTitle contains structured reasoning or thinking headers, separate thinking from response first
  const { response: extractedResp } = extractThinkingAndResponse(rawTitle);
  let cleaned = extractedResp && extractedResp.trim().length > 0 ? extractedResp.trim() : rawTitle.trim();

  // 2. Strip XML think tags
  cleaned = cleaned.replace(/<(?:think|thought)>[\s\S]*?(?:<\/(?:think|thought)>|$)/gi, '').trim();

  // 3. Strip prose-based thinking headers and CoT introductions
  const proseThinkPrefixRegex = /^(?:(?:\*\*|\*|#+\s*)?(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning|Internal Thought|Plan)(?:\*\*|\*|:|\s)*|(?:\*\*|\*|>+\s*)?Here(?:'s| is) a thinking process(?: that leads to[^\n:]*)?:?(?:\*\*|\*)?|Let(?:'s| us) think step by step:?)(?:\r?\n)?/i;
  cleaned = cleaned.replace(proseThinkPrefixRegex, '').trim();

  // 4. Strip Title / Judul labels and surrounding quotes/markdown/colons
  cleaned = cleaned
    .replace(/^(?:Title|Judul|Topic|Subjek)\s*:\s*/i, '')
    .replace(/^["'«»“”\s*#`_\-:]+|["'«»“”\s*#`_\-:]+$/g, '')
    .trim();

  // 5. If unclosed tag or leftover think remains
  if (!cleaned || cleaned.toLowerCase().includes('<think') || cleaned.toLowerCase().includes('</think') || cleaned.toLowerCase().includes('<thought')) {
    return fallback;
  }

  // 6. Reject standalone thinking headers, CoT labels, or numbered thought steps
  if (
    /^(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning|Plan)\s*:?$/i.test(cleaned) ||
    /^\d+\.\s*(?:Analyze|Identif|Draft|Outlin|Step|Pikir|Analisa|Memikirkan)/i.test(cleaned)
  ) {
    return fallback;
  }

  const firstLine = cleaned.split('\n')[0].trim().replace(/^["'«»“”\s*#`_\-:]+|["'«»“”\s*#`_\-:]+$/g, '').trim();
  if (!firstLine || /^(?:Thinking Process|Thought Process|Thinking|Thought|Reasoning|Plan)\s*:?$/i.test(firstLine)) {
    return fallback;
  }

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

