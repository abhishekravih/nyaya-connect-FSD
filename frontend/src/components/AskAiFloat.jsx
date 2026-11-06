'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {MessageCircle} from 'lucide-react';
export default function AskAiFloat(){const path=usePathname();if(!['/marketplace','/dashboard'].includes(path))return null;return <Link href="/chat" aria-label="Ask AI a legal question" className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-full border border-peach/30 bg-orange px-4 py-3 text-sm font-semibold text-background shadow-[0_0_28px_rgba(255,107,26,.28)] transition hover:-translate-y-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-peach"><MessageCircle size={18}/>Ask AI</Link>}
