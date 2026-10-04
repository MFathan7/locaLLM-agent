import { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, ExternalLink, X, Maximize2 } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

  return (
    <>
      <div className="markdown-content text-[15px]/[1.7] md:text-[16px]/[1.75] text-slate-800 dark:text-slate-100 space-y-3">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            h1: ({ children }) => <h1 className="text-xl md:text-2xl font-bold mt-4 mb-2 text-slate-900 dark:text-white">{children}</h1>,
            h2: ({ children }) => <h2 className="text-lg md:text-xl font-bold mt-3 mb-2 text-slate-900 dark:text-white">{children}</h2>,
            h3: ({ children }) => <h3 className="text-base md:text-lg font-semibold mt-2.5 mb-1.5 text-slate-900 dark:text-white">{children}</h3>,
            ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
            li: ({ children }) => <li className="pl-1">{children}</li>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-3 border-blue-500/70 pl-3.5 my-2.5 italic text-slate-600 dark:text-slate-300 bg-blue-500/5 py-1 rounded-r-lg">
                {children}
              </blockquote>
            ),
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              const isInline = !match && !String(children).includes('\n');
              const codeString = String(children).replace(/\n$/, '');

              if (isInline) {
                return (
                  <code
                    className="px-1.5 py-0.5 rounded-md font-mono text-[13px] bg-black/[0.06] dark:bg-white/[0.08] text-pink-600 dark:text-pink-400 border border-black/[0.04] dark:border-white/[0.06]"
                    {...props}
                  >
                    {children}
                  </code>
                );
              }

              return <CodeBlock language={match ? match[1] : ''} code={codeString} />;
            },
            table: ({ children }) => <TableBlock>{children}</TableBlock>,
            thead: ({ children }) => (
              <thead className="border-b border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02]">
                {children}
              </thead>
            ),
            tbody: ({ children }) => (
              <tbody className="divide-y divide-black/10 dark:divide-white/10">
                {children}
              </tbody>
            ),
            tr: ({ children }) => (
              <tr className="transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.02]">
                {children}
              </tr>
            ),
            th: ({ children }) => (
              <th className="px-4 py-2.5 text-center font-bold text-slate-900 dark:text-white">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300">
                {children}
              </td>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noreferrer noopener"
                className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 font-medium"
              >
                <span>{children}</span>
                <ExternalLink className="w-3 h-3 inline-block shrink-0 opacity-70" />
              </a>
            ),
            img: ({ src, alt }) => {
              if (!src) return null;
              return (
                <div className="my-3 group relative inline-block max-w-full">
                  <div
                    onClick={() => setLightboxImage(src)}
                    className="relative overflow-hidden rounded-2xl border border-black/10 dark:border-white/10 shadow-md cursor-pointer group-hover:shadow-lg transition-all"
                  >
                    <img
                      src={src}
                      alt={alt || 'Image'}
                      className="max-h-[380px] w-auto max-w-full object-cover transition-transform group-hover:scale-[1.01]"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <span className="p-2 rounded-full bg-black/60 text-white backdrop-blur-xs">
                        <Maximize2 className="w-4 h-4" />
                      </span>
                    </div>
                  </div>
                  {alt && <p className="text-[11px] text-slate-400 mt-1 italic">{alt}</p>}
                </div>
              );
            }
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {/* Lightbox Modal */}
      {lightboxImage && (
        <div
          onClick={() => setLightboxImage(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md cursor-zoom-out"
        >
          <div className="relative max-w-4xl max-h-[90vh]">
            <button
              onClick={() => setLightboxImage(null)}
              className="absolute -top-10 right-0 p-1.5 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
              aria-label="Close image preview"
            >
              <X className="w-5 h-5" />
            </button>
            <img
              src={lightboxImage}
              alt="Preview"
              className="max-w-full max-h-[85vh] object-contain rounded-xl shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </>
  );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 rounded-2xl overflow-hidden border border-black/10 dark:border-white/10 bg-slate-900 dark:bg-black/40 text-slate-100 shadow-md">
      {/* Code Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.08] bg-black/20 text-xs text-slate-400">
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <pre className="p-4 overflow-x-auto text-[13px]/relaxed font-mono selection:bg-blue-600/40">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function TableBlock({ children }: { children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const tableRef = useRef<HTMLTableElement>(null);

  const handleCopyTable = () => {
    if (!tableRef.current) return;
    const rows = Array.from(tableRef.current.querySelectorAll('tr'));
    if (rows.length === 0) return;

    const tableData = rows.map(row => {
      const cells = Array.from(row.querySelectorAll('th, td'));
      return cells.map(cell => (cell.textContent || '').trim().replace(/\s+/g, ' '));
    });

    const headers = tableData[0] || [];
    const bodyRows = tableData.slice(1);

    const headerLine = `| ${headers.join(' | ')} |`;
    const separatorLine = `| ${headers.map(() => '---').join(' | ')} |`;
    const bodyLines = bodyRows.map(row => `| ${row.join(' | ')} |`).join('\n');
    const markdownTable = bodyLines ? `${headerLine}\n${separatorLine}\n${bodyLines}` : headerLine;

    // Clipboard write with HTML & plain text fallback
    if (navigator.clipboard && window.ClipboardItem) {
      try {
        const html = tableRef.current.outerHTML;
        const item = new ClipboardItem({
          'text/plain': new Blob([markdownTable], { type: 'text/plain' }),
          'text/html': new Blob([html], { type: 'text/html' })
        });
        navigator.clipboard.write([item]).catch(() => {
          navigator.clipboard.writeText(markdownTable);
        });
      } catch {
        navigator.clipboard.writeText(markdownTable);
      }
    } else {
      navigator.clipboard.writeText(markdownTable);
    }

    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="group relative my-3 flex items-start gap-1.5">
      {/* Table Content */}
      <div className="flex-1 overflow-x-auto min-w-0">
        <table ref={tableRef} className="min-w-full text-xs sm:text-sm border-collapse">
          {children}
        </table>
      </div>

      {/* Copy icon button placed to the right side of the table, matching standard icon button design */}
      <div className="shrink-0 pt-1 opacity-0 group-hover:opacity-100 transition-opacity relative inline-flex items-center">
        <button
          type="button"
          onClick={handleCopyTable}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          onFocus={() => setShowTooltip(true)}
          onBlur={() => setShowTooltip(false)}
          aria-label="Copy table"
          className="relative p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.05] dark:hover:bg-white/[0.08] transition-all cursor-pointer"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-emerald-500" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>

        {/* Hover Tooltip matching standard app tooltips */}
        {showTooltip && (
          <div className="absolute bottom-full right-0 mb-2 px-2.5 py-1 bg-slate-900 dark:bg-zinc-800 text-white text-[11px] font-medium rounded-lg shadow-xl shadow-black/25 pointer-events-none whitespace-nowrap z-30 border border-white/10">
            {copied ? 'Copied to clipboard' : 'Copy table'}
            <div className="absolute top-full right-2.5 -mt-1 border-4 border-transparent border-t-slate-900 dark:border-t-zinc-800" />
          </div>
        )}
      </div>
    </div>
  );
}
