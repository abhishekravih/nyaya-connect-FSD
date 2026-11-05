'use client';

import React, { useState, useEffect } from 'react';
import {
  startVernacularSpeechRecognition,
  captureAudioBlob,
  VoiceRecordingSession
} from '../utils/voiceFallback';
import {
  askVernacularVoice,
  orchestrateLegalAssist,
  bookLawyerConsultation,
  VoiceAskResult,
  LegalAssistResult,
  LawyerRecommendation
} from '../services/apiClient';

export default function HomePage() {
  const [selectedLanguage, setSelectedLanguage] = useState('kn-IN');
  const [isRecording, setIsRecording] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [textQuery, setTextQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [voiceResult, setVoiceResult] = useState<VoiceAskResult | null>(null);
  const [orchestratorResult, setOrchestratorResult] = useState<LegalAssistResult | null>(null);
  const [selectedLawyer, setSelectedLawyer] = useState<LawyerRecommendation | null>(null);
  const [bookingSuccess, setBookingSuccess] = useState<string | null>(null);

  const [recordingSession, setRecordingSession] = useState<VoiceRecordingSession | null>(null);
  const [audioCapture, setAudioCapture] = useState<{ stopRecording: () => void } | null>(null);
  const [capturedAudioBlob, setCapturedAudioBlob] = useState<Blob | null>(null);

  const toggleRecording = async () => {
    if (isRecording) {
      // Stop recording
      if (recordingSession) recordingSession.stop();
      if (audioCapture) audioCapture.stopRecording();
      setIsRecording(false);
    } else {
      // Start recording
      setLiveTranscript('');
      setVoiceResult(null);
      setBookingSuccess(null);

      // Start audio recording
      const audioController = await captureAudioBlob((blob) => {
        setCapturedAudioBlob(blob);
      });
      setAudioCapture(audioController);

      // Start zero-latency Web Speech API fallback
      const session = startVernacularSpeechRecognition({
        language: selectedLanguage,
        onResult: (text) => {
          setLiveTranscript(text);
          setTextQuery(text);
        },
        onError: (err) => {
          console.warn('Speech engine notification:', err);
        },
        onEnd: () => {
          setIsRecording(false);
        }
      });

      setRecordingSession(session);
      setIsRecording(true);
    }
  };

  const submitVoiceQuery = async () => {
    if (!liveTranscript && !capturedAudioBlob && !textQuery) return;
    setLoading(true);
    setBookingSuccess(null);

    try {
      // 1. Send to Vernacular Voice Bridge
      const voiceRes = await askVernacularVoice({
        audioBlob: capturedAudioBlob || undefined,
        sourceLanguage: selectedLanguage,
        browserTranscript: liveTranscript || textQuery
      });
      setVoiceResult(voiceRes);

      // 2. Query Unified Orchestrator for RAG articles + Top 3 Affordable Lawyers
      const orchRes = await orchestrateLegalAssist(
        voiceRes.translated_english_query || textQuery,
        selectedLanguage
      );
      setOrchestratorResult(orchRes);
    } catch (err: any) {
      alert(`API Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleBookLawyer = async (lawyer: LawyerRecommendation) => {
    try {
      const res = await bookLawyerConsultation({
        lawyerId: lawyer.id,
        clientName: 'Verified Citizen',
        clientPhone: '+91-9876543210',
        caseCategory: orchestratorResult?.category || 'Consumer',
        notes: textQuery || liveTranscript
      });
      setSelectedLawyer(lawyer);
      setBookingSuccess(`Booking confirmed with ${lawyer.name}! Smart Escrow ID: #${res.booking_id}`);
    } catch (err: any) {
      alert(`Booking failed: ${err.message}`);
    }
  };

  return (
    <main style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px 16px' }}>
      {/* Header */}
      <header style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '16px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '28px', color: '#1e3a8a' }}>NyayaConnect (ನ್ಯಾಯ ಕನೆಕ್ಟ್)</h1>
            <p style={{ margin: '4px 0 0 0', color: '#64748b' }}>
              Full-Stack Vernacular Legal Advisor & Transparent Lawyer Marketplace • SDG 16
            </p>
          </div>
          <div>
            <label style={{ fontSize: '13px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              Vernacular Language:
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

      {/* Voice Input & Query Section */}
      <section style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', marginTop: 0, color: '#0f172a' }}>
          Step 1: Speak or Type Legal Query (Vernacular Bridge)
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
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            {isRecording ? '⏹ Stop Recording' : '🎙 Record Voice (Web Speech API)'}
          </button>
          {isRecording && (
            <span style={{ color: '#dc2626', fontWeight: 500, fontSize: '14px' }}>
              ● Listening with zero latency fallback...
            </span>
          )}
        </div>

        <textarea
          rows={3}
          value={textQuery}
          onChange={(e) => setTextQuery(e.target.value)}
          placeholder="Speak into microphone or type your legal question in Kannada, Hindi, or English..."
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
          onClick={submitVoiceQuery}
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
          {loading ? 'Processing 4-Stage Vernacular Pipeline...' : 'Submit to RAG & Marketplace'}
        </button>
      </section>

      {/* 4-Stage Vernacular Pipeline Visualizer */}
      {voiceResult && (
        <section style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px 0', color: '#166534', fontSize: '18px' }}>
            Phase 2: 4-Stage Vernacular Pipeline Output ({voiceResult.pipeline_latency_ms} ms)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
            <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
              <strong style={{ fontSize: '12px', color: '#64748b' }}>STAGE 1 & 2: TRANSCRIBED VERNACULAR</strong>
              <p style={{ margin: '6px 0 0 0', fontWeight: 600 }}>{voiceResult.transcribed_vernacular_text}</p>
            </div>
            <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
              <strong style={{ fontSize: '12px', color: '#64748b' }}>STAGE 3: TRANSLATED ENGLISH (FOR RAG)</strong>
              <p style={{ margin: '6px 0 0 0' }}>{voiceResult.translated_english_query}</p>
            </div>
            <div style={{ background: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
              <strong style={{ fontSize: '12px', color: '#64748b' }}>STAGE 4: VERNACULAR EXPLANATION (PRESERVED CITATIONS)</strong>
              <p style={{ margin: '6px 0 0 0' }}>{voiceResult.translated_explanation}</p>
            </div>
          </div>
        </section>
      )}

      {/* Constitutional Articles Grounding Cards */}
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

      {/* Recommended Verified Affordable Lawyers with Upfront Fee Cards */}
      {orchestratorResult && (
        <section style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '20px', color: '#1e3a8a' }}>
            Top 3 Verified Lawyers (Sorted by Transparent Affordability)
          </h3>

          {bookingSuccess && (
            <div style={{ background: '#ecfdf5', border: '1px solid #10b981', color: '#065f46', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontWeight: 600 }}>
              ✓ {bookingSuccess}
            </div>
          )}

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
                    <span>📍 {lawyer.location}</span> • <span>⚖ {lawyer.bar_council_id}</span> • <span>★ {lawyer.rating} ({lawyer.reviews_count})</span>
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
                  onClick={() => handleBookLawyer(lawyer)}
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
                  Book with 4 Smart Milestones
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
