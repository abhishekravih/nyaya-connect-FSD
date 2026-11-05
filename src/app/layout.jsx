import { Inter, Playfair_Display } from 'next/font/google';
import { MotionConfig } from 'framer-motion';
import './globals.css';
import Navbar from '../components/Navbar';
import { BookingProvider } from '../context/BookingContext';
import AskAiFloat from '../components/AskAiFloat';
const inter=Inter({subsets:['latin'],variable:'--font-inter'});
const playfair=Playfair_Display({subsets:['latin'],variable:'--font-playfair'});
export const metadata={title:'NyayaConnect | Justice, Made Accessible',description:'Connect with verified lawyers and find clear answers to constitutional questions.'};
export default function RootLayout({children}){return <html lang="en"><body className={`${inter.variable} ${playfair.variable}`}><MotionConfig reducedMotion="user"><BookingProvider><Navbar/>{children}<AskAiFloat/></BookingProvider></MotionConfig></body></html>}
