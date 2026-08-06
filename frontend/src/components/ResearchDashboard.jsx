import { useState, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { FileCode2, Loader2, Copy, Check } from 'lucide-react';

/* ═══════════════════════════════════════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════════════════════════════════════ */

const API_URL = 'http://localhost:8000/api/research';

const AGENT_STEPS = [
  {
    key: 'researcher',
    label: 'Researcher',
    icon: '🔍',
    description: 'Searching & scraping sources',
    color: 'from-violet-500 to-purple-600',
    glowColor: 'shadow-[0_0_24px_rgba(139,92,246,0.45)]',
    ringColor: 'ring-violet-500',
  },
  {
    key: 'synthesizer',
    label: 'Synthesizer',
    icon: '✨',
    description: 'Analyzing & composing report',
    color: 'from-cyan-400 to-blue-500',
    glowColor: 'shadow-[0_0_24px_rgba(34,211,238,0.45)]',
    ringColor: 'ring-cyan-400',
  },
  {
    key: 'validator',
    label: 'Validator',
    icon: '✅',
    description: 'Checking quality & accuracy',
    color: 'from-emerald-400 to-green-500',
    glowColor: 'shadow-[0_0_24px_rgba(52,211,153,0.45)]',
    ringColor: 'ring-emerald-400',
  },
];

/* ═══════════════════════════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════════════════════════ */

/** Animated background orbs */
function BackgroundOrbs() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden>
      <div className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-accent/[0.06] rounded-full blur-[120px] animate-pulse-slow" />
      <div className="absolute top-1/3 -right-32 w-[400px] h-[400px] bg-cyan-500/[0.05] rounded-full blur-[100px] animate-pulse-slow delay-1000" />
      <div className="absolute -bottom-20 left-1/3 w-[350px] h-[350px] bg-emerald-500/[0.04] rounded-full blur-[100px] animate-pulse-slow delay-2000" />
    </div>
  );
}

/** Single step in the pipeline stepper */
function StepIndicator({ step, index, activeNode, completedNodes, total }) {
  const isActive = activeNode === step.key;
  const isCompleted = completedNodes.has(step.key);
  const isPending = !isActive && !isCompleted;

  return (
    <div className="flex items-center gap-3">
      {/* Node circle */}
      <div className="flex flex-col items-center gap-1.5">
        <div
          className={`
            relative w-14 h-14 rounded-2xl flex items-center justify-center text-2xl
            transition-all duration-500 ease-out
            ${isActive
              ? `bg-gradient-to-br ${step.color} ${step.glowColor} scale-110 ring-2 ${step.ringColor} ring-offset-2 ring-offset-surface-400`
              : isCompleted
                ? 'bg-white/10 ring-1 ring-white/20 scale-100'
                : 'bg-white/[0.04] ring-1 ring-white/[0.06] scale-95 opacity-40'
            }
          `}
        >
          {isActive && (
            <span className="absolute inset-0 rounded-2xl animate-ping bg-white/10" />
          )}
          <span className="relative z-10">{isCompleted ? '✓' : step.icon}</span>
        </div>

        {/* Label */}
        <span
          className={`
            text-xs font-semibold tracking-wide transition-colors duration-300
            ${isActive ? 'text-white' : isCompleted ? 'text-gray-400' : 'text-gray-600'}
          `}
        >
          {step.label}
        </span>
        {isActive && (
          <span className="text-[10px] text-gray-500 animate-fade-in">
            {step.description}
          </span>
        )}
      </div>

      {/* Connector line */}
      {index < total - 1 && (
        <div className="flex-1 min-w-[40px] h-[2px] mx-1">
          <div
            className={`
              h-full rounded-full transition-all duration-700
              ${isCompleted ? `bg-gradient-to-r ${step.color}` : 'bg-white/[0.06]'}
            `}
          />
        </div>
      )}
    </div>
  );
}

/** Full pipeline stepper */
function PipelineStepper({ activeNode, completedNodes }) {
  return (
    <div className="flex items-start justify-center gap-2 px-4">
      {AGENT_STEPS.map((step, i) => (
        <StepIndicator
          key={step.key}
          step={step}
          index={i}
          activeNode={activeNode}
          completedNodes={completedNodes}
          total={AGENT_STEPS.length}
        />
      ))}
    </div>
  );
}

/** Real-time event log sidebar */
function EventLog({ events }) {
  const endRef = useRef(null);

  // Auto-scroll to bottom on new events
  if (endRef.current) {
    endRef.current.scrollIntoView({ behavior: 'smooth' });
  }

  if (events.length === 0) return null;

  return (
    <div className="mt-8 animate-fade-in">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
        Live Event Log
      </h3>
      <div className="bg-surface-300/60 backdrop-blur-sm rounded-xl border border-white/[0.04] max-h-60 overflow-y-auto p-4 space-y-2">
        {events.map((evt, i) => (
          <div
            key={i}
            className="flex items-start gap-3 text-xs animate-slide-up"
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <span className="text-gray-600 font-mono w-8 shrink-0 text-right">
              {String(i + 1).padStart(2, '0')}
            </span>
            <span
              className={`
                font-semibold shrink-0 px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider
                ${evt.node === 'researcher' ? 'bg-violet-500/20 text-violet-300'
                  : evt.node === 'synthesizer' ? 'bg-cyan-500/20 text-cyan-300'
                  : evt.node === 'validator' ? 'bg-emerald-500/20 text-emerald-300'
                  : 'bg-amber-500/20 text-amber-300'
                }
              `}
            >
              {evt.node}
            </span>
            <span className="text-gray-400 truncate">{evt.summary}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}

/** Iteration badge shown during looping */
function IterationBadge({ count }) {
  if (count <= 0) return null;
  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-full text-xs text-amber-300 animate-fade-in">
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M4 4v5h5M20 20v-5h-5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M20.49 9A9 9 0 0 0 5.64 5.64L4 4m16 16l-1.64-1.64A9 9 0 0 1 3.51 15" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Iteration {count} / 3
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Main Dashboard
   ═══════════════════════════════════════════════════════════════════════════ */

export default function ResearchDashboard() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('idle'); // idle | streaming | done | error
  const [activeNode, setActiveNode] = useState(null);
  const [completedNodes, setCompletedNodes] = useState(new Set());
  const [events, setEvents] = useState([]);
  const [iterationCount, setIterationCount] = useState(0);
  const [report, setReport] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [exportingDocs, setExportingDocs] = useState(false);
  const [copied, setCopied] = useState(false);

  /* ── SSE stream handler ──────────────────────────────────────────────── */

  const startResearch = useCallback(async () => {
    if (!query.trim() || status === 'streaming') return;

    // Reset state
    setStatus('streaming');
    setActiveNode(null);
    setCompletedNodes(new Set());
    setEvents([]);
    setIterationCount(0);
    setReport('');
    setErrorMsg('');

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let previousNode = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data: ')) continue;

          try {
            const payload = JSON.parse(line.slice(6));
            const { node, data } = payload;

            // Mark previous node as completed
            if (previousNode && previousNode !== node) {
              setCompletedNodes((prev) => new Set([...prev, previousNode]));
            }

            if (node === 'complete') {
              setCompletedNodes(
                (prev) => new Set([...prev, 'researcher', 'synthesizer', 'validator'])
              );
              setActiveNode(null);
              setReport(data.draft_summary || '');
              setStatus('done');
            } else {
              setActiveNode(node);

              // Track iterations
              if (data.iteration_count != null) {
                setIterationCount(data.iteration_count);
              }

              // Build summary for the event log
              let summary = '';
              if (node === 'researcher') {
                const terms = data.search_queries?.join(', ') || '';
                const pages = data.context_pages_added || 0;
                summary = `Generated queries: [${terms}] — scraped ${pages} pages`;
              } else if (node === 'synthesizer') {
                summary = 'Report draft composed';
              } else if (node === 'validator') {
                summary = data.revision_notes
                  ? `Needs revision: ${data.revision_notes.slice(0, 80)}…`
                  : 'Draft approved ✓';
              }

              setEvents((prev) => [...prev, { node, summary }]);
            }

            previousNode = node;
          } catch {
            // Ignore malformed SSE lines
          }
        }
      }
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.message || 'Connection failed');
    }
  }, [query, status]);

  /* ── Export to Google Docs handler ───────────────────────────────────────── */

  const handleExportDocs = useCallback(async () => {
    if (exportingDocs || !report) return;
    setExportingDocs(true);
    try {
      const res = await fetch('http://localhost:8000/api/export/docs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: report, title: query || 'Research Report' }),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Export failed (${res.status})`);
      }
      const data = await res.json();
      window.open(data.url, '_blank');
    } catch (err) {
      console.error('Google Docs export error:', err);
      alert(`Failed to export to Google Docs: ${err.message}`);
    } finally {
      setExportingDocs(false);
    }
  }, [exportingDocs, report, query]);

  /* ── Copy to clipboard handler ─────────────────────────────────────────── */

  const handleCopy = useCallback(async () => {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, [report]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      startResearch();
    }
  };

  const isStreaming = status === 'streaming';
  const isDone = status === 'done';
  const isError = status === 'error';

  /* ── Render ──────────────────────────────────────────────────────────── */

  return (
    <div className="relative min-h-screen flex flex-col">
      <BackgroundOrbs />

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="relative z-10 pt-12 pb-6 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 bg-accent/10 border border-accent/20 rounded-full text-xs text-accent-light font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          Multi-Agent Pipeline
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
          Research Assistant
        </h1>
        <p className="mt-3 text-gray-500 text-sm max-w-md mx-auto">
          AI-powered deep research with real-time streaming.
          Ask anything and watch three agents collaborate live.
        </p>
      </header>

      {/* ── Search bar ──────────────────────────────────────────────────── */}
      <div className="relative z-10 w-full max-w-2xl mx-auto px-4 mb-8">
        <div
          className={`
            relative flex items-center gap-3 bg-surface-200/80 backdrop-blur-xl
            rounded-2xl border transition-all duration-300
            ${isStreaming
              ? 'border-accent/40 shadow-glow'
              : 'border-white/[0.06] hover:border-white/[0.12] focus-within:border-accent/40 focus-within:shadow-glow'
            }
          `}
        >
          {/* Search icon */}
          <div className="pl-5 text-gray-500">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <input
            id="search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="What would you like to research?"
            disabled={isStreaming}
            className="flex-1 bg-transparent py-4 text-white placeholder:text-gray-600
                       outline-none text-base disabled:opacity-50"
          />

          <button
            id="search-button"
            onClick={startResearch}
            disabled={isStreaming || !query.trim()}
            className={`
              mr-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300
              disabled:opacity-30 disabled:cursor-not-allowed
              ${isStreaming
                ? 'bg-accent/30 text-accent-light cursor-wait'
                : 'bg-gradient-to-r from-accent to-accent-muted text-white hover:shadow-glow hover:scale-[1.03] active:scale-[0.98]'
              }
            `}
          >
            {isStreaming ? (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                Working…
              </span>
            ) : (
              'Research'
            )}
          </button>
        </div>

        {/* Shimmer bar while streaming */}
        {isStreaming && (
          <div className="mt-2 h-0.5 w-full rounded-full overflow-hidden">
            <div className="shimmer-bar h-full w-full rounded-full" />
          </div>
        )}
      </div>

      {/* ── Pipeline stepper ────────────────────────────────────────────── */}
      {(isStreaming || isDone) && (
        <div className="relative z-10 w-full max-w-2xl mx-auto px-4 mb-6 animate-fade-in">
          <div className="bg-surface-200/60 backdrop-blur-sm rounded-2xl border border-white/[0.04] p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
                Agent Pipeline
              </h2>
              <IterationBadge count={iterationCount} />
            </div>
            <PipelineStepper activeNode={activeNode} completedNodes={completedNodes} />
          </div>

          {/* Event log */}
          <EventLog events={events} />
        </div>
      )}

      {/* ── Error state ─────────────────────────────────────────────────── */}
      {isError && (
        <div className="relative z-10 w-full max-w-2xl mx-auto px-4 mb-6 animate-slide-up">
          <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-5 flex items-start gap-4">
            <span className="text-2xl">⚠️</span>
            <div>
              <h3 className="text-red-300 font-semibold text-sm">Something went wrong</h3>
              <p className="text-red-400/80 text-xs mt-1">{errorMsg}</p>
              <button
                onClick={() => { setStatus('idle'); setErrorMsg(''); }}
                className="mt-3 text-xs text-red-300 underline underline-offset-2 hover:text-red-200 transition-colors"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Final report ────────────────────────────────────────────────── */}
      {isDone && report && (
        <div className="relative z-10 w-full max-w-4xl mx-auto px-4 pb-20 animate-slide-up">
          <div className="bg-surface-200/70 backdrop-blur-sm rounded-2xl border border-white/[0.06] overflow-hidden">
            {/* Report header */}
            <div className="px-8 pt-8 pb-4 border-b border-white/[0.04] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-muted flex items-center justify-center text-lg shadow-glow">
                  📄
                </div>
                <div>
                  <h2 className="text-white font-bold text-lg">Research Report</h2>
                  <p className="text-gray-500 text-xs mt-0.5">
                    Completed in {iterationCount} iteration{iterationCount !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2">
                <button
                  id="export-docs-button"
                  onClick={handleExportDocs}
                  disabled={exportingDocs}
                  className="px-4 py-2 text-xs font-medium text-gray-400 bg-white/[0.04]
                             hover:bg-white/[0.08] rounded-lg border border-white/[0.06]
                             transition-all hover:text-white disabled:opacity-50 disabled:cursor-not-allowed
                             flex items-center gap-2"
                >
                  {exportingDocs ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FileCode2 className="w-3.5 h-3.5" />
                  )}
                  {exportingDocs ? 'Exporting…' : 'Export to Google Docs'}
                </button>

                <button
                  id="copy-report-button"
                  onClick={handleCopy}
                  className="px-4 py-2 text-xs font-medium bg-slate-800 hover:bg-slate-700
                             text-slate-300 rounded-lg border border-white/[0.06]
                             transition-all hover:text-white flex items-center gap-2"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            {/* Rendered markdown */}
            <div className="px-8 py-8 markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {report}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* ── Idle state — feature cards ──────────────────────────────────── */}
      {status === 'idle' && (
        <div className="relative z-10 w-full max-w-3xl mx-auto px-4 mt-4 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {AGENT_STEPS.map((step) => (
              <div
                key={step.key}
                className="group bg-surface-200/40 backdrop-blur-sm rounded-2xl border border-white/[0.04]
                           p-5 hover:border-white/[0.08] transition-all duration-300 hover:-translate-y-1"
              >
                <div
                  className={`
                    w-11 h-11 rounded-xl bg-gradient-to-br ${step.color}
                    flex items-center justify-center text-xl mb-3
                    group-hover:scale-110 transition-transform duration-300
                  `}
                >
                  {step.icon}
                </div>
                <h3 className="text-white font-semibold text-sm">{step.label}</h3>
                <p className="text-gray-500 text-xs mt-1.5 leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
