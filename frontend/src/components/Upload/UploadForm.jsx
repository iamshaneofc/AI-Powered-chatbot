import React, { useState } from 'react';
import { useUploadDocument, useUploadMedia } from '../../hooks/useApi';
import { UploadCloud, FileText, Film, CheckCircle, AlertCircle, FileAudio, File as FileIcon, X } from 'lucide-react';

export default function UploadForm({ onUploadSuccess }) {
  const [activeTab, setActiveTab] = useState('document'); // 'document' or 'media'
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // 'idle', 'uploading', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('');

  const docUpload = useUploadDocument();
  const mediaUpload = useUploadMedia();

  const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    const isMedia = ['mp3', 'mp4', 'wav', 'm4a', 'webm'].includes(ext);
    const isDoc = ['pdf', 'txt', 'docx'].includes(ext);

    if (activeTab === 'document' && !isDoc) {
      setUploadStatus('error');
      setErrorMessage('Please select a valid document (PDF, TXT, DOCX)');
      return;
    }
    if (activeTab === 'media' && !isMedia) {
      setUploadStatus('error');
      setErrorMessage('Please select a valid media file (MP3, MP4, WAV, etc.)');
      return;
    }

    setSelectedFile(file);
    setUploadStatus('idle');
    setErrorMessage('');
  };

  const submitUpload = async () => {
    if (!selectedFile) return;
    
    setUploadStatus('uploading');
    
    try {
      let data;
      if (activeTab === 'media') {
        data = await mediaUpload.mutateAsync(selectedFile);
      } else {
        data = await docUpload.mutateAsync(selectedFile);
      }
      
      setUploadStatus('success');
      if (onUploadSuccess) {
        onUploadSuccess({
          file: selectedFile,
          data: data,
          type: activeTab
        });
      }
      setTimeout(() => {
        setSelectedFile(null);
        setUploadStatus('idle');
      }, 3000);
    } catch (err) {
      setUploadStatus('error');
      setErrorMessage(err.response?.data?.message || err.message || 'Upload failed');
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const isOverLimit = selectedFile && selectedFile.size > MAX_FILE_SIZE;

  return (
    <div className="glass-panel rounded-xl p-4 w-full flex flex-col gap-4">
      {/* Tabs */}
      <div className="flex rounded-lg bg-black/40 p-1 border border-white/5">
        <button 
          onClick={() => { setActiveTab('document'); setSelectedFile(null); setUploadStatus('idle'); }}
          className={`flex-1 py-1.5 text-xs font-bold rounded-md flex items-center justify-center gap-2 transition-all ${activeTab === 'document' ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg' : 'text-gray-400 hover:text-gray-200'}`}
        >
          <FileText size={14} /> Document
        </button>
        <button 
          onClick={() => { setActiveTab('media'); setSelectedFile(null); setUploadStatus('idle'); }}
          className={`flex-1 py-1.5 text-xs font-bold rounded-md flex items-center justify-center gap-2 transition-all ${activeTab === 'media' ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg' : 'text-gray-400 hover:text-gray-200'}`}
        >
          <Film size={14} /> Media
        </button>
      </div>
      
      <div 
        className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer overflow-hidden group ${
          dragActive ? 'border-indigo-500 bg-indigo-500/10' : isOverLimit ? 'border-red-500/50 bg-red-500/5 hover:border-red-500 hover:bg-red-500/10' : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/5'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-upload').click()}
      >
        <input 
          id="file-upload" 
          type="file" 
          className="hidden" 
          onChange={handleChange} 
          accept={activeTab === 'document' ? ".pdf,.txt,.docx" : ".mp3,.mp4,.wav,.m4a,.webm"} 
        />
        
        {selectedFile ? (
          <div className="flex flex-col items-center gap-2 relative z-10 group/file">
            <button 
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                setUploadStatus('idle');
                setErrorMessage('');
                document.getElementById('file-upload').value = '';
              }}
              className="absolute -top-3 -right-3 bg-black/60 backdrop-blur-sm p-1.5 rounded-full border border-white/10 text-gray-400 hover:text-red-400 hover:border-red-400/50 hover:bg-red-400/10 transition-all opacity-0 group-hover/file:opacity-100 z-20 shadow-xl"
              title="Remove file"
            >
              <X size={14} />
            </button>
            {activeTab === 'media' ? <FileAudio size={36} className={isOverLimit ? "text-red-400" : "text-pink-400"} /> : <FileIcon size={36} className={isOverLimit ? "text-red-400" : "text-indigo-400"} />}
            <span className={`font-medium text-xs truncate max-w-[200px] ${isOverLimit ? "text-red-300" : "text-gray-200"}`}>{selectedFile.name}</span>
            <span className={`text-[10px] font-mono ${isOverLimit ? "text-red-400 font-bold" : "text-gray-500"}`}>{formatSize(selectedFile.size)}</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 opacity-70 group-hover:opacity-100 transition-opacity">
            <UploadCloud size={28} className="text-indigo-400 group-hover:scale-110 transition-transform" />
            <p className="text-xs font-bold text-gray-300">Drag & drop or click</p>
            <p className="text-[9px] text-gray-500 uppercase tracking-widest mt-1">
              {activeTab === 'document' ? 'PDF, DOCX, TXT' : 'MP3, MP4, WAV, WEBM'}
            </p>
          </div>
        )}
      </div>

      <div className="text-center text-[10px] text-gray-400 font-medium tracking-wide">
        Maximum allowed size: <span className="font-bold text-indigo-400">25 MB</span>
      </div>

      {uploadStatus === 'error' && (
        <div className="p-2.5 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2 text-red-300 text-xs">
          <AlertCircle size={14} className="shrink-0 mt-0.5" />
          <p className="leading-snug">{errorMessage}</p>
        </div>
      )}

      {uploadStatus === 'success' && (
        <div className="p-2.5 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center gap-2 text-green-300 text-xs">
          <CheckCircle size={14} className="shrink-0" />
          <p>Indexed successfully! Ready to chat.</p>
        </div>
      )}

      <button
        onClick={submitUpload}
        disabled={!selectedFile || uploadStatus === 'uploading' || isOverLimit}
        className={`w-full py-2.5 px-4 rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2 ${
          !selectedFile || uploadStatus === 'uploading' || isOverLimit
            ? 'bg-white/5 text-gray-500 cursor-not-allowed border border-white/5' 
            : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-500/20'
        }`}
      >
        {uploadStatus === 'uploading' ? (
          <>
            <svg className="animate-spin h-4 w-4 text-indigo-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>{activeTab === 'media' ? 'Transcribing with AI...' : 'Parsing & Indexing...'}</span>
          </>
        ) : isOverLimit ? 'File exceeds limit (25 MB)' : 'Upload to Knowledge Base'}
      </button>

      {uploadStatus === 'uploading' && (
        <p className="text-center text-[10px] text-indigo-300/80 animate-pulse mt-1 font-medium">
          {activeTab === 'media' 
            ? 'Extracting speech and transcribing timestamps locally on CPU...' 
            : 'Generating embeddings and storing in vector database...'}
        </p>
      )}
    </div>
  );
}
