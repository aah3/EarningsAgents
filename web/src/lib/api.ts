const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Prediction {
    id?: number;
    ticker: string;
    company_name: string;
    report_date: string;
    prediction_date: string;
    direction: string;
    confidence: number;
    reasoning_summary: string;
    expected_price_move?: string;
    move_vs_implied?: string;
    guidance_expectation?: string;
    likely_guidance?: string;
    bull_factors: string[];
    bear_factors: string[];
    debate_summary?: string;
    rebuttal_summary?: string;
    agent_votes?: Record<string, string>;
    options_features?: Record<string, any>;
    sector?: string | null;
    // Evaluation fields (populated by scoring task after earnings are reported)
    actual_direction?: string;
    actual_eps?: number;
    expected_eps?: number;
    actual_price_move_pct?: number;
    accuracy_score?: number;  // Brier score — lower is better
    vol_stance_hit?: boolean;
    price_dir_hit?: boolean;
    guidance_stance_hit?: boolean;
    magnitude_error_pct?: number;
    actual_guidance_stance?: string;
    composite_accuracy_score?: number;
    scored_at?: string;
    report_timing?: string;
    // Fiscal reporting period (the period being reported on, not the one report_date falls in)
    fiscal_quarter?: string | null;   // "Q1".."Q4"
    fiscal_year?: number | null;
    fiscal_period?: string | null;    // pre-formatted, e.g. "2026Q1"
}

export type HistorySortKey =
    | "ticker"
    | "sector"
    | "analysis_date"
    | "report_date"
    | "fiscal_period"
    | "prediction"
    | "confidence"
    | "expected_eps"
    | "actual_eps"
    | "post_earnings_move"
    | "brier"
    | "outcome";

export interface HistoryQuery {
    limit?: number;
    offset?: number;
    sort_by?: HistorySortKey;
    sort_dir?: "asc" | "desc";
    q?: string;
    prediction?: string;      // BEAT | MISS | INLINE
    outcome?: string;         // CORRECT | WRONG | UNVERIFIED
    status?: string;          // SCORED | PENDING
    sector?: string;
    report_date?: string;     // YYYY-MM-DD
    fiscal_period?: string;   // e.g. 2026Q1
}

export interface HistoryStats {
    total: number;
    scored_count: number;
    correct_count: number;
    win_rate: number | null;        // fraction of scored predictions that were correct
    avg_brier: number | null;       // lower is better
    avg_confidence: number | null;  // 0–1
}

export interface HistoryPage {
    items: Prediction[];
    total: number;
    limit: number;
    offset: number;
    stats: HistoryStats;   // computed over the whole filtered set, not just this page
}

export interface HistoryFilterOptions {
    sectors: string[];
    fiscal_periods: string[];
    report_dates: string[];
}

export interface PredictionMetrics {
    total_predictions: number;
    scored_predictions: number;
    win_rate: number;              // fraction correct
    avg_confidence: number;        // mean predicted confidence
    avg_brier_score: number;       // mean Brier score (lower = better)
    vol_stance_hit_rate?: number;  // fraction vol stance correct
    price_dir_hit_rate?: number;   // fraction price direction correct
    guidance_stance_hit_rate?: number; // fraction guidance stance correct
    avg_magnitude_error_pct?: number;
    avg_composite_score?: number;  // mean composite score (0-100 scale)
    beat_predictions: number;
    miss_predictions: number;
    beat_correct: number;
    miss_correct: number;
    direction_breakdown: Record<string, number>;
    agent_vote_breakdown: Record<string, Record<string, number>>;
    brier_over_time: Array<{ date: string; brier: number; ticker: string; vol_stance_hit?: boolean; price_dir_hit?: boolean; guidance_stance_hit?: boolean; composite_score?: number }>;
    confidence_buckets: Array<{ bucket: string; predicted: number; actual_win_rate: number; count: number }>;
}


export interface TaskResponse {
    task_id: string;
    status: string;
    message: string;
}

export interface TaskStatusResponse {
    task_id: string;
    status: string;
    ready: boolean;
    result?: any;
    error?: string;
}

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const apiCache = new Map<string, CacheEntry<any>>();

export function normalizeTicker(ticker: string): string {
    if (!ticker) return "";
    return ticker.trim().toUpperCase().replace(/^\$/, "").replace(/^(NASDAQ|NYSE|AMEX):/i, "");
}

export const api = {
    fetchWithAuth(url: string, token?: string, options: RequestInit = {}) {
        return this.fetchWithAuthInternal(url, token, options);
    },

    async fetchWithAuthInternal(url: string, token?: string, options: RequestInit = {}) {
        const headers = new Headers(options.headers || {});
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }

        const res = await fetch(url, { ...options, headers });
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: "Unknown error" }));
            throw new Error(error.detail || "Request failed");
        }
        return res.json();
    },

    async health() {
        return this.fetchWithAuthInternal(`${API_BASE_URL}/health`);
    },

    async predictTicker(ticker: string, reportDate: string, token?: string, userAnalysis?: string, enableRebuttals?: boolean): Promise<TaskResponse> {
        const normTicker = normalizeTicker(ticker);
        const url = `${API_BASE_URL}/earnings/predict/${normTicker}`;
        return this.fetchWithAuthInternal(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                report_date: reportDate || null,
                user_analysis: userAnalysis,
                enable_rebuttals: enableRebuttals
            })
        });
    },

    async getTaskStatus(taskId: string, token?: string): Promise<TaskStatusResponse> {
        const url = `${API_BASE_URL}/earnings/tasks/${taskId}`;
        return this.fetchWithAuthInternal(url, token);
    },

    async getWeeklyPredictions(weekStart: string, token?: string): Promise<Prediction[]> {
        const url = new URL(`${API_BASE_URL}/earnings/weekly`);
        url.searchParams.append("week_start", weekStart);
        return this.fetchWithAuthInternal(url.toString(), token);
    },

    async getPredictionHistory(
        token: string,
        params: HistoryQuery = {},
        forceRefresh: boolean = false
    ): Promise<HistoryPage> {
        const url = new URL(`${API_BASE_URL}/earnings/history`);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                url.searchParams.append(key, String(value));
            }
        });
        // Cache per distinct query — a page of results is not interchangeable
        // with another page or another filter combination.
        const cacheKey = `history:${token || "anon"}:${url.searchParams.toString()}`;
        const now = Date.now();
        if (!forceRefresh && apiCache.has(cacheKey)) {
            const entry = apiCache.get(cacheKey)!;
            if (now - entry.timestamp < CACHE_TTL_MS) {
                return entry.data;
            }
        }
        const data = await this.fetchWithAuthInternal(url.toString(), token);
        apiCache.set(cacheKey, { data, timestamp: Date.now() });
        return data;
    },

    async getHistoryFilterOptions(token: string): Promise<HistoryFilterOptions> {
        const url = `${API_BASE_URL}/earnings/history/filters`;
        return this.fetchWithAuthInternal(url, token);
    },

    /** Drop every cached history response — call after a mutation (e.g. verify outcome). */
    invalidateHistoryCache() {
        Array.from(apiCache.keys())
            .filter((k) => k.startsWith("history:"))
            .forEach((k) => apiCache.delete(k));
    },

    async chatWithConsensus(ticker: string, messages: { role: string, content: string }[], predictionId?: number, token?: string) {
        const normTicker = normalizeTicker(ticker);
        const url = `${API_BASE_URL}/earnings/chat`;
        return this.fetchWithAuthInternal(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticker: normTicker,
                prediction_id: predictionId,
                messages
            })
        });
    },

    async getChatHistory(token: string) {
        const url = `${API_BASE_URL}/earnings/chat/history`;
        return this.fetchWithAuthInternal(url, token);
    },

    async getDailyPredictions(targetDate: string, token?: string): Promise<Prediction[]> {
        const url = new URL(`${API_BASE_URL}/earnings/daily`);
        url.searchParams.append("target_date", targetDate);
        return this.fetchWithAuthInternal(url.toString(), token);
    },

    async getCalendar(
        startDate?: string, 
        endDate?: string, 
        tickers?: string, 
        useFinviz: boolean = false, 
        timeframe: string = "This Week", 
        indexName: string = "S&P 500", 
        token?: string, 
        options: RequestInit = {},
        forceRefresh: boolean = false
    ) {
        const url = new URL(`${API_BASE_URL}/earnings/calendar`);
        if (startDate) url.searchParams.append("start_date", startDate);
        if (endDate) url.searchParams.append("end_date", endDate);
        if (tickers) url.searchParams.append("tickers", tickers.split(",").map(normalizeTicker).join(","));
        if (useFinviz) {
            url.searchParams.append("use_finviz", "true");
            url.searchParams.append("timeframe", timeframe);
            url.searchParams.append("index_name", indexName);
        }

        const cacheKey = `calendar:${url.toString()}`;
        const now = Date.now();
        if (!forceRefresh && apiCache.has(cacheKey)) {
            const entry = apiCache.get(cacheKey)!;
            if (now - entry.timestamp < CACHE_TTL_MS) {
                return entry.data;
            }
        }

        const data = await this.fetchWithAuthInternal(url.toString(), token, options);
        apiCache.set(cacheKey, { data, timestamp: Date.now() });
        return data;
    },

    async getSentiment(ticker: string, daysBack: number = 30, token?: string) {
        const normTicker = normalizeTicker(ticker);
        const url = new URL(`${API_BASE_URL}/earnings/sentiment/${normTicker}`);
        url.searchParams.append("days_back", daysBack.toString());
        return this.fetchWithAuth(url.toString(), token);
    },

    async predictBatch(companies: { ticker: string, report_date: string, user_analysis?: string }[], predictionDate?: string, token?: string): Promise<Prediction[]> {
        const url = `${API_BASE_URL}/earnings/batch`;
        const normalizedCompanies = companies.map(c => ({ ...c, ticker: normalizeTicker(c.ticker) }));
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                companies: normalizedCompanies,
                prediction_date: predictionDate || new Date().toISOString().split('T')[0]
            })
        });
    },

    async getMetrics(token: string, forceRefresh: boolean = false): Promise<PredictionMetrics> {
        const url = `${API_BASE_URL}/earnings/metrics`;
        const cacheKey = `metrics:${token || "anon"}`;
        const now = Date.now();
        if (!forceRefresh && apiCache.has(cacheKey)) {
            const entry = apiCache.get(cacheKey)!;
            if (now - entry.timestamp < CACHE_TTL_MS) {
                return entry.data;
            }
        }
        const data = await this.fetchWithAuth(url, token);
        apiCache.set(cacheKey, { data, timestamp: Date.now() });
        return data;
    },

    clearCache() {
        apiCache.clear();
    },

    async verifyPrediction(predictionId: number, token?: string, force: boolean = true) {
        apiCache.clear();
        const url = `${API_BASE_URL}/earnings/${predictionId}/verify?force=${force}`;
        return this.fetchWithAuth(url, token, {
            method: 'POST'
        });
    },

    async overridePredictionActuals(
        predictionId: number,
        data: {
            expected_eps?: number;
            actual_eps?: number;
            actual_price_move_pct?: number;
            actual_direction?: string;
            actual_guidance_stance?: string;
        },
        token?: string
    ) {
        apiCache.clear();
        const url = `${API_BASE_URL}/earnings/${predictionId}/override`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
    },

    async downloadReport(predictionId: number, format: 'md' | 'pdf', ticker: string, token?: string): Promise<void> {
        const url = `${API_BASE_URL}/earnings/${predictionId}/report?format=${format}`;
        const headers = new Headers();
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }
        
        const res = await fetch(url, { headers });
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: "Failed to download report" }));
            throw new Error(error.detail || "Failed to download report");
        }
        
        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.setAttribute('download', `${ticker}_earnings_debate_report.${format}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(downloadUrl);
    },

    async getSettings(token: string) {
        const url = `${API_BASE_URL}/earnings/settings`;
        return this.fetchWithAuth(url, token);
    },

    async updateSettings(settingsData: any, token: string) {
        const url = `${API_BASE_URL}/earnings/settings`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settingsData)
        });
    },

    async submitFeedback(category: string, message: string, pageContext?: string, token?: string) {
        const url = `${API_BASE_URL}/earnings/feedback`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                category,
                message,
                page_context: pageContext,
            })
        });
    },

    async getResearchThesis(ticker: string, token?: string): Promise<ResearchThesis> {
        const url = `${API_BASE_URL}/research/${normalizeTicker(ticker)}`;
        return this.fetchWithAuth(url, token);
    },

    async getResearchBaseline(ticker: string, token?: string): Promise<ResearchThesis> {
        const url = `${API_BASE_URL}/research/${normalizeTicker(ticker)}/baseline`;
        return this.fetchWithAuth(url, token);
    },

    async getResearchHistory(ticker: string, token?: string): Promise<ResearchHistoryResponse> {
        const url = `${API_BASE_URL}/research/${normalizeTicker(ticker)}/history`;
        return this.fetchWithAuth(url, token);
    },

    async triggerResearch(ticker: string, userNotes?: string, token?: string): Promise<TaskResponse> {
        apiCache.clear();
        const url = `${API_BASE_URL}/research/${normalizeTicker(ticker)}`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_notes: userNotes })
        });
    }
};

export interface ResearchThesis {
    id: number;
    ticker: string;
    company_name: string;
    user_id?: number | null;
    user_notes?: string | null;
    generated_at: string;
    source_trigger: string;
    headline_view: string;
    confidence_level: number;
    business_viability_summary: string;
    competitive_landscape_summary: string;
    macro_context_summary: string;
    bull_case: string;
    bear_case: string;
    catalysts: string[];
    risks: string[];
    evidence_table: Array<{
        evidence: string;
        source: string;
        implication: string;
        weight: string;
    }>;
    what_changed_summary?: string | null;
    disclaimer_shown: boolean;
    scope: "personalized" | "baseline";
}

export interface ResearchHistoryResponse {
    ticker: string;
    count: number;
    history: ResearchThesis[];
}


