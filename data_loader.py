"""
Data loader for real CSV files
Loads and prepares data from processed CSV files for modeling
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class RealDataLoader:
    """Load and prepare real CSV data for modeling"""
    
    # Available countries and their CSV files
    COUNTRIES = {
        'australia': 'data/processed/australia_processed_data.csv',
        'canada': 'data/processed/canada_processed_data.csv',
        'germany': 'data/processed/germany_processed_data.csv',
        'nigeria': 'data/processed/nigeria_processed_data.csv'
    }
    
    def __init__(self, data_dir: str = "."):
        """Initialize data loader
        
        Args:
            data_dir: Directory containing CSV files (root project directory)
        """
        self.data_dir = Path(data_dir)
        self.data_cache = {}
    
    def load_country_data(self, country: str) -> Optional[pd.DataFrame]:
        """Load data for a specific country
        
        Args:
            country: Country name (australia, canada, germany, nigeria)
            
        Returns:
            DataFrame with country data or None if not found
        """
        country = country.lower()
        
        # Return from cache if already loaded
        if country in self.data_cache:
            logger.info(f"Returning cached data for {country}")
            return self.data_cache[country].copy()
        
        # Check if country exists
        if country not in self.COUNTRIES:
            logger.error(f"Unknown country: {country}. Available: {list(self.COUNTRIES.keys())}")
            return None
        
        # Load CSV file
        file_path = self.data_dir / self.COUNTRIES[country]
        if not file_path.exists():
            logger.error(f"Data file not found: {file_path}")
            return None
        
        try:
            logger.info(f"Loading data from {file_path}")
            df = pd.read_csv(file_path, low_memory=False)

            # Parse time column
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time').reset_index(drop=True)
            
            # Cache the data
            self.data_cache[country] = df.copy()
            
            logger.info(f"Loaded {len(df)} records for {country} ({df['time'].min()} to {df['time'].max()})")
            return df.copy()
            
        except Exception as e:
            logger.error(f"Error loading data for {country}: {e}")
            return None
    
    def get_feature_columns(self, df: pd.DataFrame) -> list:
        """Get list of feature columns for modeling
        
        Args:
            df: DataFrame with data
            
        Returns:
            List of feature column names (excluding categorical columns)
        """
        # Exclude target, time, and categorical columns
        exclude = ['time', 'solar_radiation', 'solar_radiation_wm2']
        
        # Get numeric columns only
        feature_cols = []
        for col in df.columns:
            if col not in exclude:
                # Only include numeric columns
                if pd.api.types.is_numeric_dtype(df[col]):
                    feature_cols.append(col)
                else:
                    logger.warning(f"Skipping non-numeric column: {col}")
        
        return feature_cols
    
    def prepare_forecasting_data(
        self, 
        country: str,
        target: str = 'solar_radiation_wm2',
        test_size: float = 0.2,
        time_steps: int = 24
    ) -> Optional[Dict]:
        """Prepare data for forecasting models
        
        Args:
            country: Country name
            target: Target variable to forecast
            test_size: Proportion of data for testing
            time_steps: Number of time steps for LSTM
            
        Returns:
            Dictionary with train/test splits and metadata
        """
        df = self.load_country_data(country)
        if df is None:
            return None
        
        # Get features
        feature_cols = self.get_feature_columns(df)
        
        # Remove target from features if present
        if target in feature_cols:
            feature_cols.remove(target)
        
        # Check if target exists
        if target not in df.columns:
            logger.error(f"Target column '{target}' not found in data")
            return None
        
        # Split into train/test
        split_idx = int(len(df) * (1 - test_size))
        
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        
        # Prepare features and target
        X_train = train_df[feature_cols].values
        y_train = train_df[target].values
        X_test = test_df[feature_cols].values
        y_test = test_df[target].values
        
        # Get time indices
        train_times = train_df['time'].values if 'time' in train_df.columns else None
        test_times = test_df['time'].values if 'time' in test_df.columns else None
        
        return {
            'X_train': X_train,
            'y_train': y_train,
            'X_test': X_test,
            'y_test': y_test,
            'train_times': train_times,
            'test_times': test_times,
            'feature_names': feature_cols,
            'target_name': target,
            'country': country,
            'train_size': len(train_df),
            'test_size': len(test_df)
        }
    
    def get_latest_data(self, country: str, hours: int = 168) -> Optional[pd.DataFrame]:
        """Get most recent data for real-time predictions
        
        Args:
            country: Country name
            hours: Number of hours of recent data to return
            
        Returns:
            DataFrame with recent data
        """
        df = self.load_country_data(country)
        if df is None:
            return None
        
        return df.tail(hours).copy()
    
    def get_data_summary(self, country: str) -> Optional[Dict]:
        """Get summary statistics for country data
        
        Args:
            country: Country name
            
        Returns:
            Dictionary with summary statistics
        """
        df = self.load_country_data(country)
        if df is None:
            return None
        
        summary = {
            'country': country,
            'total_records': len(df),
            'start_date': str(df['time'].min()) if 'time' in df.columns else None,
            'end_date': str(df['time'].max()) if 'time' in df.columns else None,
            'columns': list(df.columns),
            'missing_values': df.isnull().sum().to_dict()
        }
        
        # Add statistics for key columns
        key_cols = ['solar_radiation_wm2', 'wind_speed', 'temperature_celsius']
        for col in key_cols:
            if col in df.columns:
                summary[f'{col}_stats'] = {
                    'mean': float(df[col].mean()),
                    'std': float(df[col].std()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max())
                }
        
        return summary


# Global data loader instance
data_loader = RealDataLoader()


def get_user_country_data(country: str) -> Optional[pd.DataFrame]:
    """Convenience function to load user's country data
    
    Args:
        country: Country name
        
    Returns:
        DataFrame with country data
    """
    return data_loader.load_country_data(country)
