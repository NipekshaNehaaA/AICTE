'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  X,
  Send,
  BookOpen,
  ShieldAlert,
  ChevronRight,
  RotateCcw,
  Bot,
  User as UserIcon,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { useApp } from '@/lib/app-context';
import { apiFetch } from '@/lib/api';

interface Citation {
  clause: string;
  page: string;
  topic: string;
}

interface Message {
  id: string;
  sender: 'user' | 'copilot';
  text: string;
  citations?: Citation[];
  confidence?: number;
  followups?: string[];
  timestamp: string;
}

export const ComplianceCopilotDrawer: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestedPrompts, setSuggestedPrompts] = useState<any[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-msg',
      sender: 'copilot',
      text: (
        "Namaste! I am the **AICTE Institutional Compliance & APH Copilot**.\n\n" +
        "I provide grounded regulatory guidance based on the official **Approval Process Handbook (APH 2024-25 to 2026-27)**.\n\n" +
        "Ask me about scrutiny deficiencies, land lease validity, EVC committee requirements, working-day holiday SLAs, or click one of the statutory prompts below."
      ),
      citations: [
        { clause: "APH 2024-27", page: "1-231", topic: "Handbook Regulations" },
        { clause: "Table 2.3", page: "30", topic: "Processing Stages" },
      ],
      confidence: 0.98,
      followups: [
        "What is the statutory cure window if scrutiny notes deficiencies?",
        "What are the land lease deed requirements for approval?",
        "What are the mandatory qualifications for EVC committee inspectors?"
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const { currentUser } = useApp();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch suggested prompts on mount
  useEffect(() => {
    apiFetch<{ suggested_prompts: string[] }>('/api/v1/copilot/suggested-prompts')
      .then((data) => {
        if (data?.suggested_prompts) {
          setSuggestedPrompts(data.suggested_prompts);
        }
      })
      .catch((err) => console.log('Copilot prompt fetch error', err));
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputMessage;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputMessage('');
    setLoading(true);

    try {
      const data = await apiFetch<any>('/api/v1/copilot/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: textToSend.trim(),
        }),
      });
      const botMsg: Message = {
        id: `bot-${Date.now()}`,
        sender: 'copilot',
        text: data.answer_markdown,
        citations: data.citations,
        confidence: data.confidence_score,
        followups: data.suggested_followups,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: `bot-err-${Date.now()}`,
        sender: 'copilot',
        text: "I encountered a connection error reaching the APH knowledge service. Please ensure the backend is running on port 8000.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Launcher Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 px-4 py-3 rounded-full bg-blossom-600 text-white font-semibold text-xs shadow-lg hover:bg-blossom-700 hover:shadow-xl transition-all transform hover:-translate-y-0.5"
        title="Open AICTE Institutional Compliance & APH Copilot"
      >
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-mint-100"></span>
        </span>
        <Sparkles className="w-4 h-4 text-ivory" />
        <span className="tracking-wide">AICTE Copilot & APH Help</span>
      </button>

      {/* Slide-over Drawer Panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-ink-strong/30 backdrop-blur-sm animate-fade-in flex justify-end">
          <div className="w-full max-w-lg bg-white h-screen max-h-screen shadow-2xl flex flex-col border-l border-ink-line overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-ink-line bg-gradient-to-r from-blossom-100/50 to-white flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-blossom-600 text-white flex items-center justify-center shadow-soft">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-bold text-ink-strong">
                      AICTE Compliance & APH Copilot
                    </h2>
                    <span className="bg-blossom-100 text-blossom-700 text-[10px] font-bold px-2 py-0.5 rounded border border-blossom-300">
                      SUGGEST-ONLY
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-muted">
                    Grounded in APH 2024-25 to 2026-27 & Live Records
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={() =>
                    setMessages([
                      {
                        id: 'reset-msg',
                        sender: 'copilot',
                        text: "Chat cleared. What statutory APH topic can I clarify for you?",
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                      },
                    ])
                  }
                  className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-slate-100 transition-colors"
                  title="Reset conversation"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-slate-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Mandatory Statutory Safeguard Notice */}
            <div className="bg-amberState-100/60 border-b border-amberState-700/20 px-4 py-2 flex items-start gap-2 text-[11px] text-amberState-700 shrink-0">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-amberState-700" />
              <span>
                <strong>Statutory Safeguard:</strong> AI advisory draft (SUGGEST-ONLY). Answers support regulatory understanding; official decisions remain with the Competent Authority.
              </span>
            </div>

            {/* Suggested Prompts Quick Carousel */}
            {suggestedPrompts.length > 0 && (
              <div className="p-3 border-b border-ink-line bg-[#FAFAFA] space-y-1.5 shrink-0">
                <div className="text-[10px] font-bold uppercase tracking-wider text-ink-muted flex items-center gap-1">
                  <HelpCircle className="w-3 h-3 text-blossom-600" />
                  <span>Quick Statutory Inquiries</span>
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
                  {suggestedPrompts.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => handleSendMessage(p.query)}
                      className="shrink-0 text-[11px] bg-white border border-ink-line rounded-lg px-2.5 py-1 text-ink-strong hover:border-blossom-600 hover:text-blossom-700 transition-all shadow-xs flex items-center gap-1.5"
                    >
                      <span>{p.label}</span>
                      <ChevronRight className="w-3 h-3 text-ink-muted" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Thread */}
            <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${
                    msg.sender === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {msg.sender === 'copilot' && (
                    <div className="w-7 h-7 rounded-lg bg-blossom-100 border border-blossom-300 text-blossom-700 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-xl p-3.5 text-xs leading-relaxed space-y-2 shadow-xs ${
                      msg.sender === 'user'
                        ? 'bg-ink-strong !text-white rounded-br-none'
                        : 'bg-white border border-ink-line border-l-4 border-l-blossom-300 rounded-bl-none text-ink'
                    }`}
                  >
                    {/* Bot Banner Chip */}
                    {msg.sender === 'copilot' && (
                      <div className="flex items-center justify-between text-[10px] pb-1 border-b border-slate-100">
                        <span className="font-bold text-blossom-700 flex items-center gap-1">
                          <BookOpen className="w-3 h-3" />
                          APH 2024-27 Verified
                        </span>
                        {msg.confidence && (
                          <span className="text-mint-700 font-semibold bg-mint-100 px-1.5 py-0.2 rounded">
                            {Math.round(msg.confidence * 100)}% Grounded
                          </span>
                        )}
                      </div>
                    )}

                    {/* Message Body */}
                    <div className={`whitespace-pre-wrap font-sans text-xs ${msg.sender === 'user' ? '!text-white font-medium' : 'text-ink'}`}>
                      {msg.text}
                    </div>

                    {/* Citations Pill List */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-2 border-t border-slate-100 space-y-1">
                        <div className="text-[10px] font-bold text-ink-muted uppercase">
                          Statutory Citations:
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.citations.map((c, i) => (
                            <span
                              key={i}
                              className="text-[10px] font-mono bg-blossom-100/70 border border-blossom-300/80 text-blossom-700 px-2 py-0.5 rounded flex items-center gap-1"
                              title={`${c.topic} (Page ${c.page})`}
                            >
                              <span>{c.clause}</span>
                              <span className="text-ink-muted">p.{c.page}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Suggested Followups */}
                    {msg.followups && msg.followups.length > 0 && (
                      <div className="pt-2 border-t border-slate-100 space-y-1">
                        <div className="text-[10px] font-bold text-ink-muted">
                          Suggested Next Inquiries:
                        </div>
                        <div className="space-y-1">
                          {msg.followups.map((f, i) => (
                            <button
                              key={i}
                              onClick={() => handleSendMessage(f)}
                              className="w-full text-left text-[11px] text-blossom-700 hover:bg-blossom-100/50 p-1.5 rounded transition-colors flex items-center justify-between group"
                            >
                              <span className="truncate">{f}</span>
                              <ChevronRight className="w-3 h-3 text-blossom-600 opacity-60 group-hover:opacity-100" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className={`text-[9px] text-right pt-0.5 ${msg.sender === 'user' ? 'text-slate-300' : 'text-ink-muted'}`}>
                      {msg.timestamp}
                    </div>
                  </div>

                  {msg.sender === 'user' && (
                    <div className="w-7 h-7 rounded-lg bg-blossom-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                      <UserIcon className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-2 text-xs text-ink-muted p-2 bg-blossom-100/40 rounded-lg animate-pulse w-fit">
                  <Sparkles className="w-4 h-4 text-blossom-600 animate-spin" />
                  <span>Searching APH 2024–27 statutory rules & records...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar - Always Pinned at Bottom */}
            <div className="p-3 border-t border-ink-line bg-white shrink-0 shadow-lg z-20">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask a doubt regarding APH 2024-27 (e.g. lease, deficiency)..."
                  className="flex-1 text-xs border border-ink-line rounded-xl px-3 py-2.5 focus:outline-none focus:border-blossom-600 focus:ring-1 focus:ring-blossom-600 bg-[#FAFAFA] text-ink-strong placeholder:text-ink-muted shadow-xs"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !inputMessage.trim()}
                  className="p-2.5 rounded-xl bg-blossom-600 text-white hover:bg-blossom-700 disabled:opacity-50 transition-colors shadow-soft shrink-0"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
              <div className="text-[10px] text-ink-muted text-center mt-1.5 font-medium">
                AICTE APH 2024–27 Edition • AI output strictly SUGGEST-ONLY
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
