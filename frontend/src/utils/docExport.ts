import type { SourceItem } from '../types';

/**
 * Convert Markdown text to clean HTML for document export.
 */
function markdownToHtml(md: string): string {
  let html = md;

  // Escape HTML entities to prevent malformed XML
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks: ```lang ... ```
  html = html.replace(/```(?:(\w+)\n)?([\s\S]*?)```/g, (_, _lang, code) => {
    return `<pre style="background:#f1f5f9;border:1pt solid #cbd5e1;padding:10pt;font-family:Consolas,monospace;font-size:9.5pt;border-radius:4pt;"><code>${code.trim()}</code></pre>`;
  });

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code style="background:#f1f5f9;padding:2pt 4pt;font-family:Consolas,monospace;font-size:9.5pt;color:#b91c1c;">$1</code>');

  // Headings
  html = html.replace(/^### (.*$)/gim, '<h3 style="font-size:13pt;color:#2563eb;margin-top:14pt;margin-bottom:4pt;">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 style="font-size:16pt;color:#1d4ed8;margin-top:18pt;margin-bottom:6pt;">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 style="font-size:20pt;color:#1e3a8a;border-bottom:2pt solid #2563eb;padding-bottom:6pt;margin-bottom:12pt;">$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^> (.*$)/gim, '<blockquote style="border-left:3pt solid #3b82f6;background:#eff6ff;padding:6pt 10pt;margin:8pt 0;color:#334155;font-style:italic;">$1</blockquote>');

  // Markdown links: [Title](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:#2563eb;text-decoration:underline;">$1</a>');

  // Unordered list items: - item or * item
  html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li style="margin-bottom:3pt;">$1</li>');
  html = html.replace(/(<li.*<\/li>)/gms, '<ul style="margin:6pt 0 10pt 20pt;padding:0;">$1</ul>');

  // Paragraphs (lines separated by double newlines)
  const paragraphs = html.split(/\n\s*\n/);
  const formattedParagraphs = paragraphs.map(p => {
    const trimmed = p.trim();
    if (!trimmed) return '';
    if (trimmed.startsWith('<h') || trimmed.startsWith('<pre') || trimmed.startsWith('<ul') || trimmed.startsWith('<blockquote')) {
      return trimmed;
    }
    return `<p style="margin:0 0 8pt 0;line-height:1.6;">${trimmed.replace(/\n/g, '<br/>')}</p>`;
  });

  return formattedParagraphs.join('\n');
}

/**
 * Export assistant response to Microsoft Word compatible Document (.doc) and trigger download.
 */
export function exportResponseToDoc({
  title,
  content,
  sources,
  timestamp
}: {
  title: string;
  content: string;
  sources?: SourceItem[];
  timestamp?: number;
}): void {
  const cleanTitle = title.trim() || 'LocaLLM Response';
  const docDate = timestamp ? new Date(timestamp).toLocaleString() : new Date().toLocaleString();
  const bodyHtml = markdownToHtml(content);

  let sourcesHtml = '';
  if (sources && sources.length > 0) {
    const listItems = sources
      .map(
        (s) => `
        <li style="margin-bottom:6pt;">
          <strong>${s.domain ? s.domain + ': ' : ''}</strong>
          <a href="${s.url}" style="color:#2563eb;text-decoration:underline;">${s.title || s.url}</a>
          ${s.snippet ? `<br/><span style="font-size:9pt;color:#64748b;">${s.snippet}</span>` : ''}
        </li>`
      )
      .join('');

    sourcesHtml = `
      <div style="margin-top:24pt;padding-top:14pt;border-top:1.5pt solid #cbd5e1;">
        <h3 style="font-size:14pt;color:#1e3a8a;margin-bottom:8pt;">Sources and Citations</h3>
        <ul style="margin:0 0 10pt 20pt;padding:0;">
          ${listItems}
        </ul>
      </div>
    `;
  }

  const fullDocument = `
<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
  <meta charset='utf-8'>
  <title>${cleanTitle}</title>
  <!--[if gte mso 9]>
  <xml>
    <w:WordDocument>
      <w:View>Print</w:View>
      <w:Zoom>100</w:Zoom>
      <w:DoNotOptimizeForBrowser/>
    </w:WordDocument>
  </xml>
  <![endif]-->
  <style>
    body {
      font-family: 'Segoe UI', Calibri, Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.6;
      color: #1e293b;
      margin: 1.2in 1in 1.2in 1in;
    }
  </style>
</head>
<body>
  <div style="background-color:#f8fafc;border:1pt solid #e2e8f0;padding:8pt 12pt;border-radius:4pt;margin-bottom:18pt;font-size:9.5pt;color:#64748b;">
    <strong style="color:#0f172a;">LocaLLM Assistant Response</strong> | Export Date: ${docDate}
  </div>

  ${bodyHtml}

  ${sourcesHtml}
</body>
</html>
  `.trim();

  // Create Word document blob with UTF-8 BOM
  const blob = new Blob(['\ufeff', fullDocument], {
    type: 'application/msword;charset=utf-8'
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeFilename = `${cleanTitle.replace(/[^a-zA-Z0-9_\-\s]/g, '').trim().replace(/\s+/g, '_').slice(0, 45) || 'LocaLLM_Document'}.doc`;
  a.download = safeFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
