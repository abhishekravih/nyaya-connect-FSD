'use client';
import {createContext, useContext, useEffect, useState} from 'react';
import {getBookings} from '../services/apiClient';

const Context = createContext(null);
const KEY = 'nyayaconnect-bookings-v1';

export function BookingProvider({children}) {
  const [bookings, setBookingsState] = useState([]);
  const [chatSummary, setChatSummary] = useState('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    async function init() {
      try {
        const liveList = await getBookings();
        if (active && liveList && liveList.length > 0) {
          setBookingsState(liveList);
          if (typeof window !== 'undefined') {
            localStorage.setItem(KEY, JSON.stringify(liveList));
          }
        } else if (active) {
          const cached = JSON.parse(localStorage.getItem(KEY) || '[]');
          setBookingsState(cached);
        }
      } catch {
        if (active) {
          const cached = JSON.parse(localStorage.getItem(KEY) || '[]');
          setBookingsState(cached);
        }
      } finally {
        if (active) setReady(true);
      }
    }
    init();
    return () => { active = false; };
  }, []);

  const setBookings = value => setBookingsState(previous => {
    const next = typeof value === 'function' ? value(previous) : value;
    if (typeof window !== 'undefined') localStorage.setItem(KEY, JSON.stringify(next));
    return next;
  });

  return (
    <Context.Provider value={{bookings, setBookings, chatSummary, setChatSummary, ready}}>
      {children}
    </Context.Provider>
  );
}

export function useBooking() {
  return useContext(Context);
}
