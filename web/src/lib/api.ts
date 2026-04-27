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
    bull_factors: string[];
    bear_factors: string[];
    debate_summary?: string;
    rebuttal_summary?: string;
    agent_votes?: Record<string, string>;
    // Evaluation fields (populated by scoring task after earnings are reported)
    actual_direction?: string;
    actual_eps?: number;
    actual_price_move_pct?: number;
    accuracy_score?: number;  // Brier score — lower is better
    scored_at?: string;
}

export interface PredictionMetrics {
    total_predictions: number;
    scored_predictions: number;
    win_rate: number;              // fraction correct
    avg_confidence: number;        // mean predicted confidence
    avg_brier_score: number;       // mean Brier score (lower = better)
    beat_predictions: number;
    miss_predictions: number;
    beat_correct: number;
    miss_correct: number;
    direction_breakdown: Record<string, number>;
    agent_vote_breakdown: Record<string, Record<string, number>>;
    brier_over_time: Array<{ date: string; brier: number; ticker: string }>;
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

    async predictTicker(ticker: string, reportDate: string, token?: string, userAnalysis?: string): Promise<TaskResponse> {
        const url = `${API_BASE_URL}/earnings/predict/${ticker}`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                report_date: reportDate,
                user_analysis: userAnalysis
            })
        });
    },

    async getTaskStatus(taskId: string, token?: string): Promise<TaskStatusResponse> {
        const url = `${API_BASE_URL}/earnings/tasks/${taskId}`;
        return this.fetchWithAuth(url, token);
    },

    async getWeeklyPredictions(weekStart: string, token?: string): Promise<Prediction[]> {
        const url = new URL(`${API_BASE_URL}/earnings/weekly`);
        url.searchParams.append("week_start", weekStart);
        return this.fetchWithAuth(url.toString(), token);
    },

    async getPredictionHistory(token: string): Promise<Prediction[]> {
        const url = `${API_BASE_URL}/earnings/history`;
        return this.fetchWithAuth(url, token);
    },

    async chatWithConsensus(ticker: string, messages: { role: string, content: string }[], predictionId?: number, token?: string) {
        const url = `${API_BASE_URL}/earnings/chat`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticker,
                prediction_id: predictionId,
                messages
            })
        });
    },

    async getChatHistory(token: string) {
        const url = `${API_BASE_URL}/earnings/chat/history`;
        return this.fetchWithAuth(url, token);
    },

    async getDailyPredictions(targetDate: string, token?: string): Promise<Prediction[]> {
        const url = new URL(`${API_BASE_URL}/earnings/daily`);
        url.searchParams.append("target_date", targetDate);
        return this.fetchWithAuth(url.toString(), token);
    },

    async getCalendar(startDate?: string, endDate?: string, tickers?: string, useFinviz: boolean = false, timeframe: string = "This Week", indexName: string = "S&P 500", token?: string) {
        const url = new URL(`${API_BASE_URL}/earnings/calendar`);
        if (startDate) url.searchParams.append("start_date", startDate);
        if (endDate) url.searchParams.append("end_date", endDate);
        if (tickers) url.searchParams.append("tickers", tickers);
        if (useFinviz) {
            url.searchParams.append("use_finviz", "true");
            url.searchParams.append("timeframe", timeframe);
            url.searchParams.append("index_name", indexName);
        }
        return this.fetchWithAuth(url.toString(), token);
    },

    async getSentiment(ticker: string, daysBack: number = 30, token?: string) {
        const url = new URL(`${API_BASE_URL}/earnings/sentiment/${ticker}`);
        url.searchParams.append("days_back", daysBack.toString());
        return this.fetchWithAuth(url.toString(), token);
    },

    async predictBatch(companies: { ticker: string, report_date: string, user_analysis?: string }[], predictionDate?: string, token?: string): Promise<Prediction[]> {
        const url = `${API_BASE_URL}/earnings/batch`;
        return this.fetchWithAuth(url, token, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                companies,
                prediction_date: predictionDate || new Date().toISOString().split('T')[0]
            })
        });
    },

    async getMetrics(token: string): Promise<PredictionMetrics> {
        const url = `${API_BASE_URL}/earnings/metrics`;
        return this.fetchWithAuth(url, token);
    }
};

