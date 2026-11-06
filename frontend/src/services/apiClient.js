import lawyers from '../mocks/lawyers.json';
import responses from '../mocks/rag_responses.json';
const mocked = process.env.NEXT_PUBLIC_USE_MOCKS !== 'false';
const wait = () => new Promise(r => setTimeout(r, 300 + Math.random() * 500));

async function request(path, options = {}) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  const token = typeof window !== 'undefined' ? localStorage.getItem('nyayaconnect-auth-token') : null;
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers
  };
  const res = await fetch(`${base}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
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
    confidence_score: null
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
        confidence_score: null // Calibrated confidence omitted unless produced by RAG model
      }
    };
  }
  await wait();
  const transcript = lang === 'Kannada' ? 'ನನ್ನನ್ನು ಬಂಧಿಸಿದರೆ ನನಗೆ ಯಾವ ಹಕ್ಕುಗಳಿವೆ?' : lang === 'Hindi' ? 'गिरफ्तार होने पर मेरे क्या अधिकार हैं?' : lang === 'Tamil' ? 'கைது செய்யப்பட்டால் ನನಗೆ என்ன உரிமைகள் உள்ளன?' : 'What are my rights if arrested?';
  return { transcript, lang, rag_response: responses.find(r => r.query_keywords.some(k => ['arrest', 'detention', 'article 22'].includes(k))) };
}

export async function createBooking(payload) {
  if (!mocked) {
    const res = await request('/bookings', {
      method: 'POST',
      body: JSON.stringify({
        lawyer_id: payload.lawyer_id,
        case_category: payload.category || (payload.lawyer ? payload.lawyer.category : 'Consumer'),
        issue_summary: payload.issue_summary || 'Legal consultation request',
        total_fee: payload.total_fee,
        client_name: payload.client_name || 'Citizen Client',
        client_phone: payload.client_phone || '+91-9876543210'
      })
    });
    if (res.access_token && typeof window !== 'undefined') {
      localStorage.setItem('nyayaconnect-auth-token', res.access_token);
    }
    const milestones = (res.milestones || []).map(m => ({
      stage_number: m.stage_number,
      name: m.stage_name,
      percentage: m.percentage,
      amount: m.amount,
      status: m.status === 'COMPLETED' ? 'Completed' : (m.status === 'IN_PROGRESS' ? 'In Progress' : 'Locked')
    }));
    return {
      ...payload,
      booking_id: res.booking_id,
      status: res.payment_status === 'Pending' ? 'pending' : res.payment_status,
      milestones: milestones.length ? milestones : payload.milestones
    };
  }
  await wait();
  return { ...payload, booking_id: `B${Date.now()}`, status: 'pending' };
}

export async function getBookings() {
  if (!mocked) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('nyayaconnect-auth-token') : null;
    if (!token) return [];
    try {
      const list = await request('/bookings');
      return list.map(b => ({
        booking_id: b.booking_id,
        lawyer_id: b.lawyer_id,
        lawyer_name: b.lawyer_name,
        category: b.category,
        issue_summary: b.issue_summary,
        total_fee: b.total_fee,
        status: b.status,
        created_at: b.created_at,
        lawyer: b.lawyer,
        milestones: (b.milestones || []).map(m => ({
          stage_number: m.stage_number,
          name: m.name,
          percentage: m.percentage,
          amount: m.amount,
          status: m.status
        }))
      }));
    } catch (err) {
      console.warn('Failed to load server bookings:', err);
      return [];
    }
  }
  await wait();
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem('nyayaconnect-bookings-v1') || '[]'); } catch { return []; }
}

export async function updateMilestone(bookingId, milestoneIndex, status) {
  if (!mocked) {
    const stageNo = milestoneIndex + 1; // 0-based to 1-based stage
    const normalizedStatus = status.toUpperCase().replace(/\s+/g, '_');
    const res = await request(`/bookings/${bookingId}/milestones/${stageNo}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: normalizedStatus })
    });
    return {
      bookingId,
      milestoneIndex,
      status: res.status === 'COMPLETED' ? 'Completed' : (res.status === 'IN_PROGRESS' ? 'In Progress' : 'Locked')
    };
  }
  await wait();
  return { bookingId, milestoneIndex, status };
}
