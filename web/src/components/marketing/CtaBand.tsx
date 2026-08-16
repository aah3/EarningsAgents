"use client";

import Link from "next/link";
import { SignInButton, SignedIn, SignedOut } from "@clerk/nextjs";
import { ArrowRight } from "lucide-react";
import Container from "./Container";

export default function CtaBand() {
  return (
    <section className="py-20 md:py-28 border-t border-panel-line">
      <Container>
        <div className="relative overflow-hidden rounded-[24px] border border-teal/20 bg-panel-sunk/70 px-6 py-14 md:px-16 md:py-20 text-center">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 hero-aurora opacity-70"
          />
          <div className="relative">
            <h2 className="font-display font-semibold text-[clamp(1.8rem,3.4vw,2.75rem)] leading-[1.1] tracking-[-0.022em] text-ink mb-4 max-w-[18ch] mx-auto">
              Put a call on the record.
            </h2>
            <p className="font-body text-[16.5px] leading-[1.65] text-ink-mute max-w-[54ch] mx-auto mb-9">
              Pick a company, watch four agents fight over it, and get one
              confidence-scored verdict you can interrogate line by line.
            </p>
            <div className="flex items-center justify-center gap-3.5 flex-wrap">
              <SignedOut>
                <SignInButton mode="modal">
                  <button
                    className="font-body text-[15.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-[28px] py-3.5 rounded-[12px] transition-transform duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none cursor-pointer"
                    style={{ boxShadow: "0 8px 26px rgba(45, 212, 191, 0.32)" }}
                  >
                    Run a live prediction
                  </button>
                </SignInButton>
              </SignedOut>
              <SignedIn>
                <Link
                  href="/dashboard"
                  className="font-body text-[15.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-[28px] py-3.5 rounded-[12px] transition-transform duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none"
                  style={{ boxShadow: "0 8px 26px rgba(45, 212, 191, 0.32)" }}
                >
                  Open the dashboard
                </Link>
              </SignedIn>
              <Link
                href="/learn"
                className="font-body text-[15.5px] font-medium text-ink px-[22px] py-3.5 rounded-[12px] border border-panel-line inline-flex items-center gap-2 hover:border-ink-dim hover:bg-white/[0.03] transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none group"
              >
                Read the methodology
                <ArrowRight className="w-4 h-4 text-ink-mute group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
