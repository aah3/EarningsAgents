"""
SEC EDGAR Data Source for Earnings Prediction.

Provides:
- Company filings (10-K, 10-Q, 8-K)
- Earnings call transcripts (from 8-K exhibits)
- Financial data from XBRL filings
- Company facts and metadata

Requires: sec-edgar-downloader, requests
Install: pip install sec-edgar-downloader requests
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field
try:
    from .base import (
        BaseDataSource,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
    )
except (ImportError, ValueError):
    from base import (
        BaseDataSource,
        DataSourceConfig,
        RateLimiter,
        normalize_ticker,
    )


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SECFiling(BaseModel):
    """SEC filing information."""
    ticker: str
    filing_type: str  # 10-K, 10-Q, 8-K, etc.
    filing_date: date
    filing_url: str
    accession_number: str
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[str] = None
    items: List[str] = Field(default_factory=list)  # For 8-K items


class EarningsTranscript(BaseModel):
    """Earnings call transcript."""
    ticker: str
    date: date
    fiscal_year: int
    fiscal_quarter: str
    title: str
    full_text: str
    participants: List[str] = Field(default_factory=list)
    source: str = "SEC_EDGAR"
    url: Optional[str] = None


class CompanyFact(BaseModel):
    """Company fact from SEC API."""
    label: str
    value: float
    unit: str
    fiscal_year: int
    fiscal_quarter: Optional[str] = None
    filing_date: date


# ============================================================================
# SEC EDGAR DATA SOURCE
# ============================================================================

class SECEdgarDataSource(BaseDataSource):
    """
    SEC EDGAR data source.
    
    Provides access to official company filings and transcripts.
    
    Usage:
        config = DataSourceConfig(
            rate_limit_calls=10,  # SEC recommends max 10 requests/second
            rate_limit_period=1
        )
        
        sec = SECEdgarDataSource(config, user_agent="MyApp/1.0 (contact@example.com)")
        sec.connect()
        
        # Get company CIK
        cik = sec.get_cik("AAPL")
        print(f"Apple CIK: {cik}")
        
        # Get recent filings
        filings = sec.get_filings("AAPL", filing_type="8-K", limit=10)
        for f in filings:
            print(f"{f.filing_date}: {f.filing_type}")
        
        # Search for earnings transcripts
        transcripts = sec.get_earnings_transcripts("AAPL", year=2024)
        for t in transcripts:
            print(f"{t.date}: Q{t.fiscal_quarter} {t.fiscal_year}")
        
        # Get company facts (XBRL data)
        facts = sec.get_company_facts("AAPL")
        
        sec.disconnect()
    """
    
    def __init__(self, config: DataSourceConfig, user_agent: str):
        """
        Initialize SEC EDGAR data source.
        
        Args:
            config: Data source configuration
            user_agent: User agent string (required by SEC)
                       Format: "CompanyName/Version (email@example.com)"
        """
        super().__init__("SEC_EDGAR")
        self.config = config
        self.user_agent = user_agent
        self.rate_limiter = RateLimiter(
            config.rate_limit_calls,
            config.rate_limit_period
        )
        self.session = None
        self.base_url = "https://www.sec.gov"
        self.api_base = f"{self.base_url}/cgi-bin/browse-edgar"
        
        # Cache for CIK lookups
        self._cik_cache: Dict[str, str] = {}
    
    def connect(self) -> bool:
        """Connect to SEC EDGAR."""
        try:
            import requests
            
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': self.user_agent,
                'Accept-Encoding': 'gzip, deflate'
            })
            
            self._connected = True
            self.logger.info("SEC EDGAR initialized")
            return True
            
        except ImportError:
            self.logger.error(
                "requests not installed. Install with: pip install requests"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize SEC EDGAR: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from SEC EDGAR."""
        if self.session:
            self.session.close()
        self._connected = False
        self.session = None
        self.logger.info("SEC EDGAR disconnected")
    
    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CIK string (10 digits, zero-padded) or None
        """
        ticker = normalize_ticker(ticker)
        
        # Check cache
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]
        
        try:
            self._ensure_connected()
            self.rate_limiter.wait_if_needed()
            
            # Use SEC's company tickers JSON
            url = f"{self.base_url}/files/company_tickers.json"
            response = self.session.get(url, timeout=getattr(self.config, 'timeout', 30))
            response.raise_for_status()
            
            data = response.json()
            
            # Search for ticker
            for item in data.values():
                if item.get('ticker', '').upper() == ticker:
                    cik = str(item['cik_str']).zfill(10)
                    self._cik_cache[ticker] = cik
                    return cik
            
            self.logger.warning(f"CIK not found for {ticker}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get CIK for {ticker}: {e}")
            return None
    
    def get_filings(
        self,
        ticker: str,
        filing_type: str = "8-K",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[SECFiling]:
        """
        Get company filings.
        
        Args:
            ticker: Stock ticker symbol
            filing_type: Filing type (10-K, 10-Q, 8-K, etc.)
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of filings to return
            
        Returns:
            List of SECFiling
        """
        try:
            self._ensure_connected()
            
            cik = self.get_cik(ticker)
            if not cik:
                return []
            
            self.rate_limiter.wait_if_needed()
            
            # Query SEC submissions endpoint
            url = f"{self.base_url}/cgi-bin/browse-edgar"
            params = {
                'action': 'getcompany',
                'CIK': cik,
                'type': filing_type,
                'dateb': '',
                'owner': 'exclude',
                'count': limit,
                'output': 'atom'
            }
            
            response = self.session.get(url, params=params, timeout=getattr(self.config, 'timeout', 30))
            response.raise_for_status()
            
            # Parse XML/Atom feed
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # Define namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            filings = []
            
            for entry in root.findall('atom:entry', ns):
                filing_date_str = entry.find('atom:updated', ns).text
                filing_date = datetime.fromisoformat(filing_date_str.replace('Z', '+00:00')).date()
                
                # Filter by date range
                if start_date is not None and filing_date < start_date:
                    continue
                if end_date is not None and filing_date > end_date:
                    continue
                
                # Get filing URL
                link = entry.find('atom:link[@rel="alternate"]', ns)
                filing_url = link.get('href') if link is not None else ''
                
                # Extract accession number from URL
                accession_match = re.search(r'accession[nN]umber=([0-9-]+)', filing_url)
                accession_number = accession_match.group(1) if accession_match else ''
                
                # Get filing title for additional info
                title = entry.find('atom:title', ns)
                title_text = title.text if title is not None else ''
                
                # Extract fiscal info from title if available
                fiscal_year = None
                fiscal_quarter = None
                
                year_match = re.search(r'(\d{4})', title_text)
                if year_match:
                    fiscal_year = int(year_match.group(1))
                
                quarter_match = re.search(r'Q([1-4])', title_text, re.IGNORECASE)
                if quarter_match:
                    fiscal_quarter = f"Q{quarter_match.group(1)}"
                
                filings.append(SECFiling(
                    ticker=ticker,
                    filing_type=filing_type,
                    filing_date=filing_date,
                    filing_url=filing_url,
                    accession_number=accession_number,
                    fiscal_year=fiscal_year,
                    fiscal_quarter=fiscal_quarter,
                ))
            
            return filings
            
        except Exception as e:
            self.logger.error(f"Failed to get filings for {ticker}: {e}")
            return []
    
    def get_filing_text(self, filing_url: str) -> Optional[str]:
        """
        Get full text of a filing.
        
        Args:
            filing_url: URL to the filing
            
        Returns:
            Filing text or None
        """
        try:
            self._ensure_connected()
            self.rate_limiter.wait_if_needed()
            
            response = self.session.get(filing_url, timeout=getattr(self.config, 'timeout', 30))
            response.raise_for_status()
            
            # Parse HTML and extract text
            from bs4 import BeautifulSoup
            import re
            
            # Decode to string and remove common binary block patterns (PDF, GRAPHIC, etc.)
            content_str = response.content.decode('utf-8', errors='ignore')
            content_str = re.sub(r'<DOCUMENT>\s*<TYPE>(?:GRAPHIC|ZIP|EXCEL|PDF).*?</DOCUMENT>', '', content_str, flags=re.DOTALL | re.IGNORECASE)
            
            try:
                # lxml is faster and more robust with broken SEC text files
                soup = BeautifulSoup(content_str, 'lxml')
            except Exception:
                try:
                    # Fallback to html.parser
                    soup = BeautifulSoup(content_str, 'html.parser')
                except Exception as e:
                    self.logger.warning(f"Failed to parse with BeautifulSoup, using regex fallback: {e}")
                    # Ultimate fallback: strip HTML tags using regex
                    text = re.sub(r'<[^>]+>', ' ', content_str)
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    return '\n'.join(chunk for chunk in chunks if chunk)
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Failed to get filing text: {e}")
            return None
    
    def get_earnings_transcripts(
        self,
        ticker: str,
        year: Optional[int] = None,
        quarter: Optional[str] = None
    ) -> List[EarningsTranscript]:
        """
        Search for earnings call transcripts in 8-K filings.
        
        Note: Not all companies file transcripts with SEC.
        For comprehensive transcript coverage, use specialized services.
        
        Args:
            ticker: Stock ticker symbol
            year: Fiscal year to search
            quarter: Fiscal quarter (Q1, Q2, Q3, Q4)
            
        Returns:
            List of EarningsTranscript
        """
        try:
            # Get 8-K filings (earnings are typically in 8-K)
            end_date = date.today()
            start_date = date(year, 1, 1) if year else end_date - timedelta(days=365)
            
            filings = self.get_filings(
                ticker,
                filing_type="8-K",
                start_date=start_date,
                end_date=end_date,
                limit=20  # Reduced from 50 for efficiency
            )
            
            transcripts = []
            
            for filing in filings:
                # 1. Check index page for earnings indicators (fast)
                index_text = self.get_filing_text(filing.filing_url)
                if not index_text:
                    continue
                
                # Look for indicators that this 8-K contains earnings info
                # Item 2.02 = Results of Operations and Financial Condition
                index_lower = index_text.lower()
                indicators = ['2.02', 'results of operations', 'financial results', 'earnings']
                
                if not any(indicator in index_lower for indicator in indicators):
                    continue
                
                # 2. If likely an earnings release, fetch full submission to find transcript
                full_submission_url = filing.filing_url.replace('-index.htm', '.txt')
                filing_text = self.get_filing_text(full_submission_url)
                if not filing_text:
                    continue
                
                # Check if it's earnings-related (more specific keywords for full text)
                earnings_keywords = [
                    'earnings call',
                    'earnings conference',
                    'quarterly results',
                    'financial results',
                    'earnings release',
                    'transcript',
                ]
                
                text_lower = filing_text.lower()
                if not any(keyword in text_lower for keyword in earnings_keywords):
                    continue
                
                # Filter by quarter if specified
                if quarter and filing.fiscal_quarter != quarter:
                    continue
                
                transcripts.append(EarningsTranscript(
                    ticker=ticker,
                    date=filing.filing_date,
                    fiscal_year=filing.fiscal_year or filing.filing_date.year,
                    fiscal_quarter=filing.fiscal_quarter or "Q1",
                    title=f"{ticker} Earnings Call Transcript",
                    full_text=filing_text,
                    participants=[],  # Would need NLP to extract
                    source="SEC_EDGAR",
                    url=filing.filing_url,
                ))
            
            self.logger.info(f"Found {len(transcripts)} transcripts for {ticker}")
            return transcripts
            
        except Exception as e:
            self.logger.error(f"Failed to get transcripts for {ticker}: {e}")
            return []
    
    def get_company_facts(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company facts from SEC's XBRL API.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with company facts or None
        """
        try:
            self._ensure_connected()
            
            cik = self.get_cik(ticker)
            if not cik:
                return None
            
            self.rate_limiter.wait_if_needed()
            
            # Use company facts API
            # Note: SEC requires 'data.sec.gov' for this endpoint
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = self.session.get(url, timeout=getattr(self.config, 'timeout', 30))
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get company facts for {ticker}: {e}")
            return None
    
    # Implement abstract methods (limited functionality)
    
    def get_company_info(self, ticker: str):
        """Not implemented for SEC EDGAR."""
        return None
    
    def get_price_data(self, ticker: str):
        """Not implemented for SEC EDGAR."""
        return None
    
    def get_consensus_estimates(self, ticker: str):
        """Not implemented for SEC EDGAR."""
        return None
    
    def get_historical_earnings(self, ticker: str, num_quarters: int = 8):
        """Not implemented for SEC EDGAR."""
        return []
    
    def get_estimate_revisions(self, ticker: str, days_back: int = 90):
        """Not implemented for SEC EDGAR."""
        return []


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """Simple test of SEC EDGAR data source."""
    
    logging.basicConfig(level=logging.INFO)
    
    # Configure (SEC recommends max 10 requests/second)
    config = DataSourceConfig(
        rate_limit_calls=10,
        rate_limit_period=1
    )
    
    # Initialize with user agent
    sec = SECEdgarDataSource(
        config,
        user_agent="EarningsPredictor/1.0 (test@example.com)"
    )
    sec.connect()
    
    # Test ticker
    ticker = "AAPL"
    print(f"\n{'='*60}")
    print(f"Testing SEC EDGAR Data Source: {ticker}")
    print(f"{'='*60}\n")
    
    # Get CIK
    print("1. Company CIK:")
    cik = sec.get_cik(ticker)
    print(f"   {ticker} CIK: {cik}")
    
    # Get recent 10-Q filings
    print("\n2. Recent 8-K Filings:")
    filings = sec.get_filings(ticker, filing_type="10-Q", limit=5) # filing_type="8-K"
    for f in filings:
        print(f"   {f.filing_date}: {f.filing_type} - {f.accession_number}")
    
    # Search for earnings transcripts
    print("\n3. Earnings Transcripts (2025):")
    transcripts = sec.get_earnings_transcripts(ticker, year=2025)
    print(f"   Found {len(transcripts)} potential transcripts")
    for t in transcripts[:3]:
        print(f"   {t.date}: {t.fiscal_quarter} {t.fiscal_year}")
    
    # Get company facts
    print("\n4. Company Facts:")
    facts = sec.get_company_facts(ticker)
    if facts:
        print(f"   Entity: {facts.get('entityName', 'N/A')}")
        print(f"   CIK: {facts.get('cik', 'N/A')}")
        print(f"   Fiscal Year End: {facts.get('fiscalYearEnd', 'N/A')}")
    
    # Disconnect
    sec.disconnect()
    
    print(f"\n{'='*60}")
    print("Test completed successfully!")
    print(f"{'='*60}\n")
