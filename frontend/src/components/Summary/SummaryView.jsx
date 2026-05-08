import React from 'react';
import { useSummarize } from '../../hooks/useApi';
import { Sparkles, Loader2 } from 'lucide-react';

export default function SummaryView({ filename }) {
  const { data, isLoading, isError } = useSummarize(filename);

  if (!filename) return null;

  return (
    <div className="bg-[#1c2128] rounded-xl p-4 shadow-md border border-gray-800/60 w-full relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <Sparkles size={48} />
      </div>
      
      {isLoading ? (
        <div className="flex items-center gap-3 text-blue-400 p-2">
          <Loader2 className="animate-spin" size={18} />
          <p className="text-sm font-medium">Generating summary...</p>
        </div>
      ) : isError ? (
        <p className="text-xs text-red-400 p-2">Unable to generate summary. Ensure the file was indexed successfully.</p>
      ) : (
        <div className="relative z-10">
          <p className="text-xs text-gray-300 leading-relaxed max-h-[250px] overflow-y-auto scrollbar-thin pr-2">
            {data?.summary || "No summary available."}
          </p>
        </div>
      )}
    </div>
  );
}
