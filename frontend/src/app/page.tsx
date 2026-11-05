'use client';

import React, { useState, useEffect } from 'react';
import {
  startVernacularSpeechRecognition,
  captureAudioBlob,
  checkSpeechCapabilities,
  VoiceRecordingSession,
  BrowserSpeechCapability
} from '../utils/voiceFallback';
import {
  askVernacularVoice,
  orchestrateLegalAssist,
  bookLawyerConsultation,
  fetchPersistedBookings,
  VoiceAskResult,
  LegalAssistResult,
  LawyerRecommendation,
  BookingRecord
} from '../services/apiClient';

export default function HomePage() {
  const [selectedLanguage, setSelectedLanguage] = useState('kn-IN');
  const [isRecording, setIsRecording] = useState(false);
  const [speechMode, setSpeechMode] = useState<string>('idle');
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [capability, setCapability] = useState<BrowserSpeechCapability | null>(null);

  const [liveTranscript, setLiveTranscript] = useState('');
  const [textQuery, setTextQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [voiceResult, setVoiceResult] = useState<VoiceAskResult | null>(null);
  const [orchestratorResult, setOrchestratorResult] = useState<LegalAssistResult | null>(null);

  // Booking Form State
  const [selectedLawyer, setSelectedLawyer] = useState<LawyerRecommendation | null>(null);
  const [clientName, setClientName] = useState('');
  const [clientPhone, setClientPhone] = useState('');
  const [bookingSuccess, setBookingSuccess] = useState<string | null>(null);
  const [bookingError, setBookingError] = useState<string | null>(null);

  // Dashboard Bookings
  const [bookingsList, setBookingsList] = useState<BookingRecord[]>([]);

  const [recordingSession, setRecordingSession] = useState<VoiceRecordingSession | null>(null);
  const [audioCapture, setAudioCapture] = useState<{ stopRecording: () => void } | null>(null);
  const [capturedAudioBlob, setCapturedAudioBlob] = useState<Blob | null>(null);

  useEffect(() => {
    setCapability(checkSpeechCapabilities());
    loadBookings();
  }, []);

  const loadBookings = async () => {
    try {
      const records = await fetchPersistedBookings();
      setBookingsList(records);
    } catch {
      // ignore
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      if (recordingSession) recordingSession.stop();
      if (audioCapture) audioCapture.stopRecording();
      setIsRecording(false);
      setSpeechMode('idle');
    } else {
      setLiveTranscript('');
      setVoiceResult(null);
      setBookingSuccess(null);
      setSpeechError(null);

      const audioController = await captureAudioBlob((blob) => {
        setCapturedAudioBlob(blob);
      });
      setAudioCapture(audioController);

      const session = startVernacularSpeechRecognition({
        language: selectedLanguage,
        onStart: (mode) => {
          setSpeechMode(mode === 'on-device' ? 'On-Device Speech Processing' : 'Browser Cloud-Stream Recognition');
        },
        onResult: (text) => {
          setLiveTranscript(text);
          setTextQuery(text);
        },
        onError: (err) => {
          setSpeechError(err);
          setIsRecording(false);
          setSpeechMode('unavailable');
        },
        onEnd: () => {
          setIsRecording(false);
          setSpeechMode('idle');
        }
      });

      setRecordingSession(session);
      setIsRecording(true);
    }
  };

  const submitQuery = async () => {
    const queryToSubmit = textQuery || liveTranscript;
    if (!queryToSubmit && !capturedAudioBlob) {
      alert('Please enter a query or record your voice.');
      return;
    }
    setLoading(true);
    setBookingSuccess(null);
    setBookingError(null);

    try {
      // 1. If voice audio/transcript was captured, send to Vernacular Voice Bridge
      if (capturedAudioBlob || liveTranscript) {
        try {
          const voiceRes = await askVernacularVoice({
            audioBlob: capturedAudioBlob || undefined,
            sourceLanguage: selectedLanguage,
            browserTranscript: liveTranscript || textQuery
          });
          setVoiceResult(voiceRes);
        } catch (e: any) {
          console.warn('Voice bridge note:', e.message);
        }
      }

      // 2. Query Unified Orchestrator for RAG articles + Top 3 Affordable Lawyers
      const orchRes = await orchestrateLegalAssist(
        queryToSubmit,
        selectedLanguage
      );
      setOrchestratorResult(orchRes);
    } catch (err: any) {
      alert(`Integration Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBookLawyerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLawyer) return;
    if (!clientName.trim() || !clientPhone.trim()) {
      setBookingError('Please enter client full name and contact phone number.');
      return;
    }

    setBookingError(null);
    try {
      const res = await bookLawyerConsultation({
        lawyerId: selectedLawyer.id,
        clientName: clientName.trim(),
        clientPhone: clientPhone.trim(),
        caseCategory: orchestratorResult?.category || 'Consumer',
        notes: textQuery || liveTranscript
      });
      setBookingSuccess(
        `Consultation booked with ${res.lawyer_name}! Persisted SQL Booking ID: #${res.booking_id}. Total Fee: ₹${res.total_fee}`
      );
      setSelectedLawyer(null);
      setClientName('');
      setClientPhone('');
      await loadBookings();
    } catch (err: any) {
      setBookingError(err.message);
    }
  };

  return (
    <main style={{ maxWidth: '1080px', margin: '0 auto', padding: '24px 16px' }}>
      {/* Header */}
      <header style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '16px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '28px', color: '#1e3a8a' }}>NyayaConnect (ನ್ಯಾಯ ಕನೆಕ್ಟ್)</h1>
            <p style={{ margin: '4px 0 0 0', color: '#64748b' }}>
              Full-Stack Vernacular Legal Advisor & Transparent Lawyer Marketplace • SDG 16
            </p>
          </div>
          <div>
            <label style={{ fontSize: '13px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              Language:
            </label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '14px' }}
            >
              <option value="kn-IN">ಕನ್ನಡ (Kannada - kn-IN)</option>
              <option value="hi-IN">हिन्दी (Hindi - hi-IN)</option>
              <option value="ta-IN">தமிழ் (Tamil - ta-IN)</option>
              <option value="te-IN">తెలుగు (Telugu - te-IN)</option>
              <option value="mr-IN">मराठी (Marathi - mr-IN)</option>
              <option value="en-IN">Indian English (en-IN)</option>
            </select>
          </div>
        </div>
      </header>

      {/* Voice Recognition Capability Notice */}
      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px 14px', marginBottom: '18px', fontSize: '13px', color: '#475569' }}>
        <strong>Speech Engine Status:</strong> {capability?.supported ? (
          <span>Web Speech API available. ({capability.notes})</span>
        ) : (
          <span style={{ color: '#d97706' }}>Web Speech API unavailable in this environment. Text input is active.</span>
        )}
        {speechMode !== 'idle' && (
          <span style={{ marginLeft: '12px', fontWeight: 600, color: '#2563eb' }}>
            ● Mode: {speechMode}
          </span>
        )}
      </div>

      {speechError && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '10px 14px', borderRadius: '8px', marginBottom: '18px', fontSize: '13px' }}>
          ⚠️ {speechError}
        </div>
      )}

      {/* Voice & Query Input */}
      <section style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#0f172a' }}>
          Step 1: Ask Your Legal Question
        </h2>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
          <button
            onClick={toggleRecording}
            style={{
              padding: '12px 20px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              backgroundColor: isRecording ? '#dc2626' : '#2563eb',
              color: '#ffffff'
            }}
          >
            {isRecording ? '⏹ Stop Recording' : '🎙 Record Voice (Web Speech)'}
          </button>
          {isRecording && (
            <span style={{ color: '#dc2626', fontWeight: 500, fontSize: '14px' }}>
              ● Recording voice query ({speechMode})...
            </span>
          )}
        </div>

        <textarea
          rows={3}
          value={textQuery}
          onChange={(e) => setTextQuery(e.target.value)}
          placeholder="Speak or type your legal question in Kannada, Hindi, or English..."
          style={{
            width: '100%',
            boxSizing: 'border-box',
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid #cbd5e1',
            fontSize: '15px',
            marginBottom: '12px'
          }}
        />

        <button
          onClick={submitQuery}
          disabled={loading}
          style={{
            padding: '10px 24px',
            borderRadius: '6px',
            backgroundColor: '#059669',
            color: '#fff',
            border: 'none',
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Synthesizing Legal RAG & Matching Lawyers...' : 'Submit to RAG & Marketplace'}
        </button>
      </section>

      {/* Phase 2: Vernacular Voice Output */}
      {voiceResult && (
        <section style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px 0', color: '#166534', fontSize: '18px' }}>
            Phase 2: 4-Stage Vernacular Pipeline Output ({voiceResult.pipeline_latency_ms}ms)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
            <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
              <strong style={{ fontSize: '12px', color: '#64748b' }}>SPEECH TRANSCRIPT ({voiceResult.speech_source})</strong>
              <p style={{ margin: '6px 0 0 0', fontWeight: 600 }}>{voiceResult.transcribed_vernacular_text}</p>
            </div>
            <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
              <strong style={{ fontSize: '12px', color: '#64748b' }}>TRANSLATED QUERY (FOR RAG)</strong>
              <p style={{ margin: '6px 0 0 0' }}>{voiceResult.translated_english_query}</p>
            </div>
            <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
              <strong style={{ fontSize: '12px', color: '#64748b' }}>VERNACULAR EXPLANATION (PRESERVED CITATIONS)</strong>
              <p style={{ margin: '6px 0 0 0' }}>{voiceResult.translated_explanation}</p>
            </div>
          </div>
        </section>
      )}

      {/* Constitutional RAG Section */}
      {orchestratorResult && (
        <section style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '20px', color: '#1e3a8a' }}>
              Constitutional Grounding & Statutory Remedies ({orchestratorResult.category} Law)
            </h3>
            <span style={{ background: '#dbeafe', color: '#1e40af', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>
              Category: {orchestratorResult.category}
            </span>
          </div>

          <p style={{ lineHeight: 1.6, color: '#334155', marginBottom: '16px' }}>
            {orchestratorResult.explanation}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px', marginBottom: '12px' }}>
            {orchestratorResult.constitutional_articles.map((art, idx) => (
              <div key={idx} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px', backgroundColor: '#f8fafc' }}>
                <span style={{ display: 'inline-block', backgroundColor: '#fed7aa', color: '#9a3412', fontWeight: 700, fontSize: '12px', padding: '2px 8px', borderRadius: '4px', marginBottom: '6px' }}>
                  {art.article_number}
                </span>
                <h4 style={{ margin: '4px 0', fontSize: '15px', color: '#0f172a' }}>{art.title}</h4>
                <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>{art.relevance_summary}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Lawyer Marketplace Cards */}
      {orchestratorResult && (
        <section style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '20px', color: '#1e3a8a' }}>
            Recommended Affordable Lawyers (Sorted by Transparent Fee)
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {orchestratorResult.recommended_lawyers.map((lawyer) => (
              <div
                key={lawyer.id}
                style={{
                  border: '1px solid #cbd5e1',
                  borderRadius: '10px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <h4 style={{ margin: '0 0 4px 0', fontSize: '16px', color: '#0f172a' }}>{lawyer.name}</h4>
                    <span style={{ color: '#16a34a', fontWeight: 700, fontSize: '16px' }}>
                      ₹{lawyer.consultation_fee}
                    </span>
                  </div>
                  <p style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#475569' }}>{lawyer.specialization}</p>
                  <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '12px' }}>
                    <span>📍 {lawyer.location}</span> • <span>⚖ {lawyer.bar_council_id}</span> • <span>★ {lawyer.rating} ({lawyer.reviews_count} reviews)</span>
                  </div>

                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '10px', marginBottom: '12px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#334155', textTransform: 'uppercase' }}>
                      4 Smart Milestones:
                    </span>
                    <ol style={{ margin: '6px 0 0 0', paddingLeft: '18px', fontSize: '12px', color: '#475569' }}>
                      {lawyer.milestones.map((m, mIdx) => (
                        <li key={mIdx} style={{ marginBottom: '2px' }}>{m}</li>
                      ))}
                    </ol>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedLawyer(lawyer)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: '#1d4ed8',
                    color: '#fff',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Select for Booking
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Booking Modal / Form */}
      {selectedLawyer && (
        <section style={{ background: '#f8fafc', border: '2px solid #3b82f6', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px 0', color: '#1e3a8a' }}>
            Book Consultation with {selectedLawyer.name} (Fee: ₹{selectedLawyer.consultation_fee})
          </h3>
          <form onSubmit={handleBookLawyerSubmit} style={{ display: 'grid', gap: '12px', maxWidth: '500px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Your Full Name:
              </label>
              <input
                type="text"
                required
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="Enter citizen legal name"
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Contact Phone:
              </label>
              <input
                type="tel"
                required
                value={clientPhone}
                onChange={(e) => setClientPhone(e.target.value)}
                placeholder="+91-XXXXXXXXXX"
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                type="submit"
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#059669',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Confirm Booking & Persist to SQL
              </button>
              <button
                type="button"
                onClick={() => setSelectedLawyer(null)}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#e2e8f0',
                  color: '#334155',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      {bookingSuccess && (
        <div style={{ background: '#ecfdf5', border: '1px solid #10b981', color: '#065f46', padding: '14px', borderRadius: '8px', marginBottom: '24px', fontWeight: 600 }}>
          ✓ {bookingSuccess}
        </div>
      )}

      {bookingError && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '14px', borderRadius: '8px', marginBottom: '24px' }}>
          ✕ {bookingError}
        </div>
      )}

      {/* Dashboard View: Persisted SQL Bookings */}
      <section style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '20px', color: '#1e3a8a' }}>
          Citizen Dashboard: Persisted SQL Bookings ({bookingsList.length})
        </h3>
        {bookingsList.length === 0 ? (
          <p style={{ color: '#64748b' }}>No bookings created yet. Book a consultation above to see records persisted in the database.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#475569' }}>
                  <th style={{ padding: '8px' }}>Booking ID</th>
                  <th style={{ padding: '8px' }}>Client</th>
                  <th style={{ padding: '8px' }}>Lawyer</th>
                  <th style={{ padding: '8px' }}>Category</th>
                  <th style={{ padding: '8px' }}>Total Fee</th>
                  <th style={{ padding: '8px' }}>Status</th>
                  <th style={{ padding: '8px' }}>Milestone</th>
                </tr>
              </thead>
              <tbody>
                {bookingsList.map((b) => (
                  <tr key={b.booking_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '8px', fontWeight: 700 }}>#{b.booking_id}</td>
                    <td style={{ padding: '8px' }}>{b.client_name} ({b.client_phone})</td>
                    <td style={{ padding: '8px' }}>{b.lawyer_name}</td>
                    <td style={{ padding: '8px' }}>{b.case_category}</td>
                    <td style={{ padding: '8px', color: '#16a34a', fontWeight: 600 }}>₹{b.total_fee}</td>
                    <td style={{ padding: '8px' }}>
                      <span style={{ backgroundColor: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>
                        {b.payment_status}
                      </span>
                    </td>
                    <td style={{ padding: '8px' }}>Milestone {b.current_milestone} of 4</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
