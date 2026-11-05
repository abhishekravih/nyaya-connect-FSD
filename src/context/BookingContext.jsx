'use client';
import {createContext,useContext,useEffect,useState} from 'react';
const Context=createContext(null);const KEY='nyayaconnect-bookings-v1';
export function BookingProvider({children}){const [bookings,setBookingsState]=useState([]),[chatSummary,setChatSummary]=useState('');const [ready,setReady]=useState(false);useEffect(()=>{try{setBookingsState(JSON.parse(localStorage.getItem(KEY)||'[]'))}catch{setBookingsState([])}setReady(true)},[]);const setBookings=value=>setBookingsState(previous=>{const next=typeof value==='function'?value(previous):value;if(typeof window!=='undefined')localStorage.setItem(KEY,JSON.stringify(next));return next});return <Context.Provider value={{bookings,setBookings,chatSummary,setChatSummary,ready}}>{children}</Context.Provider>}
export function useBooking(){return useContext(Context)}
