/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx}'],
  theme: { extend: {
    colors: { background:'#0A0A0A', surface:'#141414', 'surface-2':'#1C1C1C', border:'#2A2A2A', peach:'#FFCBA4', orange:'#FF6B1A', 'orange-hover':'#FF8540', 'text-primary':'#FFF4EC', 'text-muted':'#A8A29E', civil:'#3B6CF0', consumer:'#14B8A6', criminal:'#E11D48' },
    fontFamily: { sans:['var(--font-inter)','sans-serif'], serif:['var(--font-playfair)','serif'] },
    backgroundImage: { 'peach-orange':'linear-gradient(110deg,#FFCBA4 0%,#FF6B1A 100%)' },
    boxShadow: { glow:'0 0 36px rgba(255,107,26,.18)' }
  }}, plugins: []
};
