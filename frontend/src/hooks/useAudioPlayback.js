import { useState, useEffect, useRef } from 'react';

export function useAudioPlayback(audioUrl, onPlaybackComplete) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    if (!audioUrl) return;

    audioRef.current = new Audio(audioUrl);
    
    audioRef.current.play()
      .then(() => setIsPlaying(true))
      .catch((err) => console.error("Audio playback blocked:", err));

    const handleEnded = () => {
      setIsPlaying(false);
      if (onPlaybackComplete) {
        onPlaybackComplete();
      }
    };

    audioRef.current.addEventListener('ended', handleEnded);

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.removeEventListener('ended', handleEnded);
      }
      setIsPlaying(false);
    };
  }, [audioUrl]);

  return { isPlaying };
}
