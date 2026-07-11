"use client";

import React from "react";
import Link from "next/link";
import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

export default function SiteNav() {
  return (
    <nav className="w-full max-w-[1240px] mx-auto px-10 max-[940px]:px-6 py-[22px] flex items-center justify-between">
      {/* Brand logo & text */}
      <Link
        href="/"
        className="brand flex items-center gap-[11px] font-display font-bold text-[19px] tracking-[-0.01em] text-ink select-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none rounded-lg"
      >
        <span
          className="logo w-[30px] h-[30px] rounded-[9px] bg-gradient-to-br from-teal to-teal-deep grid place-items-center text-[#04231F] font-bold"
          style={{ boxShadow: "0 0 22px rgba(45, 212, 191, 0.45)" }}
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
            <path d="M12 3l8 4.5-8 4.5-8-4.5L12 3z" fill="#04231F" />
            <path
              d="M4 12l8 4.5 8-4.5"
              stroke="#04231F"
              strokeWidth="1.6"
              fill="none"
            />
            <path
              d="M4 16.2l8 4.5 8-4.5"
              stroke="#04231F"
              strokeWidth="1.6"
              fill="none"
            />
          </svg>
        </span>
        EarningsAI
      </Link>

      {/* Nav Center Links */}
      <ul className="nav-links flex items-center gap-[34px] list-none max-[940px]:hidden">
        <li>
          <Link
            href="/learn#how-it-works"
            className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
          >
            How it works
          </Link>
        </li>
        <li>
          <Link
            href="/learn"
            className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
          >
            Learn
          </Link>
        </li>
        <li>
          <Link
            href="#"
            className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
          >
            Live
          </Link>
        </li>
        <li>
          <Link
            href="#"
            className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
          >
            Predictions
          </Link>
        </li>
        <li>
          <Link
            href="#"
            className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
          >
            Leaderboard
          </Link>
        </li>
        <li>
          <Link
            href="#"
            className="text-ink-mute hover:text-ink transition-colors duration-150 text-[14.5px] font-[450] font-body focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm px-1 py-0.5"
          >
            API
          </Link>
        </li>
      </ul>

      {/* Right CTA / Auth Status */}
      <div className="flex items-center gap-4">
        <SignedOut>
          <SignInButton mode="modal">
            <button className="text-ink-mute hover:text-ink font-body text-[14.5px] font-[450] transition-colors outline-none cursor-pointer px-1 py-0.5">
              Login
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button
              className="nav-cta font-body text-[14.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-5 py-2.5 rounded-[10px] transition-all duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none cursor-pointer"
              style={{ boxShadow: "0 6px 22px rgba(45, 212, 191, 0.28)" }}
            >
              Sign Up
            </button>
          </SignUpButton>
        </SignedOut>
        <SignedIn>
          <Link
            href="/dashboard"
            className="nav-cta font-body text-[14.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-5 py-2.5 rounded-[10px] transition-all duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none"
            style={{ boxShadow: "0 6px 22px rgba(45, 212, 191, 0.28)" }}
          >
            Dashboard
          </Link>
          <UserButton afterSignOutUrl="/" />
        </SignedIn>
      </div>
    </nav>
  );
}
