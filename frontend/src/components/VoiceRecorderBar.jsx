'use client';
import {useEffect, useRef, useState} from 'react';
import {Mic, Square, LoaderCircle} from 'lucide-react';
import {startVernacularSpeechRecognition} from '../utils/voiceFallback';

const languages = ['Kannada', 'Hindi', 'English', 'Tamil'];
const langCodeMap = {
  'Kannada': 'kn-IN',
  'Hindi': 'hi-IN',
  'Tamil': 'ta-IN',
  'English': 'en-IN'
};

export default function VoiceRecorderBar({onAudioCaptured, disabled}) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [language, setLanguage] = useState('English');

  const recorder = useRef(null);
  const chunks = useRef([]);
  const streamRef = useRef(null);
  const transcriptRef = useRef('');
  const speechSessionRef = useRef(null);

  useEffect(() => {
    if (!recording) return;
    const id = setInterval(() => setSeconds(s => s + 1), 1000);
    return () => clearInterval(id);
  }, [recording]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop());
      speechSessionRef.current?.stop();
    };
  }, []);

  async function toggle() {
    setError('');
    if (recording) {
      recorder.current?.stop();
      speechSessionRef.current?.stop();
      speechSessionRef.current = null;
      setRecording(false);
      setBusy(true);
      return;
    }

    try {
      if (typeof window === 'undefined' || typeof navigator === 'undefined') {
        throw new Error('Voice recording is only available in a browser.');
      }
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error('Voice recording is not supported in this browser. Please type your query below.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const r = new MediaRecorder(stream);
      recorder.current = r;
      chunks.current = [];
      transcriptRef.current = '';

      // Initialize Web Speech native recognition as client fallback
      try {
        speechSessionRef.current = startVernacularSpeechRecognition({
          language: langCodeMap[language] || 'en-IN',
          onResult: (text) => {
            if (text && text.trim()) {
              transcriptRef.current = text.trim();
            }
          },
          onError: (err) => {
            console.warn('Browser speech recognition fallback message:', err);
          }
        });
      } catch (speechErr) {
        console.warn('Native speech fallback not initialized:', speechErr);
      }

      r.ondataavailable = e => e.data.size && chunks.current.push(e.data);
      r.onstop = async () => {
        const blob = new Blob(chunks.current, { type: r.mimeType || 'audio/webm' });
        stream.getTracks().forEach(t => t.stop());
        streamRef.current = null;
        try {
          await onAudioCaptured?.(blob, language, transcriptRef.current);
        } catch (e) {
          setError(e.message || 'Could not process this recording. You may type your question below.');
        } finally {
          setBusy(false);
        }
      };

      r.start();
      setSeconds(0);
      setRecording(true);
    } catch (e) {
      setError(
        e.name === 'NotAllowedError'
          ? 'Microphone permission denied. You can type your legal inquiry below.'
          : (e.message || 'Speech recording error. Please type your question below.')
      );
    }
  }

  return (
    <div className="mt-5 rounded-2xl border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center gap-3">
        <button
          disabled={disabled || busy}
          onClick={toggle}
          aria-label={recording ? 'Stop recording' : 'Start voice question'}
          className={`grid h-11 w-11 place-items-center rounded-full ${
            recording ? 'bg-rose-600 text-white' : 'bg-orange text-background'
          } disabled:opacity-50`}
        >
          {busy ? <LoaderCircle className="animate-spin" size={18}/> : recording ? <Square size={17}/> : <Mic size={19}/>}
        </button>
        <div className="min-w-[90px] flex-1">
          <p className="text-sm font-medium">
            {recording ? 'Listening…' : busy ? 'Transcribing…' : 'Ask by voice'}
          </p>
          <p className="text-xs text-text-muted">
            {recording ? `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')} · ` : ''}
            {recording ? 'Speak clearly' : 'Audio recorded securely for legal RAG lookup'}
          </p>
        </div>
        <div aria-hidden="true" className={`flex h-8 items-center gap-1 ${recording ? '' : 'opacity-25'}`}>
          {Array.from({length: 12}, (_, i) => (
            <span
              key={i}
              className="w-1 rounded-full bg-orange animate-pulse"
              style={{height: `${8 + ((i * 7) % 20)}px`, animationDelay: `${i * 55}ms`}}
            />
          ))}
        </div>
        <label className="sr-only" htmlFor="voice-lang">Recording language</label>
        <select
          id="voice-lang"
          data-voice-lang
          value={language}
          onChange={e => setLanguage(e.target.value)}
          className="rounded-lg border border-border bg-surface-2 px-2 py-2 text-sm focus:border-orange focus:outline-none"
        >
          {languages.map(x => <option key={x}>{x}</option>)}
        </select>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-rose-300">{error}</p>}
    </div>
  );
}
