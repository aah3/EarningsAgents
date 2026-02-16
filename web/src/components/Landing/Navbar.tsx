"use client";

import Link from "next/link";

export default function Navbar() {
    return (
        <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center justify-between px-8 py-4 glass rounded-full w-[90%] max-w-7xl shadow-2xl">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center shadow-lg">
                    <svg className="w-6 h-6 text-background" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                </div>
                <span className="text-xl font-black tracking-tighter uppercase">Earnings AI</span>
            </div>

            <div className="hidden lg:flex items-center gap-10 text-xs font-bold uppercase tracking-widest text-gray-400">
                <Link href="#" className="hover:text-accent transition-colors">Home</Link>
                <Link href="#" className="hover:text-accent transition-colors">How It Works</Link>
                <Link href="#" className="hover:text-accent transition-colors">Live</Link>
                <Link href="#" className="hover:text-accent transition-colors">Predictions</Link>
                <Link href="#" className="hover:text-accent transition-colors">API</Link>
            </div>

            <button className="px-6 py-2.5 bg-accent text-background rounded-full text-xs font-black uppercase tracking-wider hover:scale-105 transition-all shadow-xl">
                Try Free Demo
            </button>
        </nav>
    );
}
