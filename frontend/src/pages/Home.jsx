import React, { useState } from 'react';
import UploadForm from '../components/Upload/UploadForm';
import ChatInterface from '../components/Chat/ChatInterface';
import MediaPlayer from '../components/MediaPlayer/MediaPlayer';
import SummaryView from '../components/Summary/SummaryView';
import SettingsModal from '../components/Settings/SettingsModal';
import { Sparkles, Library, PlayCircle, FileText, Zap, RotateCcw, Cpu, Settings } from 'lucide-react';
import { resetApp } from '../services/api';

export default function Home() {
  const [activeMediaUrl, setActiveMediaUrl] = useState(null);
  const [seekTimestamp, setSeekTimestamp] = useState(null);
  const [lastUploadedFile, setLastUploadedFile] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleUploadSuccess = ({ file, type }) => {
    setLastUploadedFile(file.name);
    if (type === 'media') {
      const url = URL.createObjectURL(file);
      setActiveMediaUrl(url);
    }
  };

  const handleRestart = async () => {
    if (window.confirm('Are you sure you want to restart? This will clear all documents and chat history.')) {
      try {
        await resetApp();
        setLastUploadedFile(null);
        setActiveMediaUrl(null);
        setSeekTimestamp(null);
        window.location.reload();
      } catch (error) {
        console.error('Failed to reset app:', error);
      }
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#020617] text-[#F8F9FA] overflow-hidden relative font-sans">
      {/* Immersive Background Layer - Simplified */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-5%] w-[50%] h-[50%] rounded-full bg-indigo-600/10 blur-[140px] animate-blob"></div>
        <div className="absolute bottom-[-10%] right-[-5%] w-[50%] h-[50%] rounded-full bg-purple-600/10 blur-[140px] animate-blob animation-delay-2000"></div>
        <div className="absolute top-[30%] right-[10%] w-[30%] h-[30%] rounded-full bg-blue-600/5 blur-[120px] animate-blob animation-delay-4000"></div>
      </div>

      {/* 1. Universal Top Navigation Bar */}
      <nav className="h-16 border-b border-white/5 glass-panel flex items-center justify-between px-8 z-30 shrink-0 relative">
        <div className="flex items-center gap-5 group cursor-pointer">
          <div className="relative">
            <div className="absolute -inset-2 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-xl blur opacity-20 group-hover:opacity-50 transition duration-1000"></div>
            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-700 flex items-center justify-center shadow-2xl">
              <Cpu className="text-white" size={20} />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
              Novara <span className="text-gradient">AI</span>
            </h1>
            <p className="text-[9px] text-gray-500 font-bold uppercase tracking-[0.2em] -mt-1">Neural Intelligence Hub</p>
          </div>
        </div>

        {/* Settings Button */}
        <button
          onClick={() => setIsSettingsOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-gray-300 hover:text-white transition-all group"
        >
          <Settings size={16} className="group-hover:rotate-90 transition-transform duration-500" />
          <span className="text-xs font-medium">Settings</span>
        </button>
      </nav>

      {/* 2. Main Content Wrapper */}
      <div className="flex flex-1 overflow-hidden relative z-10">

        {/* Left Sidebar (Knowledge Base) */}
        <aside className="w-[340px] border-r border-white/5 bg-[#030712]/40 backdrop-blur-md flex flex-col hidden lg:flex shrink-0 z-20 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-10 scrollbar-thin">

            {/* Knowledge Base Section */}
            <section className="animate-fade-in-up">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.25em] flex items-center gap-2.5">
                  <Library size={14} className="text-indigo-500" /> Knowledge Source
                </h2>
              </div>
              <div className="glass-card rounded-[1.5rem] p-1 shadow-2xl">
                <div className="bg-[#0f172a]/40 rounded-[1.3rem] p-5 border border-white/5">
                  <UploadForm onUploadSuccess={handleUploadSuccess} />
                </div>
              </div>
            </section>

            {/* Document Insights Section */}
            {lastUploadedFile && (
              <section className="animate-fade-in-up" style={{ animationDelay: '150ms' }}>
                <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.25em] mb-5 flex items-center gap-2.5">
                  <FileText size={14} className="text-purple-500" /> Semantic Insights
                </h2>
                <div className="glass-card rounded-[1.5rem] overflow-hidden border border-white/5">
                  <SummaryView filename={lastUploadedFile} />
                </div>
              </section>
            )}

            {/* Media Analysis Section */}
            {activeMediaUrl && (
              <section className="animate-fade-in-up" style={{ animationDelay: '300ms' }}>
                <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.25em] mb-5 flex items-center gap-2.5">
                  <PlayCircle size={14} className="text-cyan-500" /> Neural Media Feed
                </h2>
                <div className="glass-card rounded-[1.5rem] overflow-hidden border border-white/5 shadow-indigo-500/5">
                  <MediaPlayer
                    mediaUrl={activeMediaUrl}
                    seekTimestamp={seekTimestamp}
                  />
                </div>
              </section>
            )}
          </div>

          {/* Sidebar Footer */}
          <div className="p-6 border-t border-white/5 bg-[#030712]/60 space-y-5">
            <button
              onClick={handleRestart}
              className="w-full flex items-center justify-center gap-3 px-4 py-3.5 rounded-2xl bg-rose-500/5 hover:bg-rose-500/15 text-rose-400 border border-rose-500/10 hover:border-rose-500/30 transition-all text-[10px] font-black uppercase tracking-[0.2em] group"
            >
              <RotateCcw size={14} className="group-hover:rotate-[-90deg] transition-transform duration-500" />
              <span>Purge Session</span>
            </button>

            <div className="flex items-center justify-between px-2">
              <div className="flex items-center gap-2 text-[9px] text-gray-500 font-black uppercase tracking-widest">
                <Zap size={12} className="text-amber-500" />
                <span>Syncing...</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                <span className="text-[9px] text-gray-400 font-bold">STABLE</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Chat Interface */}
        <main className="flex-1 flex flex-col min-w-0 bg-transparent relative z-10 overflow-hidden">
          <div className="flex-1 overflow-hidden relative">
            <ChatInterface onPlayTimestamp={setSeekTimestamp} />
          </div>

          {/* Agency Branding */}
          <div className="absolute bottom-4 right-6 z-30 pointer-events-none flex items-center gap-1.5 opacity-60">
            <span className="text-[9px] text-gray-500 font-bold tracking-[0.2em] uppercase">Built by</span>
            <span className="text-[10px] font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 tracking-[0.2em] uppercase">Anovation</span>
          </div>
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </div>
  );
}
