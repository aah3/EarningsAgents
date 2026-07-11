import unittest
from datetime import date, datetime
from pathlib import Path
import tempfile

from config.settings import EarningsPrediction, PredictionDirection
from output.report_generator import generate_markdown_report, generate_pdf_report, export_report, FPDF_AVAILABLE

class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.prediction = EarningsPrediction(
            ticker="NKE",
            company_name="NIKE, Inc.",
            report_date=date(2026, 6, 30),
            prediction_date=datetime(2026, 6, 30, 15, 56, 12),
            direction=PredictionDirection.BEAT,
            confidence=0.78,
            expected_price_move="positive",
            move_vs_implied="neutral",
            guidance_expectation="neutral",
            reasoning_summary="Nike's historical consistency favors an EPS beat.",
            bull_factors=["Low-bar beat-and-raise scenario.", "Pessimism priced in."],
            bear_factors=["Disruptive CFO transition.", "Weak consumer demand."],
            agent_votes={"bull": "beat", "bear": "miss", "quant": "beat", "consensus": "beat"},
            debate_summary="BULL: beat\nBEAR: miss\nQUANT: beat",
            rebuttal_summary="BULL REBUTTAL: beat\nBEAR REBUTTAL: miss",
            options_features={
                "implied_move_pct": 0.046,
                "put_call_volume_ratio": 1.37,
                "atm_iv_call": 0.35,
                "iv_skew": 0.05
            }
        )

    def test_generate_markdown_report(self):
        md = generate_markdown_report(
            self.prediction, 
            elapsed_time=137.32, 
            db_sync_status="SUCCESSFUL (Record Saved with ID: 14)",
            llm_info={"provider": "gemini", "model_name": "gemini-flash-latest", "enable_rebuttals": True}
        )
        self.assertIn("# AI Earnings Debate Report: NIKE, Inc. (NKE)", md)
        self.assertIn("137.32 seconds", md)
        self.assertIn("SUCCESSFUL (Record Saved with ID: 14)", md)
        self.assertIn("gemini-flash-latest", md)
        self.assertIn("Put/Call Volume Ratio", md)

    def test_generate_pdf_report(self):
        if not FPDF_AVAILABLE:
            self.skipTest("fpdf2 not installed")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "report.pdf"
            generate_pdf_report(
                self.prediction, 
                pdf_path, 
                elapsed_time=137.32, 
                db_sync_status="SUCCESSFUL",
                llm_info={"provider": "gemini", "model_name": "gemini-flash-latest"}
            )
            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 0)

    def test_export_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            saved = export_report(
                self.prediction, 
                reports_dir, 
                elapsed_time=137.32, 
                db_sync_status="SUCCESSFUL",
                llm_info={"provider": "gemini", "model_name": "gemini-flash-latest"}
            )
            self.assertIn("md", saved)
            self.assertTrue(saved["md"].exists())
            if FPDF_AVAILABLE:
                self.assertIn("pdf", saved)
                self.assertTrue(saved["pdf"].exists())
