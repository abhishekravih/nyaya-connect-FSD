import lawyers from '../mocks/lawyers.json';
import responses from '../mocks/rag_responses.json';
const mocked = process.env.NEXT_PUBLIC_USE_MOCKS !== 'false';
const wait = () => new Promise(r => setTimeout(r, 300 + Math.random() * 500));

async function request(path, options = {}) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) throw new Error('Set NEXT_PUBLIC_API_BASE_URL to use the live API.');
  const res = await fetch(`${base}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers }
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export async function getLawyers(filters = {}) {
  if (!mocked) return request(`/lawyers?${new URLSearchParams(filters)}`);
  await wait();
  return lawyers.filter(l => !filters.category || l.category === filters.category);
}

export async function getLawyerById(id) {
  if (!mocked) return request(`/lawyers/${id}`);
  await wait();
  return lawyers.find(l => l.lawyer_id === id) || null;
}

export async function askLegalQuestion(query, lang = 'English') {
  if (!mocked) return request('/legal-question', { method: 'POST', body: JSON.stringify({ query, lang }) });
  await wait();
  const q = query.toLowerCase();
  return responses.find(r => r.query_keywords.some(k => q.includes(k))) || {
    answer_text: `I could not find a close constitutional match for “${query}” in this demo. Consumer product disputes are generally handled under consumer protection law, which is outside this constitutional sources demo. A consumer lawyer can help you assess the available remedies.`,
    cited_articles: [],
    recommended_category: /defective|product|refund|consumer|warranty/.test(q) ? 'Consumer' : 'Civil',
    confidence_score: 0.32
  };
}

export async function submitVoiceQuery(blob, lang = 'English', browserTranscript = null) {
  if (!mocked) {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
    const langMap = {
      'Kannada': 'kn-IN',
      'Hindi': 'hi-IN',
      'Tamil': 'ta-IN',
      'Telugu': 'te-IN',
      'Marathi': 'mr-IN',
      'Bengali': 'bn-IN',
      'English': 'en-IN'
    };
    const langCode = langMap[lang] || (lang.includes('-') ? lang : 'en-IN');

    // Use multipart/form-data for audio streaming and strict typing
    const formData = new FormData();
    if (blob) {
      formData.append('audio_file', blob, 'recording.webm');
    }
    formData.append('source_language', langCode);
    if (browserTranscript) {
      formData.append('browser_transcript', browserTranscript);
    }

    const endpoint = base.endsWith('/api/v1') ? `${base}/voice/ask` : `${base}/api/v1/voice/ask`;
    const res = await fetch(endpoint, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Voice query failed (${res.status}): ${errText}`);
    }
    const data = await res.json();
    return {
      transcript: data.transcribed_vernacular_text,
      lang: lang,
      rag_response: {
        answer_text: data.translated_explanation,
        cited_articles: data.constitutional_articles,
        recommended_category: data.recommended_case_category,
        confidence_score: 0.90
      }
    };
  }
  await wait();
  const transcript = lang === 'Kannada' ? 'ನನ್ನನ್ನು ಬಂಧಿಸಿದರೆ ನನಗೆ ಯಾವ ಹಕ್ಕುಗಳಿವೆ?' : lang === 'Hindi' ? 'गिरफ्तार होने पर मेरे क्या अधिकार हैं?' : lang === 'Tamil' ? 'கைது செய்யப்பட்டால் எனக்கு என்ன உரிமைகள் உள்ளன?' : 'What are my rights if arrested?';
  return { transcript, lang, rag_response: responses.find(r => r.query_keywords.some(k => ['arrest', 'detention', 'article 22'].includes(k))) };
}

export async function createBooking(payload) {
  if (!mocked) return request('/bookings', { method: 'POST', body: JSON.stringify(payload) });
  await wait();
  return { ...payload, booking_id: `B${Date.now()}`, status: 'pending' };
}

export async function getBookings() {
  if (!mocked) return request('/bookings');
  await wait();
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem('nyayaconnect-bookings-v1') || '[]'); } catch { return []; }
}

export async function updateMilestone(bookingId, milestoneIndex, status) {
  if (!mocked) return request(`/bookings/${bookingId}/milestones/${milestoneIndex}`, { method: 'PATCH', body: JSON.stringify({ status }) });
  await wait();
  return { bookingId, milestoneIndex, status };
}
