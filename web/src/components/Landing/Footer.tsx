"use client";

import Link from "next/link";

export default function Footer() {
    return (
        <footer className="pt-20 pb-12 px-8 border-t border-white/5 bg-black/60">
            <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-12">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                        <svg className="w-5 h-5 text-background" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                        </svg>
                    </div>
                    <span className="text-xl font-black tracking-tighter uppercase">Earnings AI</span>
                </div>

                <div className="flex gap-12 text-[10px] font-bold uppercase tracking-widest text-gray-500">
                    <Link href="#" className="hover:text-white transition-colors">Company Info</Link>
                    <Link href="#" className="hover:text-white transition-colors">Links</Link>
                    <Link href="#" className="hover:text-white transition-colors">Contact</Link>
                </div>

                <div className="text-[10px] text-gray-600 max-w-xs text-center md:text-right uppercase tracking-[0.2em] font-medium leading-[2]">
                    Financial predictions are for informational purposes only and not investment advice.
                    <div className="mt-4 flex justify-center md:justify-end gap-6 opacity-30 grayscale items-center">
                        <span className="hover:opacity-100 cursor-pointer transition-opacity">TWITTER</span>
                        <span className="hover:opacity-100 cursor-pointer transition-opacity">LINKEDIN</span>
                        <span className="hover:opacity-100 cursor-pointer transition-opacity">GITHUB</span>
                    </div>
                </div>
            </div>
            <div className="mt-16 pt-8 border-t border-white/5 text-center text-[10px] text-gray-700 font-bold tracking-[0.4em] uppercase">
                © 2026 EARNINGS AGENTS PROJECT. ALL RIGHTS RESERVED.
            </div>
        </footer>
    );
}
