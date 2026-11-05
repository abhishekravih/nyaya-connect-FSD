/**
 * NyayaConnect Vernacular Voice Integration & Web Speech API Zero-Latency Fallback
 * Person 4: Systems Integration & DevOps Lead
 * File: /frontend/src/utils/voiceFallback.ts
 *
 * Provides resilient, zero-latency in-browser vernacular voice transcription.
 * Designed to function smoothly on restricted college, hackathon, and mobile Wi-Fi networks
 * where external cloud STT APIs may experience timeouts or quota limits.
 */

export interface SpeechRecognitionOptions {
  language: string; // e.g., 'kn-IN', 'hi-IN', 'ta-IN', 'te-IN', 'en-IN'
  onResult: (transcript: string, isFinal: boolean) => void;
  onError: (error: string) => void;
  onStart?: () => void;
  onEnd?: () => void;
}

export interface VoiceRecordingSession {
  stop: () => void;
  abort: () => void;
}

// Check if browser supports Web Speech API
export function isWebSpeechSupported(): boolean {
  if (typeof window === 'undefined') return false;
  return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
}

/**
 * Initializes and starts the browser's native Web Speech Recognition engine.
 * Emits zero-latency live transcripts directly from client hardware.
 */
export function startVernacularSpeechRecognition(options: SpeechRecognitionOptions): VoiceRecordingSession | null {
  if (typeof window === 'undefined') return null;

  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  if (!SpeechRecognition) {
    options.onError('Web Speech API is not supported in this browser. Please use Google Chrome or Edge.');
    return null;
  }

  try {
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = options.language || 'kn-IN';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      if (options.onStart) options.onStart();
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcriptPart;
        } else {
          interimTranscript += transcriptPart;
        }
      }

      const activeText = finalTranscript || interimTranscript;
      options.onResult(activeText, Boolean(finalTranscript));
    };

    recognition.onerror = (event: any) => {
      console.warn('[NyayaConnect WebSpeech Error]:', event.error);
      options.onError(event.error || 'Speech recognition encountered a network or permission error');
    };

    recognition.onend = () => {
      if (options.onEnd) options.onEnd();
    };

    recognition.start();

    return {
      stop: () => {
        try {
          recognition.stop();
        } catch (e) {
          // ignore already stopped
        }
      },
      abort: () => {
        try {
          recognition.abort();
        } catch (e) {
          // ignore
        }
      }
    };
  } catch (err: any) {
    options.onError(err.message || 'Failed to start Web Speech Recognition');
    return null;
  }
}

/**
 * Helper to record raw audio blob via MediaRecorder API concurrently,
 * so the backend voice bridge receives both the physical audio stream and
 * the local Web Speech fallback transcript.
 */
export async function captureAudioBlob(
  onStop: (blob: Blob) => void
): Promise<{ stopRecording: () => void } | null> {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    return null;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
    });
    const chunks: Blob[] = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(chunks, { type: mediaRecorder.mimeType });
      // Stop all tracks to release hardware microphone
      stream.getTracks().forEach((track) => track.stop());
      onStop(audioBlob);
    };

    mediaRecorder.start(250);

    return {
      stopRecording: () => {
        if (mediaRecorder.state !== 'inactive') {
          mediaRecorder.stop();
        }
      }
    };
  } catch (err) {
    console.warn('Microphone access unavailable or denied:', err);
    return null;
  }
}
