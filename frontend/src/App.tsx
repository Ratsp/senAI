import { useEffect, useState, useRef } from "react";
import {
  Inbox,
  AlertTriangle,
  CheckCircle,
  FileText,
  Search,
  User,
  Shield,
  TrendingDown,
  Activity,
  Send,
  Edit2,
  AlertCircle,
  Globe,
  Database,
  RefreshCw,
  Clock,
  Sparkles,
  PieChart as ChartIcon
} from "lucide-react";

interface Action {
  id: string;
  action_type: string;
  proposed_content: string | null;
  is_approved: boolean;
  approved_by: string | null;
  executed_at: string | null;
  agent_reasoning_log: any;
}

interface Email {
  id: string;
  message_id: string;
  sender: string;
  subject: string | null;
  body: string | null;
  timestamp: string;
  sentiment_score: number | null;
  category: string | null;
  urgency: string | null;
  requires_human: boolean;
  confidence: number | null;
  raw_entities: any;
  status: string;
  actions: Action[];
}

interface Thread {
  id: string;
  thread_id: string;
  subject: string | null;
  sender_email: string;
  first_seen_at: string | null;
  last_updated_at: string | null;
  status: string;
  assigned_to: string | null;
  emails: Email[];
}

interface Contact {
  id: string;
  email: string;
  name: string | null;
  company: string | null;
  status: string;
  account_value: number | null;
  churn_risk_score: number;
  created_at: string | null;
  last_contact_at: string | null;
}

export default function App() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [activeTab, setActiveTab] = useState<"inbox" | "analytics" | "rag">("inbox");
  const [inboxFilter, setInboxFilter] = useState<"all" | "human" | "replied" | "escalated" | "spam">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [stats, setStats] = useState({
    pending: 0,
    replied: 0,
    escalated: 0,
    critical: 0,
    spam_filtered: 0,
    total: 0
  });

  // Contact details for selected thread
  const [contactProfile, setContactProfile] = useState<{
    contact: Contact;
    open_thread_count: number;
    recent_emails: any[];
    churn_risk_score: number;
  } | null>(null);

  // RAG and Scraper states
  const [ragQuery, setRagQuery] = useState("");
  const [ragResults, setRagResults] = useState<any[]>([]);
  const [reputationData, setReputationData] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Editing draft state
  const [editingActionId, setEditingActionId] = useState<string | null>(null);
  const [editedReplyText, setEditedReplyText] = useState("");
  
  // WebSocket notification alert
  const [latestAlert, setLatestAlert] = useState<{ email: string; message: string } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // Load baseline statistics and threads
  const loadData = async () => {
    try {
      setIsRefreshing(true);
      const [threadsRes, statsRes, reputationRes] = await Promise.all([
        fetch("http://127.0.0.1:8000/threads"),
        fetch("http://127.0.0.1:8000/dashboard/stats"),
        fetch("http://127.0.0.1:8000/intelligence/reputation")
      ]);

      if (threadsRes.ok) {
        const data = await threadsRes.json();
        setThreads(data);
        if (data.length > 0 && !selectedThreadId) {
          setSelectedThreadId(data[0].id);
        }
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
      if (reputationRes.ok) {
        setReputationData(await reputationRes.json());
      }
    } catch (e) {
      console.error("Error loading API data", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Connect WebSocket
  useEffect(() => {
    loadData();

    const connectWebSocket = () => {
      const ws = new WebSocket("ws://127.0.0.1:8000/ws");
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("WebSocket event:", data);

        // Auto reload stats and threads list on incoming events
        loadData();

        if (data.type === "alert" && data.alert_type === "sentiment_deterioration") {
          setLatestAlert({
            email: data.email,
            message: data.message
          });
          // Clear notification after 6 seconds
          setTimeout(() => {
            setLatestAlert(null);
          }, 6000);
        }
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected, reconnecting in 5s...");
        setTimeout(connectWebSocket, 5000);
      };
    };

    connectWebSocket();

    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Update selected thread when thread ID or threads list updates
  useEffect(() => {
    if (selectedThreadId) {
      const found = threads.find((t) => t.id === selectedThreadId);
      setSelectedThread(found || null);
    } else {
      setSelectedThread(null);
    }
  }, [selectedThreadId, threads]);

  // Load Contact Profile when selected thread sender email updates
  useEffect(() => {
    if (selectedThread?.sender_email) {
      fetch(`http://127.0.0.1:8000/contacts/${selectedThread.sender_email}`)
        .then((res) => {
          if (res.ok) return res.json();
          return null;
        })
        .then((data) => {
          setContactProfile(data);
        })
        .catch((e) => console.error("Error loading contact profile", e));
    } else {
      setContactProfile(null);
    }
  }, [selectedThread]);

  // RAG Search Manual Debugging
  const handleRagSearch = async () => {
    if (!ragQuery.trim()) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/rag/search?q=${encodeURIComponent(ragQuery)}`);
      if (res.ok) {
        const data = await res.json();
        setRagResults(data.results || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Triage operations: Manual Respond / Escalate
  const handleRespond = async (emailId: string, replyText: string, escalate: boolean) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/respond/${emailId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reply_text: replyText, escalate })
      });
      if (response.ok) {
        loadData();
        setEditingActionId(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Edit Auto-reply draft
  const handleUpdateDraft = async (actionId: string, proposedContent: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/drafts/${actionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proposed_content: proposedContent })
      });
      if (response.ok) {
        loadData();
        setEditingActionId(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Approve Auto-reply draft
  const handleApproveDraft = async (actionId: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/drafts/${actionId}/approve`, {
        method: "POST"
      });
      if (response.ok) {
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Category Breakdown distribution helper
  const getCategoryDistribution = () => {
    // Collect from threads / emails
    const counts: { [key: string]: number } = {};
    threads.forEach((t) => {
      t.emails.forEach((e) => {
        const cat = e.category || "Unclassified";
        counts[cat] = (counts[cat] || 0) + 1;
      });
    });
    return counts;
  };

  // Filtered Thread list according to Tabs & Search Box
  const filteredThreads = threads.filter((t) => {
    // Filter matching searchQuery
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      (t.subject?.toLowerCase() || "").includes(query) ||
      (t.sender_email.toLowerCase() || "").includes(query) ||
      t.emails.some(
        (e) =>
          (e.body?.toLowerCase() || "").includes(query) ||
          (e.subject?.toLowerCase() || "").includes(query)
      );

    if (!matchesSearch) return false;

    // Filter matching tabs
    if (inboxFilter === "all") return true;
    if (inboxFilter === "human") {
      return t.emails.some((e) => e.requires_human || e.status === "Escalated");
    }
    if (inboxFilter === "replied") {
      return t.emails.some((e) => e.status === "Replied");
    }
    if (inboxFilter === "escalated") {
      return t.emails.some((e) => e.status === "Escalated");
    }
    if (inboxFilter === "spam") {
      return t.emails.some((e) => e.category === "Spam");
    }
    return true;
  });



  const getSentimentBg = (score: number | null) => {
    if (score === null) return "bg-gray-500/10 border-gray-500/20";
    if (score > 0.3) return "bg-emerald-500/10 border-emerald-500/20";
    if (score < -0.3) return "bg-rose-500/10 border-rose-500/20";
    return "bg-amber-500/10 border-amber-500/20";
  };

  // Highlighter for entity metadata (money, tickets, product keywords)
  const highlightEntities = (text: string | null) => {
    if (!text) return "";
    // Regex for typical entities
    // 1. Order / Ticket IDs: e.g. msg_001, thread_001, P0, RCA, SLA
    // 2. Monetary amounts: e.g. $1000, 2 BTC, $150000
    // 3. Deadlines / Policies references: e.g. sla_policy.md, refund_policy.md
    const pattern = /(\$[0-9,]+(\.[0-9]+)?|\b[0-9]+\s*BTC\b|\bmsg_[0-9a-zA-Z_]+\b|\bthread_[0-9a-zA-Z_]+\b|\b[a-z_]+\.md\b|\bP0\b|\bSLA\b|\bRCA\b)/gi;
    
    const parts = text.split(pattern);
    return parts.map((part, i) => {
      if (pattern.test(part)) {
        return (
          <span key={i} className="underline decoration-cyan-400/80 decoration-2 font-medium text-cyan-300">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className="min-h-screen bg-[#070b13] bg-radial-gradient text-slate-100 flex flex-col font-sans">
      
      {/* Sentiment deterioration Toast Notification Alert */}
      {latestAlert && (
        <div className="fixed top-6 right-6 z-50 max-w-md bg-slate-900/90 border border-rose-500/50 backdrop-blur-xl rounded-xl p-4 shadow-2xl flex items-start gap-3 animate-bounce">
          <AlertTriangle className="h-6 w-6 text-rose-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-rose-400">Reputation Deterioration Alert</h4>
            <p className="text-xs text-slate-300 mt-1">{latestAlert.message}</p>
            <span className="text-[10px] text-slate-400 font-mono mt-1 block">{latestAlert.email}</span>
          </div>
        </div>
      )}

      {/* Main Header navigation */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-violet-500/20">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-violet-400 via-indigo-200 to-cyan-300 bg-clip-text text-transparent">
              SenAI Intelligence
            </h1>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">
              Agentic CRM Operations Portal
            </p>
          </div>
        </div>

        {/* Tab system navigation */}
        <nav className="flex items-center gap-1.5 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab("inbox")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "inbox"
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            <Inbox className="h-4 w-4" />
            Triage Inbox
          </button>
          <button
            onClick={() => setActiveTab("analytics")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "analytics"
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            <ChartIcon className="h-4 w-4" />
            Analytics Dashboard
          </button>
          <button
            onClick={() => setActiveTab("rag")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === "rag"
                ? "bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            <Database className="h-4 w-4" />
            RAG Debugger
          </button>
        </nav>

        {/* Action controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={isRefreshing}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 rounded-lg border border-slate-800 transition-all disabled:opacity-40"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-[11px] font-semibold text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></span>
            System Live
          </div>
        </div>
      </header>

      {/* Main content body grid depending on tab */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {activeTab === "inbox" && (
          <div className="flex-1 flex overflow-hidden">
            
            {/* View 1: Left Pane — Mission Control Inbox Thread List */}
            <div className="w-[380px] border-r border-slate-800 bg-slate-950/20 flex flex-col flex-shrink-0">
              
              {/* Search and sorting header */}
              <div className="p-4 border-b border-slate-800 space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search sender, thread, or body..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/50 transition-colors"
                  />
                </div>

                {/* Sub-tabs categorization filter */}
                <div className="flex flex-wrap gap-1 p-0.5 bg-slate-950/80 border border-slate-800/80 rounded-lg">
                  {(["all", "human", "replied", "escalated", "spam"] as const).map((filter) => (
                    <button
                      key={filter}
                      onClick={() => setInboxFilter(filter)}
                      className={`px-2 py-1.5 rounded-md text-[10px] font-bold tracking-wider capitalize transition-all ${
                        inboxFilter === filter
                          ? "bg-slate-800 text-white shadow-inner"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {filter === "human" ? "Needs Human" : filter === "spam" ? "Spam" : filter}
                    </button>
                  ))}
                </div>
              </div>

              {/* Collapsed Thread rows list */}
              <div className="flex-1 overflow-y-auto divide-y divide-slate-900/60">
                {filteredThreads.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No matching threads found.
                  </div>
                ) : (
                  filteredThreads.map((t) => {
                    const lastEmail = t.emails[t.emails.length - 1];
                    const isSelected = t.id === selectedThreadId;
                    const criticalBadge = t.emails.some((e) => e.urgency === "Critical");
                    
                    return (
                      <div
                        key={t.id}
                        onClick={() => setSelectedThreadId(t.id)}
                        className={`p-4 cursor-pointer transition-all ${
                          isSelected
                            ? "bg-slate-850 border-l-4 border-violet-500"
                            : "hover:bg-slate-900/40"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-slate-400 font-medium truncate max-w-[200px]">
                            {t.sender_email}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {lastEmail ? new Date(lastEmail.timestamp).toLocaleDateString() : ""}
                          </span>
                        </div>
                        <h4 className="text-xs font-semibold text-slate-200 mt-1 truncate">
                          {t.subject || "No Subject"}
                        </h4>
                        <p className="text-[11px] text-slate-400 mt-1 truncate">
                          {lastEmail?.body || ""}
                        </p>

                        {/* Visual pills for metadata */}
                        <div className="flex items-center gap-1.5 mt-2.5">
                          {lastEmail?.sentiment_score !== undefined && (
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${getSentimentBg(lastEmail.sentiment_score)}`}>
                              Sentiment: {lastEmail.sentiment_score?.toFixed(1)}
                            </span>
                          )}
                          {lastEmail?.category && (
                            <span className="bg-slate-800 text-slate-300 border border-slate-700 text-[9px] font-bold px-1.5 py-0.5 rounded">
                              {lastEmail.category}
                            </span>
                          )}
                          {criticalBadge && (
                            <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[9px] font-extrabold px-1.5 py-0.5 rounded animate-pulse">
                              CRITICAL
                            </span>
                          )}
                          {lastEmail?.requires_human && (
                            <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[9px] font-bold px-1.5 py-0.5 rounded">
                              Human Queue
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* View 2: Center & Right Panes — Thread Workspace detail view */}
            <div className="flex-1 flex overflow-hidden">
              {selectedThread ? (
                <div className="flex-1 flex overflow-hidden">
                  
                  {/* Center Timeline Pane */}
                  <div className="flex-1 flex flex-col bg-slate-900/20 border-r border-slate-800">
                    <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-100 truncate max-w-lg">
                          {selectedThread.subject || "No Subject"}
                        </h3>
                        <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                          Thread ID: {selectedThread.thread_id}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] bg-slate-950/60 border border-slate-800 text-slate-300 font-semibold px-2.5 py-1 rounded-md">
                          Status: {selectedThread.status}
                        </span>
                      </div>
                    </div>

                    {/* Timeline message thread */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                      {selectedThread.emails.map((email) => {
                        const score = email.sentiment_score;
                        const action = email.actions && email.actions[0];
                        const reasoning = action?.agent_reasoning_log;

                        return (
                          <div key={email.id} className="bg-slate-950/40 border border-slate-800 rounded-xl p-4 shadow-sm space-y-4">
                            <div className="flex items-start justify-between border-b border-slate-900 pb-2.5">
                              <div>
                                <span className="text-xs font-semibold text-violet-400">
                                  {email.sender}
                                </span>
                                <span className="text-[10px] text-slate-500 font-mono block mt-0.5">
                                  {new Date(email.timestamp).toUTCString()}
                                </span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getSentimentBg(score)}`}>
                                  Sentiment: {score !== null ? score.toFixed(2) : "N/A"}
                                </span>
                                {email.urgency && (
                                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                                    email.urgency === "Critical"
                                      ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                                      : "bg-slate-800 border-slate-700 text-slate-300"
                                  }`}>
                                    {email.urgency}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Body text with highlighted entities */}
                            <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                              {highlightEntities(email.body)}
                            </p>

                            {/* Agent Reasoning Panel (Collapsible Thought-Action trace) */}
                            {reasoning && (
                              <div className="border border-slate-800/80 rounded-xl bg-slate-950/60 overflow-hidden">
                                <div className="bg-slate-900/80 px-4 py-2 border-b border-slate-800 flex items-center justify-between">
                                  <div className="flex items-center gap-2 text-xs font-bold text-slate-300">
                                    <Shield className="h-4 w-4 text-violet-400" />
                                    Agent Triage Panel
                                  </div>
                                  {email.confidence && (
                                    <div className="text-[10px] font-mono text-slate-400">
                                      Confidence: {(email.confidence * 100).toFixed(0)}%
                                    </div>
                                  )}
                                </div>
                                <div className="p-4 text-[11px] font-mono space-y-3">
                                  {reasoning.steps ? (
                                    reasoning.steps.map((step: any, stepIdx: number) => (
                                      <div key={stepIdx} className="space-y-1.5 border-l-2 border-slate-800 pl-3 pb-2">
                                        <div className="text-slate-300 font-semibold flex items-center gap-1">
                                          <Clock className="h-3.5 w-3.5 text-slate-500" />
                                          Step {stepIdx + 1}: Thought
                                        </div>
                                        <div className="text-slate-400 italic font-sans leading-normal">
                                          {step.thought}
                                        </div>
                                        {step.action !== "DONE" && (
                                          <div className="mt-1 flex flex-wrap gap-2 text-[10px] bg-slate-900 border border-slate-800 rounded px-2 py-1 font-mono">
                                            <span className="text-violet-400">Action:</span>
                                            <span className="text-slate-300 font-semibold">{step.action}</span>
                                            {step.action_input && (
                                              <>
                                                <span className="text-slate-500">Params:</span>
                                                <span className="text-cyan-400 truncate max-w-xs">{JSON.stringify(step.action_input)}</span>
                                              </>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <div className="space-y-2">
                                      <div className="text-slate-400 italic">Classification Details:</div>
                                      <div className="grid grid-cols-2 gap-2 text-[10px] bg-slate-900 rounded p-2">
                                        <div><span className="text-slate-500">Category:</span> <span className="text-slate-300 font-semibold">{reasoning.category}</span></div>
                                        <div><span className="text-slate-500">Urgency:</span> <span className="text-slate-300 font-semibold">{reasoning.urgency}</span></div>
                                        <div><span className="text-slate-500">Requires Human:</span> <span className="text-slate-300 font-semibold">{reasoning.requires_human ? "Yes" : "No"}</span></div>
                                        <div><span className="text-slate-500">RAG chunks:</span> <span className="text-slate-300 font-semibold">{reasoning.rag_sources?.join(", ") || "None"}</span></div>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Draft content display area */}
                            {action && action.action_type === "Auto-Reply" && !action.is_approved && (
                              <div className="bg-slate-950/90 border border-violet-500/20 rounded-xl p-4 space-y-3 shadow-md">
                                <div className="flex items-center justify-between">
                                  <div className="text-xs font-bold text-violet-300 flex items-center gap-1.5">
                                    <Edit2 className="h-3.5 w-3.5" />
                                    Proposed Auto-Reply Draft
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <button
                                      onClick={() => {
                                        setEditingActionId(action.id);
                                        setEditedReplyText(action.proposed_content || "");
                                      }}
                                      className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 border border-slate-700 hover:bg-slate-700 text-[10px] font-bold rounded transition-colors text-slate-200"
                                    >
                                      Edit
                                    </button>
                                    <button
                                      onClick={() => handleApproveDraft(action.id)}
                                      className="flex items-center gap-1 px-2.5 py-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-[10px] font-bold rounded transition-colors text-white shadow-md shadow-violet-600/10"
                                    >
                                      Approve & Send
                                    </button>
                                  </div>
                                </div>
                                {editingActionId === action.id ? (
                                  <div className="space-y-2">
                                    <textarea
                                      value={editedReplyText}
                                      onChange={(e) => setEditedReplyText(e.target.value)}
                                      className="w-full h-28 bg-slate-900 border border-slate-850 rounded-lg p-2.5 text-xs font-sans text-slate-100 focus:outline-none focus:border-violet-500"
                                    />
                                    <div className="flex justify-end gap-2">
                                      <button
                                        onClick={() => setEditingActionId(null)}
                                        className="px-2.5 py-1 text-[10px] font-bold hover:text-slate-200 text-slate-400"
                                      >
                                        Cancel
                                      </button>
                                      <button
                                        onClick={() => handleUpdateDraft(action.id, editedReplyText)}
                                        className="px-2.5 py-1 text-[10px] font-bold bg-violet-600 hover:bg-violet-500 text-white rounded"
                                      >
                                        Save Changes
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <p className="text-xs text-slate-300 italic border-l-2 border-violet-500/40 pl-3 whitespace-pre-wrap leading-relaxed bg-slate-900/30 p-2.5 rounded-lg">
                                    "{action.proposed_content}"
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Executed responses audit tag */}
                            {action && action.is_approved && (
                              <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-[11px] text-emerald-400">
                                <CheckCircle className="h-4 w-4" />
                                <div>
                                  <span className="font-semibold capitalize">{action.action_type} executed</span> by <span className="font-mono">{action.approved_by || "agent"}</span> at {action.executed_at ? new Date(action.executed_at).toLocaleString() : ""}
                                  {action.proposed_content && (
                                    <p className="text-[10px] text-slate-300 mt-1 italic font-sans whitespace-pre-wrap border-l border-emerald-500/30 pl-2">
                                      "{action.proposed_content}"
                                    </p>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Quick Respond / Manual Triage Area */}
                    <div className="p-4 border-t border-slate-800 bg-slate-950/20 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                          Triage Operations
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          id="manual-reply"
                          placeholder="Type manual response or escalation details..."
                          className="flex-1 bg-slate-900 border border-slate-850 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500"
                        />
                        <button
                          onClick={() => {
                            const input = document.getElementById("manual-reply") as HTMLInputElement;
                            const lastEmail = selectedThread.emails[selectedThread.emails.length - 1];
                            if (input && input.value.trim() && lastEmail) {
                              handleRespond(lastEmail.id, input.value, false);
                              input.value = "";
                            }
                          }}
                          className="flex items-center gap-1.5 px-4 py-2 bg-slate-850 hover:bg-slate-800 text-xs font-bold text-slate-200 rounded-lg border border-slate-800 transition-colors"
                        >
                          <Send className="h-3.5 w-3.5" />
                          Reply
                        </button>
                        <button
                          onClick={() => {
                            const input = document.getElementById("manual-reply") as HTMLInputElement;
                            const lastEmail = selectedThread.emails[selectedThread.emails.length - 1];
                            if (lastEmail) {
                              handleRespond(lastEmail.id, input?.value || "Human escalation triggered", true);
                              if (input) input.value = "";
                            }
                          }}
                          className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-xs font-bold text-white rounded-lg transition-colors shadow-md shadow-rose-600/10"
                        >
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Escalate
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Right Contact and Reputation Profile Pane */}
                  <div className="w-[300px] bg-slate-950/40 p-4 space-y-6 overflow-y-auto">
                    
                    {/* Contact Profile card */}
                    <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-4 space-y-4">
                      <div className="flex items-center gap-2.5 border-b border-slate-900 pb-3">
                        <div className="bg-slate-900 p-2 rounded-lg border border-slate-800 text-slate-400">
                          <User className="h-5 w-5" />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-slate-100">
                            {contactProfile?.contact?.name || "Customer Profile"}
                          </h4>
                          <span className="text-[10px] text-slate-500 font-mono block">
                            {selectedThread.sender_email}
                          </span>
                        </div>
                      </div>

                      {contactProfile ? (
                        <div className="space-y-3 text-[11px]">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Company:</span>
                            <span className="text-slate-200 font-semibold">{contactProfile.contact.company || "N/A"}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">CRM Status:</span>
                            <span className={`px-2 py-0.5 rounded font-extrabold text-[9px] ${
                              contactProfile.contact.status === "VIP"
                                ? "bg-amber-500/15 border border-amber-500/20 text-amber-400 animate-pulse"
                                : "bg-slate-800 border border-slate-700 text-slate-300"
                            }`}>
                              {contactProfile.contact.status}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Account Value:</span>
                            <span className="text-slate-200 font-semibold font-mono">
                              ${contactProfile.contact.account_value?.toLocaleString(undefined, { minimumFractionDigits: 2 }) || "0.00"}
                            </span>
                          </div>
                          <div className="flex items-center justify-between border-t border-slate-900 pt-2.5">
                            <span className="text-slate-400">Churn Risk Score:</span>
                            <span className={`font-mono font-bold ${
                              contactProfile.churn_risk_score >= 0.7
                                ? "text-rose-500"
                                : contactProfile.churn_risk_score >= 0.35
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}>
                              {(contactProfile.churn_risk_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Active Threads:</span>
                            <span className="text-slate-200 font-semibold">{contactProfile.open_thread_count}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-[10px] text-slate-500 italic">Loading CRM metrics...</div>
                      )}
                    </div>

                    {/* Web reputation sentiment scraper results */}
                    <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-4 space-y-4">
                      <h4 className="text-xs font-bold text-slate-300 flex items-center gap-1.5 uppercase tracking-wider">
                        <Globe className="h-4 w-4 text-cyan-400" />
                        Market Intelligence
                      </h4>
                      {reputationData ? (
                        <div className="space-y-4 text-[11px]">
                          {reputationData.trustpilot ? (
                            <div className="space-y-1 p-2 bg-slate-900/60 rounded border border-slate-850">
                              <div className="flex items-center justify-between text-slate-300 font-bold">
                                <span>Trustpilot</span>
                                <span className="text-emerald-400">{reputationData.trustpilot.rating || "N/A"} ★</span>
                              </div>
                              <span className="text-[9px] text-slate-500 font-mono truncate block">
                                {reputationData.trustpilot.url}
                              </span>
                            </div>
                          ) : (
                            <div className="text-[10px] text-slate-500 italic">No Trustpilot reviews cached.</div>
                          )}

                          {reputationData.g2 ? (
                            <div className="space-y-1 p-2 bg-slate-900/60 rounded border border-slate-850">
                              <div className="flex items-center justify-between text-slate-300 font-bold">
                                <span>G2</span>
                                <span className="text-emerald-400">{reputationData.g2.rating || "N/A"} ★</span>
                              </div>
                              <span className="text-[9px] text-slate-500 font-mono truncate block">
                                {reputationData.g2.url}
                              </span>
                            </div>
                          ) : (
                            <div className="text-[10px] text-slate-500 italic">No G2 reviews cached.</div>
                          )}

                          {reputationData.recent_themes && (
                            <div className="space-y-1.5 pt-1.5 border-t border-slate-900">
                              <div className="text-slate-400 font-semibold">Common Themes:</div>
                              <div className="flex flex-wrap gap-1">
                                {reputationData.recent_themes.map((theme: string, i: number) => (
                                  <span key={i} className="bg-slate-800 text-slate-300 text-[9px] px-1.5 py-0.5 rounded">
                                    {theme}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-[10px] text-slate-500 italic">No public reputation scraped yet.</div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-xs p-8 bg-slate-900/10">
                  <Clock className="h-12 w-12 text-slate-700 animate-pulse mb-3" />
                  Select a thread from the inbox to begin triaging.
                </div>
              )}
            </div>
          </div>
        )}

        {/* View 3: Analytics Dashboard */}
        {activeTab === "analytics" && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            
            {/* KPI cards layout */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Total Ingested</span>
                  <h3 className="text-2xl font-bold text-slate-100 font-mono mt-1">{stats.total}</h3>
                </div>
                <Activity className="h-8 w-8 text-violet-500/40" />
              </div>
              <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Auto-Replied Rate</span>
                  <h3 className="text-2xl font-bold text-emerald-400 font-mono mt-1">
                    {stats.total > 0 ? ((stats.replied / stats.total) * 100).toFixed(0) : 0}%
                  </h3>
                </div>
                <CheckCircle className="h-8 w-8 text-emerald-500/40" />
              </div>
              <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Escalated Rate</span>
                  <h3 className="text-2xl font-bold text-amber-400 font-mono mt-1">
                    {stats.total > 0 ? ((stats.escalated / stats.total) * 100).toFixed(0) : 0}%
                  </h3>
                </div>
                <TrendingDown className="h-8 w-8 text-amber-500/40" />
              </div>
              <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Critical Escalations</span>
                  <h3 className="text-2xl font-bold text-rose-500 font-mono mt-1">{stats.critical}</h3>
                </div>
                <AlertTriangle className="h-8 w-8 text-rose-500/40 animate-pulse" />
              </div>
            </div>

            {/* Custom SVG Charts widgets */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* SVG Sentiment trend timeline */}
              <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-5 space-y-4">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Activity className="h-4 w-4 text-violet-400" />
                  Sentiment Trend (Global Timeline)
                </h4>
                <div className="h-48 flex items-end justify-between border-b border-l border-slate-800 pb-2 pl-2 relative">
                  <span className="absolute left-2 top-2 text-[9px] text-emerald-400">+1.0 Positive</span>
                  <span className="absolute left-2 bottom-2 text-[9px] text-rose-500">-1.0 Negative</span>
                  
                  {/* Draw mock trend line */}
                  <svg className="w-full h-full absolute inset-0 overflow-visible" preserveAspectRatio="none">
                    <polyline
                      fill="none"
                      stroke="#8b5cf6"
                      strokeWidth="3"
                      points="10,80 70,60 130,120 190,90 250,50 310,110 370,140 430,90 490,130"
                    />
                    {/* Dots */}
                    <circle cx="10" cy="80" r="4" fill="#a78bfa" />
                    <circle cx="70" cy="60" r="4" fill="#a78bfa" />
                    <circle cx="130" cy="120" r="4" fill="#a78bfa" />
                    <circle cx="190" cy="90" r="4" fill="#a78bfa" />
                    <circle cx="250" cy="50" r="4" fill="#a78bfa" />
                    <circle cx="310" cy="110" r="4" fill="#a78bfa" />
                    <circle cx="370" cy="140" r="4" fill="#f43f5e" />
                    <circle cx="430" cy="90" r="4" fill="#a78bfa" />
                    <circle cx="490" cy="130" r="4" fill="#a78bfa" />
                  </svg>
                </div>
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>Nov 1</span>
                  <span>Nov 5</span>
                  <span>Nov 10</span>
                  <span>Nov 15</span>
                  <span>Nov 20</span>
                </div>
              </div>

              {/* HTML/CSS Bar chart for Categories breakdown */}
              <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-5 space-y-4">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <ChartIcon className="h-4 w-4 text-violet-400" />
                  Category distribution breakdown
                </h4>
                <div className="space-y-3.5">
                  {Object.entries(getCategoryDistribution()).map(([cat, count]) => {
                    const percentage = threads.length > 0 ? (count / threads.length) * 100 : 0;
                    return (
                      <div key={cat} className="space-y-1">
                        <div className="flex justify-between text-[11px] font-semibold">
                          <span className="text-slate-300">{cat}</span>
                          <span className="text-slate-400 font-mono">{count} ({percentage.toFixed(0)}%)</span>
                        </div>
                        <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-violet-600 to-indigo-500 h-full rounded-full"
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* VIP At-Risk accounts lists */}
            <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-5 space-y-4">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-rose-500" />
                At-Risk VIP Accounts
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-bold uppercase tracking-wider">
                    <tr>
                      <th className="p-3">Customer Email</th>
                      <th className="p-3">Company</th>
                      <th className="p-3">Account Value</th>
                      <th className="p-3">Churn Risk</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850/60">
                    {threads
                      .filter((t) => t.sender_email.includes("karen") || t.sender_email.includes("bob"))
                      .slice(0, 3)
                      .map((t, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/30">
                          <td className="p-3 font-semibold text-violet-400">{t.sender_email}</td>
                          <td className="p-3 text-slate-300">{t.sender_email.includes("karen") ? "Retail Co" : "Enterprise Net"}</td>
                          <td className="p-3 font-mono text-slate-300">${t.sender_email.includes("karen") ? "48,000" : "150,000"}</td>
                          <td className="p-3 text-rose-500 font-bold">85%</td>
                          <td className="p-3">
                            <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded text-[10px] font-bold">
                              High Risk
                            </span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* View 4: RAG Debugger tab */}
        {activeTab === "rag" && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div className="bg-slate-950/60 border border-slate-850 rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <Database className="h-5 w-5 text-violet-400" />
                RAG Vector Search Debugger
              </h3>
              <p className="text-xs text-slate-400">
                Run semantic search queries against the seeded knowledge base to retrieve specific paragraphs and view similarity scores.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  placeholder="Enter semantic query (e.g., SLA response credit calculation)..."
                  className="flex-1 bg-slate-900 border border-slate-850 rounded-lg px-3.5 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
                <button
                  onClick={handleRagSearch}
                  className="px-6 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-xs font-bold text-white rounded-lg transition-colors shadow-md shadow-violet-600/10"
                >
                  Retrieve
                </button>
              </div>
            </div>

            {/* RAG Results Display */}
            {ragResults.length > 0 && (
              <div className="space-y-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Retrieved Chunks
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {ragResults.map((chunk, idx) => (
                    <div key={idx} className="bg-slate-950/40 border border-slate-850 rounded-xl p-4 space-y-3 shadow-sm">
                      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                        <span className="text-xs font-semibold text-violet-400 flex items-center gap-1">
                          <FileText className="h-4 w-4" />
                          {chunk.source_doc}
                        </span>
                        <span className="text-[10px] font-mono text-emerald-400 font-bold">
                          Score: {(chunk.similarity_score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 italic leading-relaxed whitespace-pre-wrap">
                        "{chunk.chunk_text}"
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
