const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Prediction {
    ticker: string;
    company_name: string;
    report_date: string;
    prediction_date: string;
    direction: string;
    confidence: number;
    reasoning_summary: string;
    bull_factors: string[];
    bear_factors: string[];
    agent_votes?: Record<string, string>;
}

export const api = {
    async fetchWithAuth(url: string, token?: string, options: RequestInit = {}) {
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
        return this.fetchWithAuth(`${API_BASE_URL}/health`);
    },

    async predictTicker(ticker: string, reportDate: string, token?: string): Promise<Prediction> {
        const url = new URL(`${API_BASE_URL}/earnings/predict/${ticker}`);
        url.searchParams.append("report_date", reportDate);
        return this.fetchWithAuth(url.toString(), token);
    },

    async getWeeklyPredictions(weekStart: string, token?: string): Promise<Prediction[]> {
        const url = new URL(`${API_BASE_URL}/earnings/weekly`);
        url.searchParams.append("week_start", weekStart);
        return this.fetchWithAuth(url.toString(), token);
    }
};
