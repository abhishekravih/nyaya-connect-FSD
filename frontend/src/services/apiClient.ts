/**
 * NyayaConnect Unified API Client
 * Person 4: System Integration & DevOps Lead
 * File: /frontend/src/services/apiClient.ts
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

const USE_MOCKS =
  process.env.NEXT_PUBLIC_USE_MOCKS === 'true';

export interface VoiceAskPayload {
  audioBlob?: Blob;
  sourceLanguage: string;
  browserTranscript?: string;
}

export interface ArticleCitation {
  article_number: string;
  title: string;
  relevance_summary: string;
}

export interface LawyerRecommendation {
  id: number;
  name: string;
  specialization: string;
  bar_council_id: string;
  experience_years: number;
  consultation_fee: number;
  rating: number;
  reviews_count: number;
  verified: boolean;
  languages_spoken: string[];
  location: string;
  milestones: string[];
}

export interface VoiceAskResult {
  success: boolean;
  source_language: string;
  speech_source: string;
  transcribed_vernacular_text: string;
  translated_english_query: string;
  constitutional_articles: ArticleCitation[];
  recommended_case_category: string;
  translated_explanation: string;
  original_english_explanation: string;
  preserved_citations: string[];
  pipeline_latency_ms: number;
}

export interface LegalAssistResult {
  status: string;
  query: string;
  category: string;
  explanation: string;
  constitutional_articles: ArticleCitation[];
  recommended_lawyers: LawyerRecommendation[];
  response_time_ms: number;
}

export interface BookingRecord {
  booking_id: number;
  lawyer_id: number;
  lawyer_name: string;
  client_name: string;
  client_phone: string;
  case_category: string;
  total_fee: number;
  payment_status: string;
  current_milestone: number;
  created_at: string;
}

/**
 * 1. POST /api/v1/voice/ask
 */
export async function askVernacularVoice(payload: VoiceAskPayload): Promise<VoiceAskResult> {
  const formData = new FormData();
  if (payload.audioBlob) {
    formData.append('audio_file', payload.audioBlob, 'voice_query.webm');
  }
  formData.append('source_language', payload.sourceLanguage);
  if (payload.browserTranscript) {
    formData.append('browser_transcript', payload.browserTranscript);
  }

  const response = await fetch(`${API_BASE_URL}/voice/ask`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Voice request failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * 2. POST /api/v1/orchestrate/legal-assist
 */
export async function orchestrateLegalAssist(
  query: string,
  sourceLanguage: string = 'en-IN'
): Promise<LegalAssistResult> {
  const response = await fetch(`${API_BASE_URL}/orchestrate/legal-assist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, source_language: sourceLanguage })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Orchestrator request failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * 3. POST /api/v1/lawyers/book
 */
export async function bookLawyerConsultation(data: {
  lawyerId: number;
  clientName: string;
  clientPhone: string;
  caseCategory: string;
  notes?: string;
}) {
  const response = await fetch(`${API_BASE_URL}/lawyers/book`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lawyer_id: data.lawyerId,
      client_name: data.clientName,
      client_phone: data.clientPhone,
      case_category: data.caseCategory,
      notes: data.notes
    })
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Booking failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * 4. GET /api/v1/lawyers/bookings (Dashboard view)
 */
export async function fetchPersistedBookings(): Promise<BookingRecord[]> {
  const response = await fetch(`${API_BASE_URL}/lawyers/bookings`);
  if (!response.ok) {
    return [];
  }
  return response.json();
}
