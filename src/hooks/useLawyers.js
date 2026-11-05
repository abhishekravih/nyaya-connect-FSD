'use client';
import {useEffect,useState} from 'react';
import {getLawyers} from '../services/apiClient';
export function useLawyers(){const [lawyers,setLawyers]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');useEffect(()=>{let active=true;getLawyers().then(x=>active&&setLawyers(x)).catch(e=>active&&setError(e.message)).finally(()=>active&&setLoading(false));return()=>{active=false}},[]);return {lawyers,loading,error}}
