/**
 * NyayaConnect Unified API Client
 * Person 4: System Integration & DevOps Lead
 * File: /frontend/src/services/apiClient.ts
 *
 * Switches smoothly between live FastAPI backend endpoints and resilient offline mocks
 * controlled via NEXT_PUBLIC_USE_MOCKS environment variable.
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
  transcribed_vernacular_text: string;
  translated_english_query: string;
  constitutional_articles: ArticleCitation[];
  recommended_case_category: string;
  translated_explanation: string;
  original_english_explanation: string;
  pipeline_latency_ms: number;
  speech_fallback_used: boolean;
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

/**
 * 1. POST /api/v1/voice/ask
 * Sends audio blob + source language + Web Speech API fallback text to backend.
 */
export async function askVernacularVoice(payload: VoiceAskPayload): Promise<VoiceAskResult> {
  if (USE_MOCKS) {
    return {
      success: true,
      source_language: payload.sourceLanguage,
      transcribed_vernacular_text: payload.browserTranscript || 'ದೋಷಪೂರಿತ ಮೊಬೈಲ್ ಮಾರಾಟ ಮತ್ತು ಹಣ ವಾಪಸಾತಿ ನಿರಾಕರಣೆ',
      translated_english_query: 'The retailer sold a defective phone and refused refund. What legal remedy applies?',
      constitutional_articles: [
        {
          article_number: 'Article 21',
          title: 'Protection of Life and Personal Liberty',
          relevance_summary: 'Guarantees fair hearing and natural justice under constitutional due process.'
        },
        {
          article_number: 'Article 39A',
          title: 'Equal Justice and Free Legal Aid',
          relevance_summary: 'Ensures justice is not denied due to economic or regional language barriers.'
        }
      ],
      recommended_case_category: 'Consumer',
      translated_explanation: 'ಗ್ರಾಹಕ ಸಂರಕ್ಷಣಾ ಕಾಯ್ದೆ 2019 ಮತ್ತು Article 21 ರ ಅಡಿಯಲ್ಲಿ ನೀವು ಪೂರ್ಣ ಮರುಪಾವತಿ ಮತ್ತು ನಷ್ಟಪರಿಹಾರ ಪಡೆಯಲು ಅರ್ಹರಾಗಿದ್ದೀರಿ.',
      original_english_explanation: 'Under Consumer Protection Act 2019 read with Article 21, you are entitled to full refund.',
      pipeline_latency_ms: 180,
      speech_fallback_used: Boolean(payload.browserTranscript)
    };
  }

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
    throw new Error(`Voice bridge request failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * 2. POST /api/v1/orchestrate/legal-assist
 * Unified composite orchestrator endpoint returning RAG articles & top 3 affordable lawyers.
 */
export async function orchestrateLegalAssist(
  query: string,
  sourceLanguage: string = 'en-IN'
): Promise<LegalAssistResult> {
  if (USE_MOCKS) {
    return {
      status: 'success',
      query,
      category: 'Consumer',
      explanation: 'Under the Consumer Protection Act 2019 read with Article 21 and Article 39A of the Constitution of India, consumers are protected against defective products.',
      constitutional_articles: [
        {
          article_number: 'Article 21',
          title: 'Protection of Life and Personal Liberty',
          relevance_summary: 'Guarantees fair consumer adjudication and procedural equity.'
        },
        {
          article_number: 'Article 39A',
          title: 'Equal Justice and Free Legal Aid',
          relevance_summary: 'Ensures access to justice irrespective of economic disabilities.'
        }
      ],
      recommended_lawyers: [
        {
          id: 101,
          name: 'Adv. Rajeshwari Hegde',
          specialization: 'Consumer Protection & Product Liability',
          bar_council_id: 'KAR/2014/4891',
          experience_years: 9,
          consultation_fee: 799,
          rating: 4.9,
          reviews_count: 142,
          verified: true,
          languages_spoken: ['Kannada', 'English', 'Hindi'],
          location: 'Bengaluru, Karnataka',
          milestones: [
            '1. Notice Drafting & Statutory Demand',
            '2. District Consumer Commission Filing',
            '3. Evidence & Rejoinder Submission',
            '4. Final Arguments & Compensation Award'
          ]
        }
      ],
      response_time_ms: 220
    };
  }

  const response = await fetch(`${API_BASE_URL}/orchestrate/legal-assist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, source_language: sourceLanguage })
  });

  if (!response.ok) {
    throw new Error(`Orchestrator request failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * 3. POST /api/v1/lawyers/book
 * Books a lawyer with upfront fee cards & 4 smart milestones.
 */
export async function bookLawyerConsultation(data: {
  lawyerId: number;
  clientName: string;
  clientPhone: string;
  caseCategory: string;
  notes?: string;
}) {
  if (USE_MOCKS) {
    return {
      booking_id: 1,
      lawyer_id: data.lawyerId,
      status: 'Confirmed',
      message: 'Consultation booked successfully with smart escrow milestones.',
      milestone_schedule: [
        'Milestone 1: Preliminary Case Review & Evidence Audit',
        'Milestone 2: Statutory Legal Notice & Registry Service',
        'Milestone 3: Tribunal / District Commission Filing',
        'Milestone 4: Arguments, Settlement & Decree Recovery'
      ]
    };
  }

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
    throw new Error(`Booking request failed with HTTP ${response.status}`);
  }

  return response.json();
}
