import { useState, useEffect } from 'react';
import { buildLineDiff } from './codeDiff.js';
import {
  Bug,
  Code2,
  CheckCircle2,
  XCircle,
  Clock,
  Database,
  History,
  Upload,
  Copy,
  Check,
  ShieldCheck,
  Cpu,
  ArrowRight,
  Terminal,
  AlertTriangle,
  RefreshCw,
  Trash2,
  ChevronRight,
  BookmarkPlus,
  Play,
  RotateCcw,
  CheckCheck
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const SAMPLE_BUGS = [
  {
    name: 'ZeroDivision',
    tag: 'Runtime',
    color: 'pill-rose',
    code: `def calculate_average(scores):
    total = sum(scores)
    return total / len(scores)

# Test with empty list
data = []
print(calculate_average(data))`,
  },
  {
    name: 'Mutable Default',
    tag: 'Logic Trap',
    color: 'pill-amber',
    code: `def register_user(username, roles=[]):
    roles.append(username)
    return roles

print(register_user("Alice"))
print(register_user("Bob")) # Unexpectedly retains Alice!`,
  },
  {
    name: 'Dict KeyError',
    tag: 'Key Lookup',
    color: 'pill-rose',
    code: `def get_user_email(profile):
    return profile['email']

user = {'name': 'Charlie', 'active': True}
print(get_user_email(user))`,
  },
  {
    name: 'UnboundLocal',
    tag: 'Scope Trap',
    color: 'pill-violet',
    code: `counter = 0

def increment():
    counter += 1
    return counter

increment()`,
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('studio'); // 'studio' | 'knowledge' | 'history'
  const [code, setCode] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [debugResult, setDebugResult] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // System Stats
  const [health, setHealth] = useState(null);
  const [knowledgeItems, setKnowledgeItems] = useState([]);
  const [knowledgeSearch, setKnowledgeSearch] = useState('');
  const [historyItems, setHistoryItems] = useState([]);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch {
      setHealth({ status: 'unreachable' });
    }
  };

  const fetchKnowledge = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/knowledge?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setKnowledgeItems(data.records || []);
      }
    } catch (err) {
      console.error('Failed to fetch knowledge:', err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryItems(data.history || []);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  useEffect(() => {
    queueMicrotask(() => {
      fetchHealth();
      fetchKnowledge();
      fetchHistory();
    });
  }, []);

  const handleDebug = async () => {
    if (!code.trim()) {
      setApiError('Please enter Python code to analyze.');
      return;
    }

    const submittedCode = code;
    const submittedErrorMessage = errorMessage;
    setIsLoading(true);
    setApiError(null);
    setDebugResult(null);
    setSavedSuccess(false);

    // Dynamic Multi-Agent visual stepper
    setCurrentStep('Agent 1: Error Analysis & AST Inspection via MCP...');
    const stepTimer1 = setTimeout(() => {
      setCurrentStep('Agent 2: Retrieving Verified Solutions from Qdrant RAG...');
    }, 1200);
    const stepTimer2 = setTimeout(() => {
      setCurrentStep('Agent 3: Synthesizing Fix & Running Isolated Sandbox Tests...');
    }, 2400);

    try {
      const response = await fetch(`${API_BASE}/api/debug`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: submittedCode,
          error_message: submittedErrorMessage,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      setDebugResult(data);
      fetchHistory();
      fetchHealth();
    } catch (err) {
      setApiError(err.message || 'An unexpected error occurred while debugging.');
    } finally {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setIsLoading(false);
      setCurrentStep('');
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.py')) {
      setApiError('Please upload a Python (.py) file.');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      setCode(event.target.result);
      setErrorMessage(''); // Clear previous traceback so uploaded code is evaluated cleanly
      setApiError(null);
      setDebugResult(null);
    };
    reader.readAsText(file);
  };

  const handleCopyCode = (textToCopy) => {
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveToKnowledge = async () => {
    if (!debugResult) return;
    try {
      const payload = {
        code: code,
        corrected_code: debugResult.corrected_code,
        error_type: debugResult.error_type || 'PythonError',
        root_cause: debugResult.root_cause || '',
        test_code: debugResult.test_code || '',
        title: `Fix for ${debugResult.error_type || 'Python bug'}`
      };

      const res = await fetch(`${API_BASE}/api/knowledge/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setSavedSuccess(true);
        fetchKnowledge();
        fetchHealth();
      }
    } catch (err) {
      console.error('Failed to save to knowledge base:', err);
    }
  };

  const handleClearHistory = async () => {
    try {
      await fetch(`${API_BASE}/api/history`, { method: 'DELETE' });
      setHistoryItems([]);
    } catch (err) {
      console.error(err);
    }
  };

  const filteredKnowledge = knowledgeItems.filter((item) => {
    const q = knowledgeSearch.toLowerCase();
    return (
      item.title?.toLowerCase().includes(q) ||
      item.error_type?.toLowerCase().includes(q) ||
      item.root_cause?.toLowerCase().includes(q)
    );
  });
  const diffRows = debugResult
    ? buildLineDiff(debugResult.code || code, debugResult.corrected_code || debugResult.code || code)
    : [];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#000000' }}>
      
      {/* Top Obsidian Navigation Bar */}
      <header
        style={{
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: '#040405',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          padding: '12px 28px',
        }}
      >
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
          
          {/* Logo & Meta */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '9px',
                backgroundColor: '#0a0a0c',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 16px -2px rgba(16, 185, 129, 0.4)',
              }}
            >
              <Bug size={19} color="#10b981" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px', fontWeight: '800', letterSpacing: '-0.03em', color: '#ffffff' }}>
                  DevFix
                </span>
                <span style={{ fontSize: '16px', fontWeight: '800', letterSpacing: '-0.03em', color: '#10b981' }}>
                  AI
                </span>
                <span className="pill pill-emerald" style={{ fontSize: '10px', padding: '1px 7px' }}>
                  Multi-Agent v1.0
                </span>
              </div>
              <p style={{ fontSize: '11px', color: '#71717a', letterSpacing: '-0.01em' }}>
                LangGraph • Groq • Qdrant RAG • Python MCP SDK
              </p>
            </div>
          </div>

          {/* Obsidian Navigation Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: '#090a0d', padding: '4px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.07)' }}>
            <button
              onClick={() => setActiveTab('studio')}
              className="btn-obsidian"
              style={{
                backgroundColor: activeTab === 'studio' ? '#18191d' : 'transparent',
                borderColor: activeTab === 'studio' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                color: activeTab === 'studio' ? '#ffffff' : '#71717a',
              }}
            >
              <Code2 size={15} color={activeTab === 'studio' ? '#10b981' : '#71717a'} />
              <span>Debug Studio</span>
            </button>
            <button
              onClick={() => setActiveTab('knowledge')}
              className="btn-obsidian"
              style={{
                backgroundColor: activeTab === 'knowledge' ? '#18191d' : 'transparent',
                borderColor: activeTab === 'knowledge' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                color: activeTab === 'knowledge' ? '#ffffff' : '#71717a',
              }}
            >
              <Database size={15} color={activeTab === 'knowledge' ? '#8b5cf6' : '#71717a'} />
              <span>Knowledge Base ({health?.services?.qdrant?.total_records || knowledgeItems.length || '35+'})</span>
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className="btn-obsidian"
              style={{
                backgroundColor: activeTab === 'history' ? '#18191d' : 'transparent',
                borderColor: activeTab === 'history' ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                color: activeTab === 'history' ? '#ffffff' : '#71717a',
              }}
            >
              <History size={15} color={activeTab === 'history' ? '#06b6d4' : '#71717a'} />
              <span>History ({historyItems.length})</span>
            </button>
          </div>

          {/* Backend Status indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              className={`pill ${health?.status === 'healthy' ? 'pill-emerald' : 'pill-rose'}`}
              style={{ padding: '5px 12px', fontSize: '11px' }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: health?.status === 'healthy' ? '#10b981' : '#f43f5e',
                  boxShadow: health?.status === 'healthy' ? '0 0 10px #10b981' : 'none',
                }}
              />
              {health?.status === 'healthy' ? 'Backend Ready' : 'Connecting Backend...'}
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main style={{ flex: 1, maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '24px 24px' }}>
        
        {apiError && (
          <div
            className="obsidian-card"
            style={{
              borderColor: 'rgba(244, 63, 94, 0.3)',
              backgroundColor: 'rgba(244, 63, 94, 0.05)',
              padding: '14px 18px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              color: '#fda4af',
            }}
          >
            <AlertTriangle size={18} color="#f43f5e" />
            <span style={{ fontSize: '13px' }}>{apiError}</span>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 1: DEBUG STUDIO */}
        {/* ============================================================== */}
        {activeTab === 'studio' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '22px' }}>
            
            {/* Left Column: Code Inputs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Preset Chips Bar */}
              <div className="obsidian-card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#71717a' }}>
                    Quick Presets:
                  </span>
                  {SAMPLE_BUGS.map((sample, idx) => (
                    <button
                      key={idx}
                      className="btn-obsidian"
                      style={{ padding: '4px 10px', fontSize: '11.5px', gap: '6px' }}
                      onClick={() => {
                        setCode(sample.code);
                        setErrorMessage('');
                        setDebugResult(null);
                      }}
                    >
                      <span className={`pill ${sample.color}`} style={{ fontSize: '9px', padding: '1px 5px' }}>
                        {sample.tag}
                      </span>
                      <span>{sample.name}</span>
                    </button>
                  ))}
                </div>

                <label className="btn-obsidian" style={{ cursor: 'pointer', fontSize: '11.5px' }}>
                  <Upload size={13} color="#10b981" />
                  <span>Upload .py</span>
                  <input
                    type="file"
                    accept=".py"
                    style={{ display: 'none' }}
                    onChange={handleFileUpload}
                  />
                </label>
              </div>

              {/* Code Editor Window */}
              <div className="editor-window">
                <div className="editor-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="window-dots">
                      <div className="window-dot" style={{ backgroundColor: '#ff5f56' }} />
                      <div className="window-dot" style={{ backgroundColor: '#ffbd2e' }} />
                      <div className="window-dot" style={{ backgroundColor: '#27c93f' }} />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
                      <Code2 size={13} color="#10b981" />
                      <span className="font-mono" style={{ fontSize: '12px', color: '#e4e4e7' }}>
                        buggy_program.py
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: '#52525b' }}>Python AST Validated</span>
                    <button
                      className="btn-obsidian"
                      style={{ padding: '2px 8px', fontSize: '11px' }}
                      onClick={() => {
                        setCode('');
                        setErrorMessage('');
                        setDebugResult(null);
                      }}
                      title="Clear code and traceback"
                    >
                      <RotateCcw size={11} /> Clear All
                    </button>
                  </div>
                </div>
                <textarea
                  className="editor-textarea"
                  rows={13}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="# Paste your Python code here..."
                />
              </div>

              {/* Traceback Window */}
              <div className="editor-window">
                <div className="editor-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="window-dots">
                      <div className="window-dot" style={{ backgroundColor: '#ff5f56' }} />
                      <div className="window-dot" style={{ backgroundColor: '#ffbd2e' }} />
                      <div className="window-dot" style={{ backgroundColor: '#27c93f' }} />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
                      <Terminal size={13} color="#f43f5e" />
                      <span className="font-mono" style={{ fontSize: '12px', color: '#e4e4e7' }}>
                        traceback.log
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: '#52525b' }}>Auto-detected if empty</span>
                    {errorMessage && (
                      <button
                        className="btn-obsidian"
                        style={{ padding: '2px 8px', fontSize: '11px', color: '#fda4af' }}
                        onClick={() => setErrorMessage('')}
                        title="Clear traceback"
                      >
                        <RotateCcw size={11} /> Clear
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  className="editor-textarea"
                  rows={5}
                  value={errorMessage}
                  onChange={(e) => setErrorMessage(e.target.value)}
                  placeholder="Paste Python error message or console traceback (optional - auto-detected if left empty)..."
                  style={{ color: '#fda4af' }}
                />
              </div>

              {/* Action Button */}
              <div>
                <button
                  className="btn-emerald"
                  onClick={handleDebug}
                  disabled={isLoading}
                  style={{ width: '100%', padding: '13px', fontSize: '14.5px' }}
                >
                  {isLoading ? (
                    <>
                      <RefreshCw size={17} className="animate-spin-smooth" />
                      <span>{currentStep || 'Multi-Agent Workflow Running...'}</span>
                    </>
                  ) : (
                    <>
                      <Play size={16} fill="#000000" />
                      <span>Analyze & Debug with Multi-Agent AI</span>
                    </>
                  )}
                </button>
              </div>

            </div>

            {/* Right Column: AI Agent Outputs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {!debugResult && !isLoading && (
                <div
                  className="obsidian-card"
                  style={{
                    padding: '56px 28px',
                    textAlign: 'center',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '18px',
                    minHeight: '450px',
                  }}
                >
                  <div
                    style={{
                      width: '64px',
                      height: '64px',
                      borderRadius: '16px',
                      backgroundColor: '#0c0d10',
                      border: '1px solid rgba(16, 185, 129, 0.25)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 0 30px -5px rgba(16, 185, 129, 0.15)',
                    }}
                  >
                    <Cpu size={30} color="#10b981" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#ffffff', marginBottom: '6px' }}>
                      Autonomous Multi-Agent Engine
                    </h3>
                    <p style={{ fontSize: '13px', color: '#71717a', maxWidth: '420px', lineHeight: 1.6 }}>
                      Load an example preset or paste your code on the left. DevFix coordinates static AST analysis, Qdrant RAG retrieval, and isolated sandbox execution.
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                    <span className="pill pill-cyan">1. Error Analysis</span>
                    <span className="pill pill-violet">2. Qdrant RAG</span>
                    <span className="pill pill-emerald">3. Sandbox Validation</span>
                  </div>
                </div>
              )}

              {isLoading && (
                <div
                  className="obsidian-card"
                  style={{
                    padding: '36px 24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                    minHeight: '450px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div
                      style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '10px',
                        backgroundColor: '#10b98115',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <RefreshCw size={20} className="animate-spin-smooth" color="#10b981" />
                    </div>
                    <div>
                      <h4 style={{ fontSize: '15px', fontWeight: '700', color: '#ffffff' }}>
                        LangGraph Agent Pipeline Active
                      </h4>
                      <p style={{ fontSize: '12px', color: '#10b981' }}>{currentStep}</p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: '10px', backgroundColor: '#07080a', border: '1px solid var(--border-hairline)' }}>
                      <CheckCircle2 size={16} color="#06b6d4" />
                      <div>
                        <div style={{ fontSize: '12.5px', fontWeight: '600', color: '#ffffff' }}>Agent 1: AST & Traceback Inspection</div>
                        <div style={{ fontSize: '11px', color: '#71717a' }}>MCP analyze_code + read_error_log parsing offending lines</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: '10px', backgroundColor: '#07080a', border: '1px solid var(--border-hairline)' }}>
                      <Database size={16} color="#8b5cf6" />
                      <div>
                        <div style={{ fontSize: '12.5px', fontWeight: '600', color: '#ffffff' }}>Agent 2: Qdrant Vector Retrieval</div>
                        <div style={{ fontSize: '11px', color: '#71717a' }}>Querying MiniLM embeddings for verified debugging cases</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: '10px', backgroundColor: '#07080a', border: '1px solid var(--border-hairline)' }}>
                      <ShieldCheck size={16} color="#10b981" />
                      <div>
                        <div style={{ fontSize: '12.5px', fontWeight: '600', color: '#ffffff' }}>Agent 3: Sandbox Assertion Execution</div>
                        <div style={{ fontSize: '11px', color: '#71717a' }}>MCP run_tests executing in isolated subprocess with timeout</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {debugResult && !isLoading && (
                <>
                  <div className="obsidian-card" style={{ padding: '18px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '12px' }}>
                      <strong style={{ color: debugResult.issues?.length ? '#fda4af' : '#6ee7b7' }}>
                        {debugResult.validation_result?.passed && debugResult.validation_result?.tests_configured
                          ? 'Status: Tests Passed'
                          : debugResult.issues?.length ? `${debugResult.issues.length} issue(s) detected` : 'Status: No issues detected'}
                      </strong>
                      <span className="pill pill-dark">{debugResult.analysis_mode === 'static_analysis_and_execution' ? 'Static + execution' : 'Static analysis'}</span>
                    </div>
                    <p style={{ fontSize: '13px', color: '#cbd5d1', lineHeight: 1.6 }}>
                      {debugResult.validation_result?.passed && debugResult.validation_result?.tests_configured
                        ? 'Your code executed successfully and all configured tests passed.'
                        : debugResult.issues?.length ? debugResult.summary : 'Your Python code passed the available static checks. No definite errors were detected.'}
                    </p>
                    {debugResult.issues?.map((issue, index) => (
                      <div key={`${issue.error_type}-${issue.line}-${index}`} style={{ padding: '12px 0', borderTop: '1px solid var(--border-hairline)', marginTop: '10px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px', alignItems: 'center', marginBottom: '6px' }}>
                          <strong style={{ color: '#fda4af' }}>{issue.error_type}</strong>
                          {issue.line && <span className="pill pill-amber">Line {issue.line}</span>}
                          <span className="pill pill-dark">{issue.confirmed ? 'Confirmed' : 'Possible'}</span>
                          <span className="pill pill-dark">{issue.severity}</span>
                        </div>
                        <p style={{ color: '#d4d4d8', fontSize: '12.5px', lineHeight: 1.55 }}>{issue.explanation}</p>
                        {issue.suggested_fix && <p style={{ color: '#a1a1aa', fontSize: '12px', marginTop: '5px' }}>Suggested fix: {issue.suggested_fix}</p>}
                        {issue.evidence && <code style={{ display: 'block', color: '#71717a', fontSize: '11px', marginTop: '5px' }}>{issue.evidence}</code>}
                      </div>
                    ))}
                    {debugResult.request_id && <span className="pill pill-dark font-mono" style={{ marginTop: '8px' }}>{debugResult.request_id}</span>}
                  </div>

                  {/* Proposed Fix Window */}
                  <div className="editor-window">
                    <div className="editor-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="window-dots">
                          <div className="window-dot" style={{ backgroundColor: '#ff5f56' }} />
                          <div className="window-dot" style={{ backgroundColor: '#ffbd2e' }} />
                          <div className="window-dot" style={{ backgroundColor: '#27c93f' }} />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
                          <CheckCircle2 size={13} color="#10b981" />
                          <span className="font-mono" style={{ fontSize: '12px', color: '#10b981', fontWeight: '600' }}>
                            corrected_solution.py
                          </span>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          className="btn-obsidian"
                          onClick={() => {
                            setCode(debugResult.corrected_code);
                            setErrorMessage('');
                            setApiError(null);
                          }}
                          style={{ fontSize: '11.5px', padding: '4px 10px' }}
                        >
                          Apply Fix
                        </button>
                        <button
                          className="btn-obsidian"
                          onClick={() => handleCopyCode(debugResult.corrected_code)}
                          style={{ fontSize: '11.5px', padding: '4px 10px' }}
                        >
                          {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                          <span>{copied ? 'Copied' : 'Copy Fix'}</span>
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', overflowX: 'auto' }}>
                      {[['Original', 'original'], ['Corrected', 'corrected']].map(([title, side]) => (
                        <section key={side} style={{ minWidth: 280, borderRight: side === 'original' ? '1px solid var(--border-hairline)' : 0 }}>
                          <div style={{ padding: '8px 12px', color: '#a1a1aa', fontSize: '11px', borderBottom: '1px solid var(--border-hairline)' }}>{title}</div>
                          <pre className="font-mono" style={{ margin: 0, padding: '8px 0', fontSize: '12px', lineHeight: 1.6, overflowX: 'auto', backgroundColor: '#040506' }}>
                            {diffRows.map((row, index) => {
                              const line = side === 'original' ? row.original : row.corrected;
                              const lineNumber = side === 'original' ? row.originalLine : row.correctedLine;
                              const changed = row.type !== 'context';
                              const foreground = row.type === 'removed' ? '#fda4af' : row.type === 'added' ? '#6ee7b7' : '#e4e4e7';
                              const background = row.type === 'removed' ? 'rgba(244, 63, 94, 0.12)' : row.type === 'added' ? 'rgba(16, 185, 129, 0.12)' : row.type === 'modified' ? 'rgba(234, 179, 8, 0.10)' : 'transparent';
                              return <div key={`${row.type}-${index}`} style={{ display: 'flex', minHeight: '1.6em', whiteSpace: 'pre', color: foreground, backgroundColor: background }}><span style={{ width: 42, flex: '0 0 42px', paddingRight: 8, textAlign: 'right', color: changed ? foreground : '#52525b', userSelect: 'none' }}>{lineNumber ?? ''}</span><code style={{ paddingRight: 12 }}>{line ?? ''}</code></div>;
                            })}
                          </pre>
                        </section>
                      ))}
                    </div>

                    {debugResult.explanation && (
                      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-hairline)', fontSize: '12.5px', color: '#a1a1aa', backgroundColor: '#07080a' }}>
                        <strong style={{ color: '#ffffff' }}>Why this works: </strong>
                        {debugResult.explanation}
                      </div>
                    )}
                  </div>

                  {/* Sandboxed Test Outcome Window */}
                  <div className="editor-window">
                    <div className="editor-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <ShieldCheck size={14} color="#10b981" />
                        <span className="font-mono" style={{ fontSize: '12px', color: '#e4e4e7' }}>
                          Sandbox Test Runner (MCP run_tests)
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {debugResult.validation_result?.passed && debugResult.validation_result?.tests_configured ? (
                          <span className="pill pill-emerald" style={{ fontSize: '11px' }}>
                            <CheckCheck size={12} /> Tests Passed
                          </span>
                        ) : !debugResult.validation_result?.tests_configured ? (
                          <span className="pill pill-dark" style={{ fontSize: '11px' }}>
                            {debugResult.execution_result?.executed ? 'Execution completed' : 'Static analysis only'}
                          </span>
                        ) : (
                          <span className="pill pill-rose" style={{ fontSize: '11px' }}>
                            <XCircle size={12} /> {debugResult.validation_result?.status?.toUpperCase() || 'FAILED'}
                          </span>
                        )}
                        {debugResult.validation_result?.duration_ms && (
                          <span style={{ fontSize: '11px', color: '#71717a' }}>
                            {debugResult.validation_result.duration_ms} ms
                          </span>
                        )}
                      </div>
                    </div>

                    {debugResult.test_code && (
                      <div style={{ padding: '12px 16px', backgroundColor: '#040506' }}>
                        <span style={{ fontSize: '10px', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Executed Assertions:
                        </span>
                        <pre
                          className="font-mono"
                          style={{
                            padding: '10px 12px',
                            borderRadius: '6px',
                            backgroundColor: '#0a0b0d',
                            border: '1px solid var(--border-hairline)',
                            fontSize: '12px',
                            marginTop: '6px',
                            overflowX: 'auto',
                            color: '#e4e4e7',
                          }}
                        >
                          <code>{debugResult.test_code}</code>
                        </pre>
                      </div>
                    )}

                    {debugResult.validation_result?.stderr && (
                      <div style={{ padding: '10px 16px', backgroundColor: 'rgba(244, 63, 94, 0.08)', borderTop: '1px solid rgba(244, 63, 94, 0.2)' }}>
                        <span style={{ fontSize: '10px', color: '#fb7185', fontWeight: '700', textTransform: 'uppercase' }}>Stderr Output:</span>
                        <pre className="font-mono" style={{ fontSize: '11px', color: '#fda4af', marginTop: '4px', whiteSpace: 'pre-wrap' }}>
                          {debugResult.validation_result.stderr}
                        </pre>
                      </div>
                    )}
                  </div>

                  {/* Qdrant RAG Citations */}
                  {debugResult.rag_references?.length > 0 && (
                    <div className="obsidian-card" style={{ padding: '18px 20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                        <Database size={15} color="#8b5cf6" />
                        <span style={{ fontSize: '13px', fontWeight: '700', color: '#ffffff' }}>
                          Qdrant Verified Knowledge Base References
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {debugResult.rag_references.map((ref, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '12px 14px',
                              borderRadius: '8px',
                              backgroundColor: '#07080a',
                              border: '1px solid var(--border-hairline)',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ fontSize: '13px', fontWeight: '600', color: '#c084fc' }}>
                                {ref.title || ref.error_type}
                              </span>
                              <span className="pill pill-violet" style={{ fontSize: '10px' }}>
                                {Math.round((ref.score || 0.8) * 100)}% Match
                              </span>
                            </div>
                            <p style={{ fontSize: '12px', color: '#a1a1aa', lineHeight: 1.5 }}>
                              {ref.root_cause || ref.snippet}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Opt-in Save Card */}
                  <div
                    className="obsidian-card"
                    style={{
                      padding: '16px 20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '12px',
                      borderColor: savedSuccess ? 'rgba(16, 185, 129, 0.4)' : 'var(--border-hairline)',
                      backgroundColor: savedSuccess ? 'rgba(16, 185, 129, 0.04)' : 'var(--black-card)',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <BookmarkPlus size={15} color={savedSuccess ? '#10b981' : '#a1a1aa'} />
                        <span style={{ fontSize: '13.5px', fontWeight: '600', color: '#ffffff' }}>
                          Save Solution to Knowledge Base?
                        </span>
                      </div>
                      <p style={{ fontSize: '11.5px', color: '#71717a', marginTop: '2px' }}>
                        Opt-in only. Automatic privacy scrubber redacts API keys, passwords, and tokens before saving to Qdrant.
                      </p>
                    </div>

                    <button
                      className="btn-obsidian"
                      onClick={handleSaveToKnowledge}
                      disabled={savedSuccess}
                      style={{
                        backgroundColor: savedSuccess ? 'rgba(16, 185, 129, 0.15)' : '#141518',
                        borderColor: savedSuccess ? '#10b981' : 'var(--border-hairline)',
                        color: savedSuccess ? '#34d399' : '#ffffff',
                      }}
                    >
                      {savedSuccess ? (
                        <>
                          <Check size={13} color="#10b981" />
                          <span>Indexed in Qdrant</span>
                        </>
                      ) : (
                        <>
                          <BookmarkPlus size={13} color="#10b981" />
                          <span>Add to Knowledge Base</span>
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 2: KNOWLEDGE BASE VIEW */}
        {/* ============================================================== */}
        {activeTab === 'knowledge' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div className="obsidian-card" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <h2 style={{ fontSize: '17px', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Database size={19} color="#8b5cf6" />
                  Qdrant Vector Knowledge Base
                </h2>
                <p style={{ fontSize: '12px', color: '#71717a', marginTop: '4px' }}>
                  Total verified debugging cases indexed: <strong style={{ color: '#ffffff' }}>{knowledgeItems.length}</strong> (Local embedded Qdrant instance)
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="text"
                  placeholder="Search error types, causes, tags..."
                  value={knowledgeSearch}
                  onChange={(e) => setKnowledgeSearch(e.target.value)}
                  style={{
                    backgroundColor: '#07080a',
                    border: '1px solid var(--border-hairline)',
                    borderRadius: '8px',
                    padding: '8px 14px',
                    color: '#ffffff',
                    fontSize: '12.5px',
                    width: '300px',
                    outline: 'none',
                  }}
                />
                <button
                  className="btn-obsidian"
                  onClick={() => {
                    fetchKnowledge();
                    fetchHealth();
                  }}
                >
                  <RefreshCw size={13} /> Refresh
                </button>
              </div>
            </div>

            {/* Knowledge Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: '16px' }}>
              {filteredKnowledge.map((item, idx) => (
                <div key={idx} className="obsidian-card obsidian-card-interactive" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="pill pill-violet" style={{ fontSize: '11px' }}>
                      {item.error_type}
                    </span>
                    <span className="pill pill-dark" style={{ fontSize: '10px' }}>
                      {item.category || 'Python'}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '14.5px', fontWeight: '700', color: '#ffffff' }}>
                    {item.title}
                  </h3>

                  <p style={{ fontSize: '12.5px', color: '#a1a1aa', lineHeight: 1.55, flex: 1 }}>
                    {item.root_cause}
                  </p>

                  {item.corrected_code && (
                    <div style={{ marginTop: '6px' }}>
                      <span style={{ fontSize: '10px', color: '#52525b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Verified Fix:</span>
                      <pre
                        className="font-mono"
                        style={{
                          backgroundColor: '#040506',
                          border: '1px solid var(--border-hairline)',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          fontSize: '11.5px',
                          marginTop: '4px',
                          overflowX: 'auto',
                          maxHeight: '130px',
                          color: '#6ee7b7',
                        }}
                      >
                        <code>{item.corrected_code}</code>
                      </pre>
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
                    <button
                      className="btn-obsidian"
                      style={{ fontSize: '11.5px', padding: '4px 10px' }}
                      onClick={() => {
                        if (item.buggy_code) setCode(item.buggy_code);
                        if (item.title) setErrorMessage(item.title);
                        setActiveTab('studio');
                      }}
                    >
                      Load into Studio <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* TAB 3: HISTORY LOG */}
        {/* ============================================================== */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div className="obsidian-card" style={{ padding: '18px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h2 style={{ fontSize: '17px', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <History size={19} color="#06b6d4" />
                  Debugging Session History
                </h2>
                <p style={{ fontSize: '12px', color: '#71717a', marginTop: '4px' }}>
                  Sessions are stored separately from reusable vector knowledge for maximum privacy.
                </p>
              </div>

              {historyItems.length > 0 && (
                <button className="btn-obsidian" onClick={handleClearHistory} style={{ color: '#f43f5e' }}>
                  <Trash2 size={13} /> Clear History
                </button>
              )}
            </div>

            {historyItems.length === 0 ? (
              <div className="obsidian-card" style={{ padding: '56px', textAlign: 'center', color: '#71717a' }}>
                No debugging sessions recorded yet. Run a session in the Debug Studio!
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {historyItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="obsidian-card obsidian-card-interactive"
                    style={{
                      padding: '16px 20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '8px',
                          backgroundColor: item.validation_result?.passed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                          border: `1px solid ${item.validation_result?.passed ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {item.validation_result?.passed ? (
                          <CheckCircle2 size={16} color="#10b981" />
                        ) : (
                          <XCircle size={16} color="#f43f5e" />
                        )}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '13.5px', fontWeight: '700', color: '#ffffff' }}>
                            {item.error_type || 'Python Issue'}
                          </span>
                          <span className="pill pill-violet" style={{ fontSize: '10px' }}>
                            {item.status}
                          </span>
                        </div>
                        <p style={{ fontSize: '12px', color: '#71717a', marginTop: '2px' }}>
                          {item.summary || item.root_cause || 'Debugging session'}
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <span style={{ fontSize: '11px', color: '#52525b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} />
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                      <button
                        className="btn-obsidian"
                        style={{ fontSize: '11.5px' }}
                        onClick={() => {
                          setCode(item.code);
                          setErrorMessage(item.error_message || '');
                          setDebugResult(item);
                          setActiveTab('studio');
                        }}
                      >
                        Inspect in Studio <ChevronRight size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Sleek Minimal Footer */}
      <footer
        style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          padding: '16px 24px',
          textAlign: 'center',
          fontSize: '11.5px',
          color: '#52525b',
          backgroundColor: '#020203',
        }}
      >
        DevFix AI • Pitch Black Obsidian Developer Dashboard • Powered by LangGraph, Groq, Qdrant & Python MCP
      </footer>
    </div>
  );
}
