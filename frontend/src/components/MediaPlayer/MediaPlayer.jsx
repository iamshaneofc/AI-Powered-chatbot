import React, { useRef, useEffect } from 'react';
import ReactPlayer from 'react-player';

export default function MediaPlayer({ mediaUrl, seekTimestamp }) {
  const playerRef = useRef(null);

  useEffect(() => {
    if (seekTimestamp !== null && playerRef.current) {
      // Seek to timestamp when it changes
      playerRef.current.seekTo(parseFloat(seekTimestamp), 'seconds');
    }
  }, [seekTimestamp]);

  if (!mediaUrl) {
    return null;
  }

  return (
    <div className="bg-[#1c2128] rounded-xl shadow-md border border-gray-800/60 w-full overflow-hidden">
      <div className="bg-black aspect-video relative group">
        <ReactPlayer
          ref={playerRef}
          url={mediaUrl}
          width="100%"
          height="100%"
          controls={true}
          playing={seekTimestamp !== null} // Auto play when seek is triggered
          style={{ position: 'absolute', top: 0, left: 0 }}
        />
      </div>
    </div>
  );
}
