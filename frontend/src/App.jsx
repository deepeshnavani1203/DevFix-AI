import React, { useState, useEffect } from 'react';
import {
  Bug,
  Code2,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  Database,
  History,
  Upload,
  Copy,
  Check,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
  Terminal,
  AlertTriangle,
  RefreshCw,
  Trash2,
  FileCode2,
  ChevronRight,
  BookmarkPlus
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const SAMPLE_BUGS = [
  {
    name: 'ZeroDivision in Average',
    code: `def calculate_average(scores):
    total = sum(scores)
    return total / len(scores)

# Test with empty list
data = []
print(calculate_average(data))`,
    error: `Traceback (most recent call last):
  File "calc.py", line 6, in <module>
    print(calculate_average(data))
  File "calc.py", line 3, in calculate_average
    return total / len(scores)
ZeroDivisionError: division by zero`
  },
  {
    name: 'Mutable Default Argument',
    code: `def register_user(username, roles=[]):
    roles.append(username)
    return roles

print(register_user("Alice"))
print(register_user("Bob")) # Unexpectedly retains Alice!`,
    error: `LogicError: Default argument 'roles' retains state across multiple invocations.`
  },
  {
    name: 'Dict KeyError Access',
    code: `def get_user_email(profile):
    return profile['email']

user = {'name': 'Charlie', 'active': True}
print(get_user_email(user))`,
    error: `Traceback (most recent call last):
  File "user.py", line 5, in <module>
    print(get_user_email(user))
  File "user.py", line 2, in get_user_email
    return profile['email']
KeyError: 'email'`
  },
  {
    name: 'UnboundLocalError Scope Trap',
    code: `counter = 0

def increment():
    counter += 1
    return counter

increment()`,
    error: `Traceback (most recent call last):
  File "scope.py", line 7, in <module>
    increment()
  File "scope.py", line 4, in increment
    counter += 1
UnboundLocalError: cannot access local variable 'counter' where it is not associated with a value`
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('studio'); // 'studio' | 'knowledge' | 'history'
  const [code, setCode] = useState(SAMPLE_BUGS[0].code);
  const [errorMessage, setErrorMessage] = useState(SAMPLE_BUGS[0].error);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [debugResult, setDebugResult] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // System Health & Knowledge Stats
  const [health, setHealth] = useState(null);
  const [knowledgeItems, setKnowledgeItems] = useState([]);
  const [knowledgeSearch, setKnowledgeSearch] = useState('');
  const [historyItems, setHistoryItems] = useState([]);

  // Load health on mount
  useEffect(() => {
    fetchHealth();
    fetchKnowledge();
    fetchHistory();
  }, []);

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

  const handleDebug = async () => {
    if (!code.trim()) {
      setApiError('Please enter Python code to analyze.');
      return;
    }

    setIsLoading(true);
    setApiError(null);
    setDebugResult(null);
    setSavedSuccess(false);

    // Multi-Agent visual stepper
    setCurrentStep('Agent 1: Error Analysis & AST Inspection via MCP...');
    const stepTimer1 = setTimeout(() => {
      setCurrentStep('Agent 2: Retrieving Verified Solutions from Qdrant RAG...');
    }, 1200);
    const stepTimer2 = setTimeout(() => {
      setCurrentStep('Agent 3: Synthesizing Fix & Executing Sandboxed Tests via MCP...');
    }, 2400);

    try {
      const response = await fetch(`${API_BASE}/api/debug`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: code,
          error_message: errorMessage,
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
      setApiError(null);
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

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Bar */}
      <header
        style={{
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(7, 9, 14, 0.85)',
          backdropFilter: 'blur(12px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          padding: '14px 28px',
        }}
      >
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
          {/* Logo & Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 16px rgba(56, 189, 248, 0.4)',
              }}
            >
              <Bug size={22} color="#030712" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h1 style={{ fontSize: '18px', fontWeight: '700', letterSpacing: '-0.02em', color: '#fff' }}>
                  DevFix AI
                </h1>
                <span className="badge badge-purple" style={{ fontSize: '11px', padding: '2px 8px' }}>
                  Multi-Agent
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                LangGraph • Groq • Qdrant RAG • Python MCP
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255, 255, 255, 0.04)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => setActiveTab('studio')}
              className="btn-secondary"
              style={{
                background: activeTab === 'studio' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                borderColor: activeTab === 'studio' ? 'var(--accent-cyan)' : 'transparent',
                color: activeTab === 'studio' ? 'var(--accent-cyan)' : 'var(--text-muted)',
              }}
            >
              <Code2 size={16} /> Debug Studio
            </button>
            <button
              onClick={() => setActiveTab('knowledge')}
              className="btn-secondary"
              style={{
                background: activeTab === 'knowledge' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                borderColor: activeTab === 'knowledge' ? 'var(--accent-cyan)' : 'transparent',
                color: activeTab === 'knowledge' ? 'var(--accent-cyan)' : 'var(--text-muted)',
              }}
            >
              <Database size={16} /> Knowledge Base ({health?.services?.qdrant?.total_records || knowledgeItems.length || '35+'})
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className="btn-secondary"
              style={{
                background: activeTab === 'history' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                borderColor: activeTab === 'history' ? 'var(--accent-cyan)' : 'transparent',
                color: activeTab === 'history' ? 'var(--accent-cyan)' : 'var(--text-muted)',
              }}
            >
              <History size={16} /> History ({historyItems.length})
            </button>
          </div>

          {/* Status & Connection Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              className={`badge ${health?.status === 'healthy' ? 'badge-green' : 'badge-red'}`}
              style={{ padding: '6px 12px' }}
            >
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: health?.status === 'healthy' ? '#10b981' : '#ef4444',
                  boxShadow: health?.status === 'healthy' ? '0 0 8px #10b981' : 'none',
                }}
              />
              {health?.status === 'healthy' ? 'Backend Online' : 'Backend Disconnected'}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, maxWidth: '1400px', width: '100%', margin: '0 auto', padding: '24px 20px' }}>
        {apiError && (
          <div
            className="glass-panel"
            style={{
              borderColor: 'rgba(239, 68, 68, 0.4)',
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              padding: '14px 18px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              color: '#fca5a5',
            }}
          >
            <AlertTriangle size={20} color="#ef4444" />
            <span style={{ fontSize: '14px' }}>{apiError}</span>
          </div>
        )}

        {/* TAB 1: DEBUG STUDIO */}
        {activeTab === 'studio' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))', gap: '24px' }}>
            
            {/* Left Side: Code & Error Input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              
              {/* Presets & File Upload toolbar */}
              <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={16} color="var(--accent-cyan)" />
                  <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-muted)' }}>Load Example:</span>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {SAMPLE_BUGS.map((sample, idx) => (
                      <button
                        key={idx}
                        className="btn-secondary"
                        style={{ fontSize: '11px', padding: '4px 8px' }}
                        onClick={() => {
                          setCode(sample.code);
                          setErrorMessage(sample.error);
                          setDebugResult(null);
                        }}
                      >
                        {sample.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Upload .py file */}
                <label className="btn-secondary" style={{ cursor: 'pointer', fontSize: '12px' }}>
                  <Upload size={14} />
                  <span>Upload .py</span>
                  <input
                    type="file"
                    accept=".py"
                    style={{ display: 'none' }}
                    onChange={handleFileUpload}
                  />
                </label>
              </div>

              {/* Code Input Area */}
              <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Code2 size={16} color="var(--accent-cyan)" />
                    <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)' }}>
                      Python Source Code
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                    Python 3.12+ AST validated
                  </span>
                </div>
                <textarea
                  className="code-editor"
                  rows={13}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Paste buggy Python code here..."
                  style={{ width: '100%' }}
                />
              </div>

              {/* Error / Traceback Input Area */}
              <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Terminal size={16} color="#f87171" />
                    <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)' }}>
                      Error Traceback / Message (Optional)
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                    Parsed with MCP read_error_log
                  </span>
                </div>
                <textarea
                  className="code-editor"
                  rows={6}
                  value={errorMessage}
                  onChange={(e) => setErrorMessage(e.target.value)}
                  placeholder="Paste Python traceback or console error log here (optional)..."
                  style={{ width: '100%', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                />
              </div>

              {/* Run Button & Loading Stepper */}
              <div>
                <button
                  className="btn-primary"
                  onClick={handleDebug}
                  disabled={isLoading}
                  style={{ width: '100%', padding: '14px', fontSize: '15px' }}
                >
                  {isLoading ? (
                    <>
                      <RefreshCw size={18} className="spin-slow" />
                      <span>{currentStep || 'Debugging with Multi-Agent Pipeline...'}</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} />
                      <span>Analyze & Fix with DevFix Multi-Agent</span>
                    </>
                  )}
                </button>
              </div>

            </div>

            {/* Right Side: Multi-Agent Analysis, Solutions & Validation */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              
              {!debugResult && !isLoading && (
                <div
                  className="glass-panel"
                  style={{
                    padding: '48px 24px',
                    textAlign: 'center',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '16px',
                    minHeight: '400px',
                  }}
                >
                  <div
                    style={{
                      width: '60px',
                      height: '60px',
                      borderRadius: '16px',
                      background: 'rgba(56, 189, 248, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <Cpu size={30} color="var(--accent-cyan)" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '17px', fontWeight: '600', color: '#fff', marginBottom: '6px' }}>
                      Multi-Agent Debugging Engine Ready
                    </h3>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '420px', lineHeight: 1.6 }}>
                      Load an example or paste your code on the left. DevFix orchestrates Error Analysis, Qdrant RAG, and Sandboxed MCP Testing to deliver verified fixes.
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                    <span className="badge badge-blue">1. Error Analysis</span>
                    <span className="badge badge-purple">2. RAG Retrieval</span>
                    <span className="badge badge-green">3. Sandbox Validation</span>
                  </div>
                </div>
              )}

              {isLoading && (
                <div
                  className="glass-panel animate-pulse-glow"
                  style={{
                    padding: '40px 24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px',
                    minHeight: '400px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <RefreshCw size={24} className="spin-slow" color="var(--accent-cyan)" />
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#fff' }}>
                        Autonomous Agent Orchestration in Progress
                      </h3>
                      <p style={{ fontSize: '13px', color: 'var(--accent-cyan)' }}>{currentStep}</p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.03)' }}>
                      <CheckCircle2 size={16} color="#38bdf8" />
                      <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Agent 1: Inspecting code AST & traceback frames via MCP tools</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.03)' }}>
                      <Database size={16} color="#a855f7" />
                      <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Agent 2: Embedding query and retrieving similar cases from Qdrant</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '12px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.03)' }}>
                      <ShieldCheck size={16} color="#10b981" />
                      <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Agent 3: Generating fix and executing sandboxed tests with timeout</span>
                    </div>
                  </div>
                </div>
              )}

              {debugResult && !isLoading && (
                <>
                  {/* Agent Telemetry & Diagnostics Card */}
                  <div className="glass-panel" style={{ padding: '18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge badge-red" style={{ fontSize: '13px' }}>
                          {debugResult.error_type || 'Error Detected'}
                        </span>
                        {debugResult.error_line && (
                          <span className="badge badge-amber" style={{ fontSize: '12px' }}>
                            Line {debugResult.error_line}
                          </span>
                        )}
                      </div>

                      {/* MCP Call Badges */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>MCP Tools:</span>
                        {(debugResult.mcp_calls_made || []).map((tool, i) => (
                          <span key={i} className="badge badge-blue" style={{ fontSize: '10px', padding: '2px 6px' }}>
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginBottom: '12px' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#e2e8f0', marginBottom: '4px' }}>
                        Root Cause Diagnosis
                      </h4>
                      <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                        {debugResult.root_cause || 'Identified runtime logic anomaly.'}
                      </p>
                    </div>

                    {debugResult.hypotheses?.length > 0 && (
                      <div style={{ marginTop: '8px' }}>
                        <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-dim)' }}>Contributing Factors:</span>
                        <ul style={{ paddingLeft: '18px', marginTop: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                          {debugResult.hypotheses.map((h, i) => (
                            <li key={i}>{h}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Proposed Corrected Code */}
                  <div className="glass-panel" style={{ padding: '18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileCode2 size={16} color="var(--accent-cyan)" />
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
                          Suggested Corrected Code
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          className="btn-secondary"
                          onClick={() => setCode(debugResult.corrected_code)}
                          title="Apply this fix to the editor"
                        >
                          Apply to Editor
                        </button>
                        <button
                          className="btn-secondary"
                          onClick={() => handleCopyCode(debugResult.corrected_code)}
                        >
                          {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                          <span>{copied ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                    </div>

                    <pre
                      className="code-font"
                      style={{
                        backgroundColor: 'var(--bg-input)',
                        padding: '14px',
                        borderRadius: '8px',
                        fontSize: '13px',
                        lineHeight: 1.6,
                        overflowX: 'auto',
                        border: '1px solid var(--border-subtle)',
                        color: '#93c5fd',
                      }}
                    >
                      <code>{debugResult.corrected_code}</code>
                    </pre>

                    {debugResult.explanation && (
                      <div style={{ marginTop: '12px', fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        <strong style={{ color: '#cbd5e1' }}>Explanation: </strong>
                        {debugResult.explanation}
                      </div>
                    )}
                  </div>

                  {/* Sandboxed Test Validation Outcome */}
                  <div className="glass-panel" style={{ padding: '18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <ShieldCheck size={18} color="var(--accent-green)" />
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
                          Sandboxed Test Validation (MCP run_tests)
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {debugResult.validation_result?.passed ? (
                          <span className="badge badge-green">
                            <CheckCircle2 size={13} /> Tests Passed
                          </span>
                        ) : (
                          <span className="badge badge-red">
                            <XCircle size={13} /> {debugResult.validation_result?.status?.toUpperCase() || 'FAILED'}
                          </span>
                        )}
                        {debugResult.validation_result?.duration_ms && (
                          <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                            {debugResult.validation_result.duration_ms} ms
                          </span>
                        )}
                      </div>
                    </div>

                    {debugResult.test_code && (
                      <div style={{ marginTop: '8px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Verification Assertions Executed:</span>
                        <pre
                          className="code-font"
                          style={{
                            backgroundColor: '#090d15',
                            padding: '10px 12px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            marginTop: '4px',
                            overflowX: 'auto',
                            color: '#a7f3d0',
                          }}
                        >
                          <code>{debugResult.test_code}</code>
                        </pre>
                      </div>
                    )}

                    {debugResult.validation_result?.stderr && (
                      <div style={{ marginTop: '10px', padding: '10px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                        <span style={{ fontSize: '11px', color: '#f87171', fontWeight: '600' }}>Sandbox Output / Traceback:</span>
                        <pre className="code-font" style={{ fontSize: '11px', color: '#fca5a5', marginTop: '4px', whiteSpace: 'pre-wrap' }}>
                          {debugResult.validation_result.stderr}
                        </pre>
                      </div>
                    )}
                  </div>

                  {/* RAG Retrieved Source References */}
                  {debugResult.rag_references?.length > 0 && (
                    <div className="glass-panel" style={{ padding: '18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                        <Database size={16} color="var(--accent-purple)" />
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
                          Qdrant RAG Verified Knowledge Citations
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {debugResult.rag_references.map((ref, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '12px 14px',
                              borderRadius: '8px',
                              backgroundColor: 'rgba(255, 255, 255, 0.02)',
                              border: '1px solid var(--border-subtle)',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ fontSize: '13px', fontWeight: '600', color: '#c084fc' }}>
                                {ref.title || ref.error_type}
                              </span>
                              <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                                Match: {Math.round((ref.score || 0.8) * 100)}%
                              </span>
                            </div>
                            <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                              {ref.root_cause || ref.snippet}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Explicit Opt-in: Save to Knowledge Base Button */}
                  <div
                    className="glass-panel"
                    style={{
                      padding: '16px 20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '12px',
                      borderColor: savedSuccess ? 'rgba(16, 185, 129, 0.4)' : 'var(--border-subtle)',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <BookmarkPlus size={16} color={savedSuccess ? '#10b981' : 'var(--accent-cyan)'} />
                        <span style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
                          Save Verified Solution to Knowledge Base?
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        Opt-in only. Automatic privacy sanitizer scrubs API keys, passwords, and sensitive tokens.
                      </p>
                    </div>

                    <button
                      className="btn-secondary"
                      onClick={handleSaveToKnowledge}
                      disabled={savedSuccess}
                      style={{
                        background: savedSuccess ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.1)',
                        borderColor: savedSuccess ? '#10b981' : 'var(--accent-cyan)',
                        color: savedSuccess ? '#34d399' : 'var(--accent-cyan)',
                      }}
                    >
                      {savedSuccess ? (
                        <>
                          <Check size={14} /> Saved to Qdrant
                        </>
                      ) : (
                        <>
                          <BookmarkPlus size={14} /> Add to RAG Knowledge
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: KNOWLEDGE BASE VIEW */}
        {activeTab === 'knowledge' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Database size={20} color="var(--accent-purple)" />
                  Qdrant Vector Knowledge Base
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Total verified debugging cases indexed: <strong>{knowledgeItems.length}</strong> (Local embedded Qdrant instance)
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="text"
                  placeholder="Search error types, causes, tags..."
                  value={knowledgeSearch}
                  onChange={(e) => setKnowledgeSearch(e.target.value)}
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '8px 14px',
                    color: '#fff',
                    fontSize: '13px',
                    width: '280px',
                    outline: 'none',
                  }}
                />
                <button
                  className="btn-secondary"
                  onClick={() => {
                    fetchKnowledge();
                    fetchHealth();
                  }}
                >
                  <RefreshCw size={14} /> Refresh
                </button>
              </div>
            </div>

            {/* Knowledge Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '16px' }}>
              {filteredKnowledge.map((item, idx) => (
                <div key={idx} className="glass-panel" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="badge badge-purple" style={{ fontSize: '11px' }}>
                      {item.error_type}
                    </span>
                    <span className="badge badge-blue" style={{ fontSize: '10px' }}>
                      {item.category || 'Python'}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '15px', fontWeight: '600', color: '#f1f5f9' }}>
                    {item.title}
                  </h3>

                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, flex: 1 }}>
                    {item.root_cause}
                  </p>

                  {item.corrected_code && (
                    <div style={{ marginTop: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Verified Fix:</span>
                      <pre
                        className="code-font"
                        style={{
                          backgroundColor: '#090d15',
                          padding: '8px 10px',
                          borderRadius: '6px',
                          fontSize: '11.5px',
                          marginTop: '4px',
                          overflowX: 'auto',
                          maxHeight: '120px',
                          color: '#93c5fd',
                        }}
                      >
                        <code>{item.corrected_code}</code>
                      </pre>
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                    <button
                      className="btn-secondary"
                      style={{ fontSize: '11px', padding: '4px 10px' }}
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

        {/* TAB 3: HISTORY LOG */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div className="glass-panel" style={{ padding: '18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <History size={20} color="var(--accent-cyan)" />
                  Debugging Session History
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Sessions are maintained separately from the reusable RAG knowledge base.
                </p>
              </div>

              {historyItems.length > 0 && (
                <button className="btn-secondary" onClick={handleClearHistory} style={{ color: '#f87171' }}>
                  <Trash2 size={14} /> Clear History
                </button>
              )}
            </div>

            {historyItems.length === 0 ? (
              <div className="glass-panel" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
                No debugging sessions recorded yet. Run a session in the Debug Studio!
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {historyItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="glass-panel"
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
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          backgroundColor: item.validation_result?.passed ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {item.validation_result?.passed ? (
                          <CheckCircle2 size={18} color="#10b981" />
                        ) : (
                          <XCircle size={18} color="#ef4444" />
                        )}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
                            {item.error_type || 'Python Issue'}
                          </span>
                          <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                            {item.status}
                          </span>
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {item.summary || item.root_cause || 'Debugging session'}
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} />
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                      <button
                        className="btn-secondary"
                        style={{ fontSize: '12px' }}
                        onClick={() => {
                          setCode(item.code);
                          setErrorMessage(item.error_message || '');
                          setDebugResult(item);
                          setActiveTab('studio');
                        }}
                      >
                        Inspect in Studio <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle)',
          padding: '16px 24px',
          textAlign: 'center',
          fontSize: '12px',
          color: 'var(--text-dim)',
          backgroundColor: 'rgba(7, 9, 14, 0.95)',
        }}
      >
        DevFix AI • Multi-Agent Autonomous Python Debugger • Powered by LangGraph, Groq, Qdrant & MCP
      </footer>
    </div>
  );
}
