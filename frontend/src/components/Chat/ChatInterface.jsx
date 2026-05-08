import React, { useState, useRef, useEffect } from 'react';
import { useChatQuery } from '../../hooks/useApi';
import { Send, Bot, Clock, ChevronDown, ChevronUp, FileText, Sparkles, User, Fingerprint } from 'lucide-react';

export default function ChatInterface({ onPlayTimestamp }) {
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', text: "Neural Link established. I'm your Novara assistant. Upload documents or media to begin analysis." }
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const [expandedSources, setExpandedSources] = useState({});
  
  const chatMutation = useChatQuery();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, chatMutation.isPending]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || chatMutation.isPending) return;

    const userMessage = { id: Date.now(), role: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const response = await chatMutation.mutateAsync(userMessage.text);
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        role: 'assistant', 
        text: response.answer,
        sources: response.sources
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        role: 'assistant', 
        text: error.message || "Sorry, I encountered an error while trying to answer that." 
      }]);
    }
  };

  const toggleSource = (msgId, srcIdx) => {
    const key = `${msgId}-${srcIdx}`;
    setExpandedSources(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const getConfidenceLabel = (score) => {
    if (score >= 0.8) return "Strong Match";
    if (score >= 0.6) return "Related Context";
    return "Partial Match";
  };

  return (
    <div className="flex flex-col h-full bg-transparent relative">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 md:p-12 space-y-10 scrollbar-thin pb-40">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-6 max-w-3xl mx-auto ${msg.role === 'user' ? 'flex-row-reverse' : ''} animate-fade-in-up`}>
            
            {/* Avatar Section */}
            <div className="shrink-0 flex flex-col items-center gap-2">
              <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shadow-2xl transition-all duration-500 ${
                msg.role === 'user' 
                  ? 'bg-gradient-to-br from-indigo-500 to-blue-600 border border-white/20' 
                  : 'bg-[#1e293b] border border-indigo-500/30'
              }`}>
                {msg.role === 'user' ? <Fingerprint size={20} className="text-white" /> : <Bot size={20} className="text-indigo-400" />}
              </div>
              <span className="text-[8px] font-black uppercase tracking-[0.2em] text-gray-600">
                {msg.role === 'user' ? 'Client' : 'Nexus'}
              </span>
            </div>
            
            <div className={`max-w-[85%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`px-6 py-4 text-[14px] leading-relaxed relative group ${
                msg.role === 'user' 
                  ? 'chat-bubble-user' 
                  : 'chat-bubble-ai'
              }`}>
                {msg.role === 'assistant' && (
                  <div className="absolute -top-1 -left-1">
                    <Sparkles size={12} className="text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                )}
                <p className="whitespace-pre-wrap font-medium">{msg.text}</p>
              </div>
              
              {/* Sources Section */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-5 w-full space-y-3">
                  <div className="flex items-center gap-3 px-1">
                    <div className="h-px flex-1 bg-gradient-to-r from-indigo-500/20 to-transparent"></div>
                    <span className="text-[9px] font-black text-indigo-400/60 uppercase tracking-[0.3em]">Knowledge Fragments</span>
                    <div className="h-px flex-1 bg-gradient-to-l from-indigo-500/20 to-transparent"></div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {msg.sources.map((src, idx) => {
                      const key = `${msg.id}-${idx}`;
                      const isExpanded = expandedSources[key];
                      return (
                        <div key={idx} className="glass-card rounded-[1.2rem] overflow-hidden group/src">
                          <div 
                            className="p-3.5 flex justify-between items-center cursor-pointer hover:bg-white/[0.02] transition-colors"
                            onClick={() => toggleSource(msg.id, idx)}
                          >
                            <div className="flex items-center gap-3 truncate">
                              <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                                <FileText size={14} className="text-indigo-400" />
                              </div>
                              <div className="flex flex-col truncate">
                                <span className="font-bold text-gray-200 text-xs truncate max-w-[120px]">{src.source}</span>
                                <span className="text-[9px] text-indigo-400/70 font-black uppercase">{getConfidenceLabel(src.score)}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {src.timestamp && onPlayTimestamp && (
                                <button 
                                  onClick={(e) => { e.stopPropagation(); onPlayTimestamp(src.timestamp); }}
                                  className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-all text-[10px] font-bold border border-indigo-500/10"
                                >
                                  <Clock size={10} />
                                  <span>{Math.floor(parseFloat(src.timestamp) || 0)}s</span>
                                </button>
                              )}
                              {isExpanded ? <ChevronUp size={16} className="text-gray-600" /> : <ChevronDown size={16} className="text-gray-600" />}
                            </div>
                          </div>
                          {isExpanded && (
                            <div className="p-4 pt-0">
                              <div className="p-3 rounded-xl bg-black/40 border border-white/5 text-[12px] text-gray-400 italic leading-relaxed">
                                "{src.text}"
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {chatMutation.isPending && (
          <div className="flex gap-6 max-w-3xl mx-auto animate-fade-in-up">
            <div className="shrink-0 flex flex-col items-center gap-2">
              <div className="w-10 h-10 rounded-2xl bg-[#1e293b] border border-indigo-500/30 flex items-center justify-center shadow-2xl">
                <Bot size={20} className="text-indigo-400" />
              </div>
            </div>
            <div className="chat-bubble-ai px-8 py-5 flex items-center gap-2">
              <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} className="h-10" />
      </div>

      {/* Input Terminal Area */}
      <div className="absolute bottom-0 left-0 right-0 p-8 pt-0 z-20 pointer-events-none">
        <div className="max-w-3xl mx-auto pointer-events-auto relative">
          <div className="absolute inset-0 bg-[#020617]/80 backdrop-blur-2xl -m-4 rounded-[3rem] pointer-events-none opacity-0 group-focus-within:opacity-100 transition-opacity"></div>
          
          <form onSubmit={handleSubmit} className="relative group">
            {/* Input Glow */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-500 rounded-3xl blur opacity-20 group-focus-within:opacity-40 transition duration-1000"></div>
            
            <div className="relative flex items-center bg-[#111827]/80 backdrop-blur-3xl border border-white/10 rounded-[1.8rem] shadow-2xl overflow-hidden transition-all duration-500 focus-within:border-indigo-500/50">
              <div className="pl-6 text-indigo-500/50">
                <Sparkles size={20} />
              </div>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Submit query to neural link..."
                className="w-full bg-transparent text-[#F8F9FA] rounded-[1.8rem] py-6 px-5 focus:outline-none placeholder-gray-600 font-medium text-sm"
                disabled={chatMutation.isPending}
              />
              <div className="pr-3 flex items-center gap-3">
                <button
                  type="submit"
                  disabled={!input.trim() || chatMutation.isPending}
                  className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-600 to-blue-700 text-white hover:scale-105 active:scale-95 disabled:opacity-30 disabled:grayscale transition-all shadow-xl flex items-center justify-center group/send"
                >
                  <Send size={18} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
