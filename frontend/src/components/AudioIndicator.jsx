'use client';
import React from 'react';

export default function AudioIndicator({ isPlaying }) {
  if (!isPlaying) {
    return (
      <div style={{ color: '#6b7280', fontSize: '14px', margin: '10px 0' }}>
        • AI Interviewer is silent
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', height: '30px', color: '#2563eb', margin: '10px 0' }}>
      <div style={{ width: '4px', backgroundColor: '#2563eb', borderRadius: '2px', animation: 'bounce 0.6s infinite alternate' }} />
      <div style={{ width: '4px', backgroundColor: '#2563eb', borderRadius: '2px', animation: 'bounce 0.6s infinite alternate 0.2s' }} />
      <div style={{ width: '4px', backgroundColor: '#2563eb', borderRadius: '2px', animation: 'bounce 0.6s infinite alternate 0.4s' }} />
      <span style={{ marginLeft: '8px', fontSize: '14px', fontWeight: '500' }}>AI Interviewer speaking...</span>
      
      <style>{`
        @keyframes bounce {
          from { height: 4px; }
          to { height: 24px; }
        }
      `}</style>
    </div>
  );
}
