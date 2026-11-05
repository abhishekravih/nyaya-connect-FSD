import {Suspense} from 'react';
import MarketplaceGrid from '../../components/MarketplaceGrid';
export default function MarketplacePage(){return <main className="page-shell min-h-screen px-5 pb-20 pt-28 sm:px-8 sm:pt-32"><div className="mx-auto max-w-7xl"><Suspense fallback={<div className="h-96 animate-pulse rounded-2xl bg-surface"/>}><MarketplaceGrid/></Suspense></div></main>}
