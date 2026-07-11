"""
Report Generator for Earnings Prediction POC.
Generates beautiful Markdown (.md) and PDF (.pdf) reports for earnings predictions.
"""

import os
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
    }
    
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    # Replace any other non-latin-1 characters with a question mark
    try:
        return text.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        # Fallback to ascii replacement
        return text.encode('ascii', 'replace').decode('ascii')


def ensure_list(val: Any) -> List[str]:
    """Safely convert any JSON-string or list representing factors into a list of strings."""
    if not val:
        return []
    if isinstance(val, list):
        return [str(item) for item in val]
    if isinstance(val, str):
        import json
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            return [str(parsed)]
        except Exception:
            # Maybe it's a comma-separated list or a single string
            if val.startswith("[") and val.endswith("]"):
                # Clean up brackets manually if JSON parse failed
                cleaned = val.strip("[]").replace('"', '').replace("'", "")
                return [item.strip() for item in cleaned.split(",") if item.strip()]
            return [val]
    return [str(val)]



class PDFReport(FPDF):
    def __init__(self, ticker: str, company_name: str):
        super().__init__()
        self.ticker = ticker
        self.company_name = company_name
        self.set_margins(15, 15, 15) # Use uniform margins
        
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()} | AI Earnings Agent Consensus Report", align="C")




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

    # Bull/Bear factors
    bull_list = ensure_list(prediction.bull_factors)
    bull_factors_str = "\n".join([f"- **✓** {f}" for f in bull_list]) if bull_list else "*No specific bullish factors logged.*"
        
    bear_list = ensure_list(prediction.bear_factors)
    bear_factors_str = "\n".join([f"- **×** {f}" for f in bear_list]) if bear_list else "*No specific bearish factors logged.*"

    debate_sect = ""
    if prediction.debate_summary:
        debate_sect = f"## Detailed Agent Debate\n\n```\n{prediction.debate_summary.strip()}\n```\n"

    rebuttal_sect = ""
    if prediction.rebuttal_summary:
        rebuttal_sect = f"## Rebuttal Round\n\n```\n{prediction.rebuttal_summary.strip()}\n```\n"

    # Outcome Scored details (if scored)
    outcome_sect = ""
    if getattr(prediction, "actual_direction", None):
        actual_dir = prediction.actual_direction.upper()
        actual_eps = f"${prediction.actual_eps:.2f}" if prediction.actual_eps is not None else "N/A"
        actual_move = f"{prediction.actual_price_move_pct * 100:.2f}%" if prediction.actual_price_move_pct is not None else "N/A"
        brier = f"{prediction.accuracy_score:.4f}" if prediction.accuracy_score is not None else "N/A"
        scored_at_str = prediction.scored_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(prediction.scored_at, "strftime") else str(prediction.scored_at)
        
        outcome_sect = f"""
---

## Ex-Post Verification (Scored Outcome)

| Metric | Ground Truth Value |
| :--- | :--- |
| **Actual Direction** | **{actual_dir}** (VS Prediction: **{"CORRECT" if actual_dir == direction_val else "INCORRECT"}**) |
| **Actual Reported EPS** | {actual_eps} |
| **Post-Earnings Price Move** | {actual_move} |
| **Accuracy Score (Brier)** | {brier} (lower is better, 0.0 is perfect) |
| **Scored At** | {scored_at_str} |
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
| **Guidance Expectation** | {prediction.guidance_expectation or 'N/A'} |
| **Execution Duration** | {elapsed_time_str} |
| **Supabase DB Sync** | **{db_sync_status}** |
| **Run Timestamp** | {prediction_date_str} |

> [!NOTE]
> The prediction was generated using the **{model_name}** model via provider **{provider}**.
> Rebuttals were **{"enabled" if rebuttals_enabled == "Yes" else "disabled"}** during this execution.

---

{options_table}

---

{desc_sect}## Bull Case Factors

{bull_factors_str}

---

## Bear Case Factors

{bear_factors_str}

---

## Consensus Reasoning & Synthesis

{prediction.reasoning_summary}

---

{debate_sect}

{rebuttal_sect}
{outcome_sect}
"""
    return md


def generate_pdf_report(
    prediction: Any,
    output_path: Path,
    elapsed_time: Optional[float] = None,
    db_sync_status: str = "SUCCESSFUL",
    llm_info: Optional[Dict[str, Any]] = None
) -> None:
    """Generate a PDF report for an earnings prediction using fpdf2."""
    if not FPDF_AVAILABLE:
        raise RuntimeError("fpdf2 is not available. Cannot generate PDF report.")
        
    ticker = prediction.ticker
    company_name = prediction.company_name
    
    report_date_str = prediction.report_date.strftime("%Y-%m-%d") if hasattr(prediction.report_date, "strftime") else str(prediction.report_date)
    prediction_date_str = prediction.prediction_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(prediction.prediction_date, "strftime") else str(prediction.prediction_date)
    
    direction_val = prediction.direction.value.upper() if hasattr(prediction.direction, "value") else str(prediction.direction).upper()
    confidence_val = prediction.confidence
    if confidence_val <= 1.0:
        confidence_val *= 100
        
    elapsed_time_str = f"{elapsed_time:.2f}s" if elapsed_time else "N/A"
    
    pdf = PDFReport(ticker, company_name)
    pdf.add_page()
    
    # Draw header banner on first page
    pdf.set_fill_color(12, 16, 23)
    pdf.rect(0, 0, 210, 25, "F")
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.text(15, 10, "AI EARNINGS DEBATE REPORT")
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(180, 180, 180)
    pdf.text(15, 17, f"Company: {company_name} ({ticker})")
    
    pdf.set_y(32)
    
    # 1. Executive Summary Table

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(40, 50, 60)
    pdf.cell(pdf.epw, 8, "EXECUTIVE SUMMARY", new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    
    summary_data = [
        ("Ticker", ticker),
        ("Company Name", company_name),
        ("Reporting Date", report_date_str),
        ("Prediction", direction_val),
        ("Confidence Level", f"{confidence_val:.1f}%"),
        ("Expected Price Move", prediction.expected_price_move or "N/A"),
        ("Move vs Implied", prediction.move_vs_implied or "N/A"),
        ("Guidance Expectation", prediction.guidance_expectation or "N/A"),
        ("Execution Time", elapsed_time_str),
        ("Database Sync", db_sync_status),
        ("Timestamp", prediction_date_str)
    ]
    
    # Draw table
    col_width = 85
    for label, val in summary_data:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_width, 6, sanitize_for_pdf(label), border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(col_width, 6, sanitize_for_pdf(val), border=1, new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(8)
    
    # 2. Options signals
    if prediction.options_features:
        opt = prediction.options_features
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(40, 50, 60)
        pdf.cell(pdf.epw, 8, "OPTIONS MARKET SIGNALS", new_x="LMARGIN", new_y="NEXT")
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)
        
        options_data = [
            ("Implied Move", f"{opt.get('implied_move_pct', 0) * 100:.1f}%" if opt.get('implied_move_pct') else "N/A"),
            ("Put/Call Volume Ratio", f"{opt.get('put_call_volume_ratio', 0):.2f}x" if opt.get('put_call_volume_ratio') else "N/A"),
            ("ATM IV (Implied Vol)", f"{opt.get('atm_iv_call', 0) * 100:.1f}%" if opt.get('atm_iv_call') else "N/A"),
            ("IV Skew (Puts - Calls)", f"{opt.get('iv_skew', 0) * 100:.1f}%" if opt.get('iv_skew') else "N/A")
        ]
        
        for label, val in options_data:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(col_width, 6, sanitize_for_pdf(label), border=1)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(col_width, 6, sanitize_for_pdf(val), border=1, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(8)
        
    # 2.5 Company Description (if available)
    if getattr(prediction, "company_description", None):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(40, 50, 60)
        pdf.cell(pdf.epw, 8, "COMPANY DESCRIPTION", new_x="LMARGIN", new_y="NEXT")
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(pdf.epw, 5, sanitize_for_pdf(prediction.company_description))
        pdf.ln(8)

    # 3. Bull / Bear cases
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(46, 125, 50) # Green for bull case
    pdf.cell(pdf.epw, 8, "BULL FACTORS", new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    bull_list = ensure_list(prediction.bull_factors)
    if bull_list:
        for f in bull_list:
            pdf.multi_cell(pdf.epw, 5, f"- {sanitize_for_pdf(f)}")
    else:
        pdf.cell(pdf.epw, 5, "No specific bullish factors logged.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(198, 40, 40) # Red for bear case
    pdf.cell(pdf.epw, 8, "BEAR FACTORS", new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    bear_list = ensure_list(prediction.bear_factors)
    if bear_list:
        for f in bear_list:
            pdf.multi_cell(pdf.epw, 5, f"- {sanitize_for_pdf(f)}")
    else:
        pdf.cell(pdf.epw, 5, "No specific bearish factors logged.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    
    # 4. Consensus Summary
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(106, 27, 154) # Purple for consensus
    pdf.cell(pdf.epw, 8, "CONSENSUS SYNTHESIS", new_x="LMARGIN", new_y="NEXT")
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(pdf.epw, 5, sanitize_for_pdf(prediction.reasoning_summary))
    pdf.ln(8)
    
    # 5. Outcome Scored details (if scored)
    if getattr(prediction, "actual_direction", None):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(40, 50, 60)
        pdf.cell(pdf.epw, 8, "EX-POST VERIFICATION (SCORED OUTCOME)", new_x="LMARGIN", new_y="NEXT")
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)
        
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
        
        for label, val in outcome_data:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(col_width, 6, sanitize_for_pdf(label), border=1)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(col_width, 6, sanitize_for_pdf(val), border=1, new_x="LMARGIN", new_y="NEXT")
            
        pdf.ln(8)
        
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
