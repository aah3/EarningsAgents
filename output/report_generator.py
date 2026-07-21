"""
Report Generator for Earnings Prediction POC.
Generates beautiful, highly-formatted Markdown (.md) and PDF (.pdf) reports for earnings predictions.
"""

import os
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try importing fpdf2 for PDF generation
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    class FPDF:
        pass
    logger.warning("fpdf2 library not installed. PDF generation will be unavailable.")


def sanitize_for_pdf(text: str) -> str:
    """Sanitize unicode characters and emojis to prevent FPDF latin-1 encoding crashes."""
    if not text:
        return ""
    
    replacements = {
        "🐂": "[Bull Case]",
        "🐻": "[Bear Case]",
        "📊": "[Quant Case]",
        "🤝": "[Consensus]",
        "⚡": "[Options]",
        "🚀": "",
        "✓": "+",
        "×": "-",
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
        "\u2022": "*",
        "™": "(TM)",
        "®": "(R)",
        "©": "(C)",
    }
    
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    try:
        return text.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return text.encode('ascii', 'replace').decode('ascii')


def ensure_list(val: Any) -> List[str]:
    """Safely convert any JSON-string, list, or multiline string representing factors into a clean list of strings."""
    if not val:
        return []
    
    raw_items = []
    if isinstance(val, list):
        raw_items = [str(item) for item in val]
    elif isinstance(val, str):
        s = val.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                raw_items = [str(item) for item in parsed]
            else:
                raw_items = [str(parsed)]
        except Exception:
            if s.startswith("[") and s.endswith("]"):
                cleaned = s.strip("[]").replace('"', '').replace("'", "")
                raw_items = [item.strip() for item in cleaned.split(",") if item.strip()]
            elif "\n" in s:
                raw_items = [line.strip() for line in s.split("\n") if line.strip()]
            else:
                raw_items = [s]
    else:
        raw_items = [str(val)]
        
    cleaned_items = []
    for item in raw_items:
        clean_s = item.strip()
        # Remove common bullet prefixes so we avoid double bullets
        for prefix in ["-", "*", "•", "✓", "×", "+", "[Bull Case]", "[Bear Case]", "[Quant Case]"]:
            if clean_s.startswith(prefix):
                clean_s = clean_s[len(prefix):].strip()
        if clean_s:
            cleaned_items.append(clean_s)
            
    return cleaned_items


class PDFReport(FPDF):
    def __init__(self, ticker: str, company_name: str, direction_val: str = ""):
        super().__init__()
        self.ticker = ticker
        self.company_name = company_name
        self.direction_val = direction_val
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=18)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(100, 116, 139) # Slate 500
            self.cell(100, 6, f"AI EARNINGS DEBATE REPORT | {self.ticker} ({self.company_name})", align="L")
            self.cell(80, 6, f"Prediction: {self.direction_val}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(226, 232, 240) # Slate 200
            self.line(15, self.get_y(), 195, self.get_y())
            self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184) # Slate 400
        self.cell(0, 10, f"Page {self.page_no()} | Confidential - AI Agent Consensus Analysis", align="C")


def generate_markdown_report(
    prediction: Any, 
    elapsed_time: Optional[float] = None, 
    db_sync_status: str = "SUCCESSFUL",
    llm_info: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a Markdown report string for an earnings prediction."""
    ticker = prediction.ticker
    company_name = prediction.company_name
    
    report_date_str = prediction.report_date.strftime("%B %d, %Y") if hasattr(prediction.report_date, "strftime") else str(prediction.report_date)
    prediction_date_str = prediction.prediction_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(prediction.prediction_date, "strftime") else str(prediction.prediction_date)
    
    direction_val = prediction.direction.value.upper() if hasattr(prediction.direction, "value") else str(prediction.direction).upper()
    confidence_val = prediction.confidence
    if confidence_val <= 1.0:
        confidence_val *= 100
        
    elapsed_time_str = f"{elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes)" if elapsed_time else "N/A"
    
    # LLM Info
    provider = "N/A"
    model_name = "N/A"
    rebuttals_enabled = "N/A"
    if llm_info:
        provider = llm_info.get("provider", "N/A")
        model_name = llm_info.get("model_name", "N/A")
        rebuttals_enabled = "Yes" if llm_info.get("enable_rebuttals") else "No"
    
    # Option signals
    options_table = ""
    if prediction.options_features:
        opt = prediction.options_features
        implied_move = f"{opt.get('implied_move_pct', 0) * 100:.1f}%" if opt.get('implied_move_pct') else "N/A"
        pc_ratio = f"{opt.get('put_call_volume_ratio', 0):.2f}x" if opt.get('put_call_volume_ratio') else "N/A"
        atm_iv = f"{opt.get('atm_iv_call', 0) * 100:.1f}%" if opt.get('atm_iv_call') else "N/A"
        skew = f"{opt.get('iv_skew', 0) * 100:.1f}%" if opt.get('iv_skew') else "N/A"
        
        options_table = f"""
## Options Market Signals

| Signal | Value |
| :--- | :--- |
| **Implied Move** | {implied_move} |
| **Put/Call Volume Ratio** | {pc_ratio} |
| **ATM IV (Implied Vol)** | {atm_iv} |
| **IV Skew (Puts - Calls)** | {skew} |
"""

    # Guidance section
    guidance_exp_val = getattr(prediction, "guidance_expectation", None) or "N/A"
    likely_guidance_val = getattr(prediction, "likely_guidance", None) or ""
    guidance_sect = ""
    if guidance_exp_val != "N/A" or likely_guidance_val:
        likely_str = f"\n\n**Likely Guidance Detail**:\n{likely_guidance_val}" if likely_guidance_val else ""
        guidance_sect = f"## Guidance Outlook & Expectation\n\n- **Directional Expectation**: `{guidance_exp_val.upper()}`{likely_str}\n\n---\n\n"

    # Bull/Bear factors
    bull_list = ensure_list(prediction.bull_factors)
    bull_factors_str = "\n".join([f"- **✓** {f}" for f in bull_list]) if bull_list else "*No specific bullish factors logged.*"
        
    bear_list = ensure_list(prediction.bear_factors)
    bear_factors_str = "\n".join([f"- **×** {f}" for f in bear_list]) if bear_list else "*No specific bearish factors logged.*"

    debate_sect = ""
    if prediction.debate_summary:
        debate_sect = f"## Detailed Agent Debate (Pass 1 - Three-Agent Analysis)\n\n```\n{prediction.debate_summary.strip()}\n```\n\n---\n\n"

    rebuttal_sect = ""
    if prediction.rebuttal_summary:
        rebuttal_sect = f"## Rebuttal Round (Pass 2 - Cross-Examination)\n\n```\n{prediction.rebuttal_summary.strip()}\n```\n\n---\n\n"

    # Outcome Scored details (if scored)
    outcome_sect = ""
    if getattr(prediction, "actual_direction", None):
        actual_dir = prediction.actual_direction.upper()
        actual_eps = f"${prediction.actual_eps:.2f}" if prediction.actual_eps is not None else "N/A"
        actual_move = f"{prediction.actual_price_move_pct * 100:.2f}%" if prediction.actual_price_move_pct is not None else "N/A"
        brier = f"{prediction.accuracy_score:.4f}" if prediction.accuracy_score is not None else "N/A"
        scored_at_str = prediction.scored_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(prediction.scored_at, "strftime") else str(prediction.scored_at)
        
        outcome_sect = f"""
## Ex-Post Verification (Scored Outcome)

| Metric | Ground Truth Value |
| :--- | :--- |
| **Actual Direction** | **{actual_dir}** (VS Prediction: **{"CORRECT" if actual_dir == direction_val else "INCORRECT"}**) |
| **Actual Reported EPS** | {actual_eps} |
| **Post-Earnings Price Move** | {actual_move} |
| **Accuracy Score (Brier)** | {brier} (lower is better, 0.0 is perfect) |
| **Scored At** | {scored_at_str} |

---
"""

    desc_sect = ""
    if getattr(prediction, "company_description", None):
        desc_sect = f"## Company Description\n\n{prediction.company_description}\n\n---\n\n"

    md = f"""# AI Earnings Debate Report: {company_name} ({ticker})

This report details the execution and results of the Multi-Agent AI Earnings Debate for **{company_name} ({ticker})**, which reports earnings on **{report_date_str}**.

---

## Executive Summary

| Metric | Details |
| :--- | :--- |
| **Ticker** | **{ticker}** ({company_name}) |
| **Reporting Date** | {report_date_str} |
| **Consensus Prediction** | **{direction_val}** |
| **Confidence Level** | **{confidence_val:.1f}%** |
| **Expected Price Move** | {prediction.expected_price_move or 'N/A'} |
| **Move vs Implied** | {prediction.move_vs_implied or 'N/A'} |
| **Guidance Expectation** | {guidance_exp_val} |
| **Execution Duration** | {elapsed_time_str} |
| **Supabase DB Sync** | **{db_sync_status}** |
| **Run Timestamp** | {prediction_date_str} |

> [!NOTE]
> The prediction was generated using the **{model_name}** model via provider **{provider}**.
> Rebuttals were **{"enabled" if rebuttals_enabled == "Yes" else "disabled"}** during this execution.

---

{options_table}

---

{desc_sect}{guidance_sect}## Bull Case Factors

{bull_factors_str}

---

## Bear Case Factors

{bear_factors_str}

---

## Consensus Reasoning & Synthesis

{prediction.reasoning_summary}

---

{debate_sect}{rebuttal_sect}{outcome_sect}> **Not investment advice.** This report is AI-generated and may be wrong. It is provided for informational and research purposes only and does not constitute financial, investment, or trading advice. Do your own research before making any financial decision.
"""
    return md


def generate_pdf_report(
    prediction: Any,
    output_path: Path,
    elapsed_time: Optional[float] = None,
    db_sync_status: str = "SUCCESSFUL",
    llm_info: Optional[Dict[str, Any]] = None
) -> None:
    """Generate a high-quality PDF report for an earnings prediction using fpdf2."""
    if not FPDF_AVAILABLE:
        raise RuntimeError("fpdf2 is not available. Cannot generate PDF report.")
        
    ticker = prediction.ticker
    company_name = prediction.company_name
    
    report_date_str = prediction.report_date.strftime("%B %d, %Y") if hasattr(prediction.report_date, "strftime") else str(prediction.report_date)
    prediction_date_str = prediction.prediction_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(prediction.prediction_date, "strftime") else str(prediction.prediction_date)
    
    direction_val = prediction.direction.value.upper() if hasattr(prediction.direction, "value") else str(prediction.direction).upper()
    confidence_val = prediction.confidence
    if confidence_val <= 1.0:
        confidence_val *= 100
        
    elapsed_time_str = f"{elapsed_time:.2f}s ({elapsed_time/60.0:.1f}m)" if elapsed_time else "N/A"
    
    pdf = PDFReport(ticker, company_name, direction_val)
    pdf.add_page()
    
    # ----------------------------------------------------
    # Top Header Banner (Page 1)
    # ----------------------------------------------------
    pdf.set_fill_color(15, 23, 42) # Slate 900
    pdf.rect(0, 0, 210, 28, "F")
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.text(15, 12, "AI EARNINGS DEBATE REPORT")
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(203, 213, 225) # Slate 300
    pdf.text(15, 20, sanitize_for_pdf(f"{company_name} ({ticker})  |  Release: {report_date_str}"))
    
    # Prediction Badge on top right
    badge_bg = (22, 163, 74) if "BEAT" in direction_val else ((220, 38, 38) if "MISS" in direction_val else (37, 99, 235))
    pdf.set_fill_color(*badge_bg)
    pdf.rect(145, 7, 50, 14, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.text(150, 16, sanitize_for_pdf(f"CALL: {direction_val}"))
    
    pdf.set_y(34)
    
    # Printable width: 210 - 30 = 180mm
    epw = 180
    
    # ----------------------------------------------------
    # 1. Executive Summary Table
    # ----------------------------------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(30, 41, 59) # Slate 800
    pdf.set_text_color(255, 255, 255)
    pdf.cell(epw, 7, "  EXECUTIVE SUMMARY", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    summary_data = [
        ("Ticker", ticker),
        ("Company Name", company_name),
        ("Reporting Date", report_date_str),
        ("Consensus Prediction", direction_val),
        ("Confidence Level", f"{confidence_val:.1f}%"),
        ("Expected Price Move", prediction.expected_price_move or "N/A"),
        ("Move vs Implied", prediction.move_vs_implied or "N/A"),
        ("Guidance Expectation", getattr(prediction, "guidance_expectation", None) or "N/A"),
        ("Execution Time", elapsed_time_str),
        ("Database Sync", db_sync_status),
        ("Run Timestamp", prediction_date_str)
    ]
    
    col1_w = 60
    col2_w = 120
    
    row_count = 0
    for label, val in summary_data:
        fill_color = (248, 250, 252) if row_count % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        pdf.set_draw_color(226, 232, 240)
        
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(51, 65, 85) # Slate 700
        pdf.cell(col1_w, 6, f"  {sanitize_for_pdf(label)}", border=1, fill=True)
        
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(15, 23, 42) # Slate 900
        pdf.cell(col2_w, 6, f"  {sanitize_for_pdf(val)}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        row_count += 1
        
    pdf.ln(6)
    
    # ----------------------------------------------------
    # 2. Options Signals Table (if present)
    # ----------------------------------------------------
    if prediction.options_features:
        opt = prediction.options_features
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 7, "  OPTIONS MARKET SIGNALS", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        options_data = [
            ("Implied Move", f"{opt.get('implied_move_pct', 0) * 100:.1f}%" if opt.get('implied_move_pct') else "N/A"),
            ("Put/Call Volume Ratio", f"{opt.get('put_call_volume_ratio', 0):.2f}x" if opt.get('put_call_volume_ratio') else "N/A"),
            ("ATM IV (Implied Vol)", f"{opt.get('atm_iv_call', 0) * 100:.1f}%" if opt.get('atm_iv_call') else "N/A"),
            ("IV Skew (Puts - Calls)", f"{opt.get('iv_skew', 0) * 100:.1f}%" if opt.get('iv_skew') else "N/A")
        ]
        
        r_idx = 0
        for label, val in options_data:
            fill_color = (248, 250, 252) if r_idx % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill_color)
            pdf.set_draw_color(226, 232, 240)
            
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(col1_w, 6, f"  {sanitize_for_pdf(label)}", border=1, fill=True)
            
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(col2_w, 6, f"  {sanitize_for_pdf(val)}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            r_idx += 1
            
        pdf.ln(6)
        
    # ----------------------------------------------------
    # 3. Company Description (if present)
    # ----------------------------------------------------
    if getattr(prediction, "company_description", None):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 7, "  COMPANY OVERVIEW", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(epw, 5, sanitize_for_pdf(prediction.company_description), border=1, fill=True)
        pdf.ln(6)

    # ----------------------------------------------------
    # 4. Guidance Outlook & Likely Specifics (if present)
    # ----------------------------------------------------
    guidance_exp_val = getattr(prediction, "guidance_expectation", None) or "N/A"
    likely_guidance_val = getattr(prediction, "likely_guidance", None) or ""
    
    if guidance_exp_val != "N/A" or likely_guidance_val:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(217, 119, 6) # Amber 600
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 7, "  GUIDANCE OUTLOOK & SPECIFICS", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_fill_color(254, 243, 199) # Amber 100
        pdf.set_draw_color(253, 230, 138) # Amber 200
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(120, 53, 15) # Amber 900
        
        g_text = f"Directional Expectation: {guidance_exp_val.upper()}"
        if likely_guidance_val:
            g_text += f"\nLikely Guidance Detail:\n{likely_guidance_val}"
            
        pdf.multi_cell(epw, 5, sanitize_for_pdf(g_text), border=1, fill=True)
        pdf.ln(6)

    # ----------------------------------------------------
    # 5. Bull Factors (Green Card Box)
    # ----------------------------------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(22, 163, 74) # Green 600
    pdf.set_text_color(255, 255, 255)
    pdf.cell(epw, 7, "  BULL FACTORS (EPS BEAT DRIVERS)", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_fill_color(240, 253, 244) # Green 50
    pdf.set_draw_color(187, 247, 208) # Green 200
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(20, 83, 45) # Green 900
    
    bull_list = ensure_list(prediction.bull_factors)
    if bull_list:
        bull_text = "\n".join([f"+  {f}" for f in bull_list])
    else:
        bull_text = "No specific bullish factors logged."
        
    pdf.multi_cell(epw, 5.5, sanitize_for_pdf(bull_text), border=1, fill=True)
    pdf.ln(6)
    
    # ----------------------------------------------------
    # 6. Bear Factors (Red Card Box)
    # ----------------------------------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(220, 38, 38) # Red 600
    pdf.set_text_color(255, 255, 255)
    pdf.cell(epw, 7, "  BEAR FACTORS (EARNINGS RISKS & HEADWINDS)", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_fill_color(254, 242, 242) # Red 50
    pdf.set_draw_color(254, 202, 202) # Red 200
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(127, 29, 29) # Red 900
    
    bear_list = ensure_list(prediction.bear_factors)
    if bear_list:
        bear_text = "\n".join([f"-  {f}" for f in bear_list])
    else:
        bear_text = "No specific bearish factors logged."
        
    pdf.multi_cell(epw, 5.5, sanitize_for_pdf(bear_text), border=1, fill=True)
    pdf.ln(6)
    
    # ----------------------------------------------------
    # 7. Consensus Synthesis & Reasoning (Purple/Indigo Box)
    # ----------------------------------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(79, 70, 229) # Indigo 600
    pdf.set_text_color(255, 255, 255)
    pdf.cell(epw, 7, "  CONSENSUS SYNTHESIS & REASONING", fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_fill_color(245, 243, 255) # Indigo 50
    pdf.set_draw_color(221, 214, 254) # Indigo 200
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(49, 46, 129) # Indigo 900
    pdf.multi_cell(epw, 5.5, sanitize_for_pdf(prediction.reasoning_summary), border=1, fill=True)
    pdf.ln(6)
    
    # ----------------------------------------------------
    # 8. Detailed Agent Debate (Pass 1 - Three-Agent Analysis)
    # ----------------------------------------------------
    if prediction.debate_summary:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(71, 85, 105) # Slate 600
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 7, "  DETAILED AGENT DEBATE (PASS 1)", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_fill_color(241, 245, 249) # Slate 100
        pdf.set_draw_color(203, 213, 225) # Slate 300
        pdf.set_font("Courier", "", 8.5)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(epw, 4.5, sanitize_for_pdf(prediction.debate_summary.strip()), border=1, fill=True)
        pdf.ln(6)
        
    # ----------------------------------------------------
    # 9. Rebuttal Round (Pass 2 - Cross-Examination)
    # ----------------------------------------------------
    if prediction.rebuttal_summary:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(13, 148, 136) # Teal 600
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 7, "  REBUTTAL ROUND (PASS 2 - CROSS-EXAMINATION)", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_fill_color(240, 253, 250) # Teal 50
        pdf.set_draw_color(153, 246, 228) # Teal 200
        pdf.set_font("Courier", "", 8.5)
        pdf.set_text_color(19, 78, 74) # Teal 900
        pdf.multi_cell(epw, 4.5, sanitize_for_pdf(prediction.rebuttal_summary.strip()), border=1, fill=True)
        pdf.ln(6)

    # ----------------------------------------------------
    # 10. Outcome Scored Details (if scored)
    # ----------------------------------------------------
    if getattr(prediction, "actual_direction", None):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(epw, 7, "  EX-POST VERIFICATION (SCORED OUTCOME)", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        actual_dir = prediction.actual_direction.upper()
        actual_eps = f"${prediction.actual_eps:.2f}" if prediction.actual_eps is not None else "N/A"
        actual_move = f"{prediction.actual_price_move_pct * 100:.2f}%" if prediction.actual_price_move_pct is not None else "N/A"
        brier = f"{prediction.accuracy_score:.4f}" if prediction.accuracy_score is not None else "N/A"
        scored_at_str = prediction.scored_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(prediction.scored_at, "strftime") else str(prediction.scored_at)
        
        outcome_data = [
            ("Actual Direction", f"{actual_dir} ({'CORRECT' if actual_dir == direction_val else 'INCORRECT'})"),
            ("Actual Reported EPS", actual_eps),
            ("Post-Earnings Price Move", actual_move),
            ("Accuracy Score (Brier)", brier),
            ("Scored At", scored_at_str)
        ]
        
        r_idx = 0
        for label, val in outcome_data:
            fill_color = (248, 250, 252) if r_idx % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill_color)
            pdf.set_draw_color(226, 232, 240)
            
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(col1_w, 6, f"  {sanitize_for_pdf(label)}", border=1, fill=True)
            
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(col2_w, 6, f"  {sanitize_for_pdf(val)}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            r_idx += 1
            
        pdf.ln(6)

    # ----------------------------------------------------
    # Disclaimer
    # ----------------------------------------------------
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(
        epw, 4,
        "Not investment advice. This report is AI-generated and may be wrong. It is provided for "
        "informational and research purposes only and does not constitute financial, investment, or "
        "trading advice. Do your own research before making any financial decision."
    )

    # Write to output file
    pdf.output(str(output_path))


def export_report(
    prediction: Any,
    reports_dir: Path,
    elapsed_time: Optional[float] = None,
    db_sync_status: str = "SUCCESSFUL",
    llm_info: Optional[Dict[str, Any]] = None,
    formats: Optional[List[str]] = None
) -> Dict[str, Path]:
    """
    Generate and save reports to reports_dir.
    Returns dict mapping format name -> Path to saved report file.
    """
    if formats is None:
        formats = ["md", "pdf"]
        
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    ticker = prediction.ticker
    report_date_val = prediction.report_date
    date_str = report_date_val.strftime("%Y-%m-%d") if hasattr(report_date_val, "strftime") else str(report_date_val)
    
    base_filename = f"{ticker}_{date_str}_report"
    saved_paths = {}
    
    # 1. MD Format
    if "md" in formats:
        md_content = generate_markdown_report(prediction, elapsed_time, db_sync_status, llm_info)
        md_path = reports_dir / f"{base_filename}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        saved_paths["md"] = md_path
        logger.info(f"Saved Markdown report to {md_path}")
        
    # 2. PDF Format
    if "pdf" in formats:
        if FPDF_AVAILABLE:
            pdf_path = reports_dir / f"{base_filename}.pdf"
            try:
                generate_pdf_report(prediction, pdf_path, elapsed_time, db_sync_status, llm_info)
                saved_paths["pdf"] = pdf_path
                logger.info(f"Saved PDF report to {pdf_path}")
            except Exception as e:
                logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
        else:
            logger.warning("Cannot generate PDF report: fpdf2 is not installed.")
            
    return saved_paths
