"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { UserButton, useUser } from "@clerk/nextjs";

const navItems = [
    { name: "Overview", href: "/dashboard", icon: "📊" },
    { name: "Predictions", href: "/dashboard/predictions", icon: "📈" },
    { name: "History", href: "/dashboard/history", icon: "📜" },
    { name: "Settings", href: "/dashboard/settings", icon: "⚙️" },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { user } = useUser();

    return (
        <aside className="w-64 border-r border-white/5 bg-black/40 flex flex-col h-screen fixed left-0 top-0">
            <div className="p-8 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shadow-lg">
                        <svg className="w-5 h-5 text-background" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                        </svg>
                    </div>
                    <span className="text-lg font-black tracking-tighter uppercase">Earnings AI</span>
                </div>
            </div>

            <nav className="flex-1 p-4 space-y-2 mt-4">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all font-bold text-sm ${isActive
                                ? "bg-accent text-background shadow-lg"
                                : "text-gray-400 hover:bg-white/5 hover:text-white"
                                }`}
                        >
                            <span className="text-xl">{item.icon}</span>
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-6 border-t border-white/5">
                <div className="flex items-center justify-between p-3 glass rounded-2xl">
                    <div className="flex items-center gap-3 min-w-0">
                        <UserButton afterSignOutUrl="/" />
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold truncate">{user?.firstName || "User"}</p>
                            <p className="text-[10px] text-gray-500 truncate">Pro Member</p>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
