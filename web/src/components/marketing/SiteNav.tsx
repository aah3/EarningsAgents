"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import { Menu, X } from "lucide-react";
import Container from "./Container";

/** Every entry resolves to something that exists. The old nav shipped four
 *  `href="#"` placeholders (Live, Predictions, Leaderboard, API) that silently
 *  did nothing when clicked. */
const LINKS = [
  { label: "How it works", href: "/#how-it-works" },
  { label: "The committee", href: "/#agents" },
  { label: "Track record", href: "/#track-record" },
  { label: "Methodology", href: "/learn" },
];

export default function SiteNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 transition-colors duration-200 ${
        scrolled
          ? "bg-bg/80 backdrop-blur-xl border-b border-panel-line"
          : "bg-transparent border-b border-transparent"
      }`}
    >
      <Container>
        <nav className="flex items-center justify-between py-4">
          <Link
            href="/"
            className="flex items-center gap-[11px] font-display font-bold text-[19px] tracking-[-0.01em] text-ink select-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none rounded-lg"
          >
            <span
              className="w-[30px] h-[30px] rounded-[9px] bg-gradient-to-br from-teal to-teal-deep grid place-items-center"
              style={{ boxShadow: "0 0 22px rgba(45, 212, 191, 0.45)" }}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                <path d="M12 3l8 4.5-8 4.5-8-4.5L12 3z" fill="#04231F" />
                <path d="M4 12l8 4.5 8-4.5" stroke="#04231F" strokeWidth="1.6" fill="none" />
                <path d="M4 16.2l8 4.5 8-4.5" stroke="#04231F" strokeWidth="1.6" fill="none" />
              </svg>
            </span>
            EarningsAI
          </Link>

          <ul className="hidden lg:flex items-center gap-8 list-none">
            {LINKS.map((l) => (
              <li key={l.label}>
                <Link
                  href={l.href}
                  className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-3">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="hidden sm:block text-ink-mute hover:text-ink font-body text-[14.5px] font-[450] transition-colors outline-none cursor-pointer px-1 py-0.5">
                  Login
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button
                  className="font-body text-[14.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-5 py-2.5 rounded-[10px] transition-transform duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none cursor-pointer"
                  style={{ boxShadow: "0 6px 22px rgba(45, 212, 191, 0.28)" }}
                >
                  Sign Up
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/dashboard"
                className="font-body text-[14.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-5 py-2.5 rounded-[10px] transition-transform duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none"
                style={{ boxShadow: "0 6px 22px rgba(45, 212, 191, 0.28)" }}
              >
                Dashboard
              </Link>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>

            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={open ? "Close menu" : "Open menu"}
              className="lg:hidden w-9 h-9 grid place-items-center rounded-[10px] border border-panel-line text-ink-mute hover:text-ink transition-colors focus-visible:ring-2 focus-visible:ring-teal outline-none cursor-pointer"
            >
              {open ? <X className="w-[18px] h-[18px]" /> : <Menu className="w-[18px] h-[18px]" />}
            </button>
          </div>
        </nav>
      </Container>

      {open && (
        <div className="lg:hidden border-t border-panel-line bg-bg/95 backdrop-blur-xl">
          <Container>
            <ul className="flex flex-col py-2 list-none">
              {LINKS.map((l) => (
                <li key={l.label}>
                  <Link
                    href={l.href}
                    onClick={() => setOpen(false)}
                    className="block py-3 font-body text-[15px] text-ink-mute hover:text-ink transition-colors border-b border-panel-line last:border-0"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </Container>
        </div>
      )}
    </header>
  );
}
