"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ResearchThesis } from "@/lib/api";

/**
 * Shared thesis state for a ticker.
 *
 * `ResearchThesisView` is rendered from two mutually exclusive branches of
 * AnalysisResult — the summary embedded in the prediction tab, and the full
 * view in the research tab. Switching tabs unmounts one and mounts the other,
 * and `api.getResearchThesis` is uncached, so every switch re-ran the request
 * and flashed the loading state. Holding the last result in a module-scoped
 * cache keyed by ticker means the second mount renders immediately.
 *
 * This is deliberately a cache, not a store: `refetch` always hits the network,
 * and `invalidateThesis` is called after a generation is triggered so the
 * polling read cannot serve a stale entry.
 */

type CacheEntry = { thesis: ResearchThesis | null; at: number };

const CACHE_TTL_MS = 5 * 60 * 1000;
const cache = new Map<string, CacheEntry>();

/** Drop a ticker's cached thesis (or the whole cache when called bare). */
export function invalidateThesis(ticker?: string) {
    if (ticker) cache.delete(ticker.toUpperCase());
    else cache.clear();
}

export function useResearchThesis(ticker: string) {
    const { getToken } = useAuth();
    const key = (ticker || "").toUpperCase();
    const cached = cache.get(key);
    const fresh = cached && Date.now() - cached.at < CACHE_TTL_MS;

    const [thesis, setThesisState] = useState<ResearchThesis | null>(fresh ? cached.thesis : null);
    // Only show the loading state when there is nothing to render yet.
    const [loading, setLoading] = useState(!fresh);
    const [error, setError] = useState<string | null>(null);

    /** Set locally and seed the cache, so a remount shows the same thing. */
    const setThesis = useCallback((next: ResearchThesis | null) => {
        setThesisState(next);
        if (key) cache.set(key, { thesis: next, at: Date.now() });
    }, [key]);

    const fetchThesis = useCallback(async () => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.getResearchThesis(ticker, token);
            setThesisState(res);
            cache.set(key, { thesis: res, at: Date.now() });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err);
            if (msg.includes("404")) {
                // No thesis yet is an empty state, not an error.
                setThesisState(null);
                cache.set(key, { thesis: null, at: Date.now() });
            } else {
                setError(msg || "Failed to load research thesis.");
            }
        } finally {
            setLoading(false);
        }
    }, [ticker, key, getToken]);

    useEffect(() => {
        const entry = cache.get(key);
        if (entry && Date.now() - entry.at < CACHE_TTL_MS) {
            setThesisState(entry.thesis);
            setLoading(false);
            return;
        }
        fetchThesis();
    }, [key, fetchThesis]);

    return { thesis, setThesis, loading, error, refetch: fetchThesis };
}
