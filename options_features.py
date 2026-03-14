import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class OptionFeaturesExtractor:
    """
    Extracts quantitative features from an options chain DataFrame.
    Designed for use in ML pipelines and Quant Trading strategies.
    
    Generates features such as:
    - Put-Call Ratios (Volume and Open Interest)
    - OTM Option Ratios
    - IV Skewness (OTM Put IV vs OTM Call IV)
    - Volume-weighted and OI-weighted strikes relative to spot
    - Net Gamma Exposure
    - Max Pain Strike
    """

    def __init__(
        self,
        ticker_col: str = 'ticker',
        date_col: str = 'date',
        right_col: str = 'right',
        strike_col: str = 'strike',
        spot_col: str = 'stock_price',
        volume_col: str = 'volume',
        oi_col: str = 'open_interest',
        iv_col: str = 'implied_volatility',
        gamma_col: str = 'gamma',
        exp_col: str = 'exp',
        sid_col: Optional[str] = None
    ):
        """
        Initialize the extractor with the expected column names in the options DataFrame.
        Provides generic mapping to use with different data providers.
        """
        self.cols = {
            'ticker': ticker_col,
            'date': date_col,
            'right': right_col,
            'strike': strike_col,
            'spot': spot_col,
            'volume': volume_col,
            'oi': oi_col,
            'iv': iv_col,
            'gamma': gamma_col,
            'exp': exp_col,
            'sid': sid_col
        }

    def _extract_for_group(
        self, 
        group: pd.DataFrame, 
        date_val: str, 
        ticker_val: str, 
        sid_val: Optional[str] = None, 
        exp_val: Optional[str] = None
    ) -> dict:
        """
        Extract features for a specific grouping of the options dataframe.
        """
        spot = group[self.cols['spot']].iloc[0] if len(group) > 0 else 0.0
        
        # Determine Call vs Put
        calls = group[group[self.cols['right']].astype(str).str.lower().isin(['c', 'call'])]
        puts = group[group[self.cols['right']].astype(str).str.lower().isin(['p', 'put'])]
        
        # OTM definitions (Calls: Strike > Spot, Puts: Strike < Spot)
        otm_calls = calls[calls[self.cols['strike']] > spot]
        otm_puts = puts[puts[self.cols['strike']] < spot]
        
        # 1. Volume Ratios
        total_call_vol = calls[self.cols['volume']].sum()
        total_put_vol = puts[self.cols['volume']].sum()
        total_vol = total_call_vol + total_put_vol
        put_call_volume_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else np.nan
        
        otm_call_vol = otm_calls[self.cols['volume']].sum()
        otm_put_vol = otm_puts[self.cols['volume']].sum()
        otm_call_put_vol_ratio = otm_call_vol / otm_put_vol if otm_put_vol > 0 else np.nan
        
        # 2. Open Interest Ratios
        total_call_oi = calls[self.cols['oi']].sum()
        total_put_oi = puts[self.cols['oi']].sum()
        total_oi = total_call_oi + total_put_oi
        put_call_oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else np.nan
        
        otm_call_oi = otm_calls[self.cols['oi']].sum()
        otm_put_oi = otm_puts[self.cols['oi']].sum()
        otm_call_put_oi_ratio = otm_call_oi / otm_put_oi if otm_put_oi > 0 else np.nan
        
        # 3. IV Skewness (OTM puts IV vs OTM calls IV)
        def vw_iv(df_sub):
            v_sum = df_sub[self.cols['volume']].sum()
            # If no volume, fallback to OI weighted
            if v_sum == 0:
                oi_sum = df_sub[self.cols['oi']].sum()
                if oi_sum == 0:
                    return df_sub[self.cols['iv']].mean()
                return (df_sub[self.cols['iv']] * df_sub[self.cols['oi']]).sum() / oi_sum
            return (df_sub[self.cols['iv']] * df_sub[self.cols['volume']]).sum() / v_sum
            
        otm_put_iv = vw_iv(otm_puts)
        otm_call_iv = vw_iv(otm_calls)
        otm_put_call_iv_ratio = otm_put_iv / otm_call_iv if (otm_call_iv and otm_call_iv > 0) else np.nan
        iv_skew = otm_put_iv - otm_call_iv if (pd.notnull(otm_put_iv) and pd.notnull(otm_call_iv)) else np.nan
        
        # 4. Volume & OI weighted strikes
        vw_strike_to_spot = np.nan
        if total_vol > 0:
            vw_strike = (group[self.cols['strike']] * group[self.cols['volume']]).sum() / total_vol
            vw_strike_to_spot = vw_strike / spot if spot > 0 else np.nan
            
        oi_w_strike_to_spot = np.nan
        if total_oi > 0:
            oi_w_strike = (group[self.cols['strike']] * group[self.cols['oi']]).sum() / total_oi
            oi_w_strike_to_spot = oi_w_strike / spot if spot > 0 else np.nan
            
        # 5. Gamma Exposure / Pain
        net_gamma_exposure = np.nan
        if self.cols['gamma'] in group.columns and pd.notnull(group[self.cols['gamma']]).any():
            call_gamma = (calls[self.cols['gamma']] * calls[self.cols['oi']]).sum()
            put_gamma = (puts[self.cols['gamma']] * puts[self.cols['oi']]).sum()
            net_gamma_exposure = call_gamma - put_gamma

        # 6. Max Pain
        unique_strikes = group[self.cols['strike']].unique()
        max_pain_strike = np.nan
        
        if len(unique_strikes) > 0 and len(group) > 0:
            call_strikes = calls[self.cols['strike']].values
            call_ois = calls[self.cols['oi']].values
            put_strikes = puts[self.cols['strike']].values
            put_ois = puts[self.cols['oi']].values
            
            # Vectorized Max Pain calculation
            # Pain(k) = sum(max(0, k - call_strike) * call_oi) + sum(max(0, put_strike - k) * put_oi)
            strikes_grid = unique_strikes[:, np.newaxis]
            
            call_pain_matrix = np.maximum(0, strikes_grid - call_strikes) * call_ois
            put_pain_matrix = np.maximum(0, put_strikes - strikes_grid) * put_ois
            
            total_pain = call_pain_matrix.sum(axis=1) + put_pain_matrix.sum(axis=1)
            min_pain_idx = np.argmin(total_pain)
            max_pain_strike = unique_strikes[min_pain_idx]
            
        max_pain_to_spot = max_pain_strike / spot if (spot > 0 and pd.notnull(max_pain_strike)) else np.nan

        features = {
            'date': date_val,
            'ticker': ticker_val,
        }
        
        if self.cols['sid'] and sid_val:
            features['sid'] = sid_val
            
        if exp_val is not None:
            features['exp'] = exp_val
            
        features.update({
            'spot_price': spot,
            'total_volume': total_vol,
            'total_oi': total_oi,
            'put_call_volume_ratio': put_call_volume_ratio,
            'put_call_oi_ratio': put_call_oi_ratio,
            'otm_call_put_vol_ratio': otm_call_put_vol_ratio,
            'otm_call_put_oi_ratio': otm_call_put_oi_ratio,
            'otm_put_call_iv_ratio': otm_put_call_iv_ratio,
            'iv_skew': iv_skew,
            'vw_strike_to_spot': vw_strike_to_spot,
            'oi_w_strike_to_spot': oi_w_strike_to_spot,
            'net_gamma_exposure': net_gamma_exposure,
            'max_pain_strike': max_pain_strike,
            'max_pain_to_spot': max_pain_to_spot,
        })
        
        return features

    def extract_features(self, df: pd.DataFrame, group_by_expiry: bool = False) -> pd.DataFrame:
        """
        Calculates features from option chain dataframe.
        
        Args:
            df: Input dataframe with option chain metadata.
            group_by_expiry: If True, calculates features per expiration date.
                             If False, aggregates across the entire option chain.
        Returns:
            DataFrame with estimated features.
        """
        if df.empty:
            return pd.DataFrame()
            
        # Core columns validation
        core_cols = [self.cols['date'], self.cols['ticker'], self.cols['right'], 
                     self.cols['strike'], self.cols['spot'], self.cols['volume'], 
                     self.cols['oi'], self.cols['iv']]
        missing_cols = [c for c in core_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in DataFrame: {missing_cols}")

        results = []
        
        groupby_cols = [self.cols['date'], self.cols['ticker']]
        
        if self.cols['sid'] and self.cols['sid'] in df.columns:
            groupby_cols.append(self.cols['sid'])
            
        if group_by_expiry:
            if self.cols['exp'] not in df.columns:
                raise ValueError(f"Missing expiration column '{self.cols['exp']}' required for grouping by expiry.")
            groupby_cols.append(self.cols['exp'])
            
        for name, group in df.groupby(groupby_cols):
            # Parse grouping keys
            sid_val = None
            exp_val = None
            
            if isinstance(name, tuple):
                date_val = name[0]
                ticker_val = name[1]
                idx = 2
                if self.cols['sid'] and self.cols['sid'] in df.columns:
                    sid_val = name[idx]
                    idx += 1
                if group_by_expiry:
                    exp_val = name[idx]
            else:
                date_val = name
                ticker_val = group[self.cols['ticker']].iloc[0] # Fallback
                
            features = self._extract_for_group(group, date_val, ticker_val, sid_val, exp_val)
            results.append(features)
            
        return pd.DataFrame(results)

if __name__ == "__main__":
    # Example Usage
    from data.yahoo_finance import YahooFinanceDataSource, DataSourceConfig
    
    config = DataSourceConfig()
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    
    # We load option chains with a reasonable expiration limit for testing
    df = yahoo.get_option_chain_dataframe("AAPL", num_expirations=3)
    
    if not df.empty:
        # 1. Instantiate the extractor
        extractor = OptionFeaturesExtractor(date_col='date')
        
        # 2. Extract aggregated features for the entire chain
        features_df = extractor.extract_features(df, group_by_expiry=False)
        print("--- Aggregated Global Features ---")
        print(features_df.head().T)
        
        # 3. Extract features segmented by expiration
        features_exp_df = extractor.extract_features(df, group_by_expiry=True)
        print("\\n--- Features Grouped by Expiration ---")
        print(features_exp_df[['exp', 'put_call_volume_ratio', 'iv_skew', 'max_pain_strike']].head())
