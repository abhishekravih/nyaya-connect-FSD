/**
 * NyayaConnect Vernacular Voice Integration & Web Speech Utility
 * Person 4: Systems Integration & DevOps Lead
 * File: /frontend/src/utils/voiceFallback.ts
 *
 * NOTE ON BROWSER SPEECH RECOGNITION (MDN REFERENCE):
 * The Web Speech API does NOT guarantee on-device or offline recognition.
 * Most modern browsers (Chrome/Edge) stream audio to vendor cloud servers
 * (e.g. Google/Microsoft speech servers) unless on-device language packs and
 * experimental APIs (e.g. `processLocally`) are supported and installed.
 * When on restricted networks (firewalls/proxies blocking speech servers),
 * browser recognition may fail; users should use the direct text input fallback.
 */

export interface SpeechRecognitionOptions {
  language: string; // e.g., 'kn-IN', 'hi-IN', 'ta-IN', 'te-IN', 'en-IN'
  onResult: (transcript: string, isFinal: boolean) => void;
  onError: (error: string) => void;
  onStart?: (mode: 'on-device' | 'cloud-stream' | 'unknown') => void;
  onEnd?: () => void;
}

export interface VoiceRecordingSession {
  stop: () => void;
  abort: () => void;
  mode: 'on-device' | 'cloud-stream' | 'unknown';
}

export interface BrowserSpeechCapability {
  supported: boolean;
  hasOnDeviceOption: boolean;
  notes: string;
}

/**
 * Checks browser speech recognition capabilities based on MDN standards.
 */
export function checkSpeechCapabilities(): BrowserSpeechCapability {
  if (typeof window === 'undefined') {
    return { supported: false, hasOnDeviceOption: false, notes: 'Non-browser SSR environment' };
  }

  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  if (!SpeechRecognition) {
    return {
      supported: false,
      hasOnDeviceOption: false,
      notes: 'Web Speech API is not supported in this browser. Use Chrome, Edge, or direct text input.'
    };
  }

  // Check for experimental processLocally property support
  const instance = new SpeechRecognition();
  const hasOnDeviceOption = 'processLocally' in instance;

  return {
    supported: true,
    hasOnDeviceOption,
    notes: hasOnDeviceOption
      ? 'Browser supports on-device speech preference check.'
      : 'Standard Web Speech active (may rely on browser cloud servers).'
  };
}

/**
 * Initializes and starts the browser's native Web Speech Recognition engine.
 * Sets realistic expectations regarding network and on-device requirements.
 */
export function startVernacularSpeechRecognition(options: SpeechRecognitionOptions): VoiceRecordingSession | null {
  if (typeof window === 'undefined') return null;

  const SpeechRecognition =
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

  if (!SpeechRecognition) {
    options.onError('Web Speech API is not supported in this browser. Please use Google Chrome/Edge or type your question below.');
    return null;
  }

  try {
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = options.language || 'kn-IN';
    recognition.maxAlternatives = 1;

    let recognizedMode: 'on-device' | 'cloud-stream' | 'unknown' = 'unknown';

    // Attempt on-device preference if browser supports the draft specification
    if ('processLocally' in recognition) {
      try {
        (recognition as any).processLocally = true;
        recognizedMode = 'on-device';
      } catch {
        recognizedMode = 'cloud-stream';
      }
    } else {
      recognizedMode = 'cloud-stream';
    }

    recognition.onstart = () => {
      if (options.onStart) options.onStart(recognizedMode);
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
      let message = event.error;
      if (event.error === 'network') {
        message = 'Speech recognition network error: Cloud speech server unreachable on this network. Please type your query below.';
      } else if (event.error === 'not-allowed') {
        message = 'Microphone permission denied. Please allow microphone access or type your query.';
      }
      options.onError(message);
    };

    recognition.onend = () => {
      if (options.onEnd) options.onEnd();
    };

    recognition.start();

    return {
      stop: () => {
        try {
          recognition.stop();
        } catch {
          // ignore
        }
      },
      abort: () => {
        try {
          recognition.abort();
        } catch {
          // ignore
        }
      },
      mode: recognizedMode
    };
  } catch (err: any) {
    options.onError(err.message || 'Failed to initialize speech recognition. Use text input.');
    return null;
  }
}

/**
 * Captures raw audio blob from device microphone via MediaRecorder API.
 */
export async function captureAudioBlob(
  onStop: (blob: Blob) => void
): Promise<{ stopRecording: () => void } | null> {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    return null;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : 'audio/mp4';

    const mediaRecorder = new MediaRecorder(stream, { mimeType });
    const chunks: Blob[] = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunks.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(chunks, { type: mediaRecorder.mimeType });
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
    console.warn('Microphone access unavailable:', err);
    return null;
  }
}
