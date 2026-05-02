"""
Data processing and feature engineering utilities
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
from config import config
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    """Handle data loading, preprocessing, and feature engineering"""
    
    def __init__(self, country: str = "nigeria"):
        """Initialize data processor for a specific country"""
        self.country = country.lower()
        self.data_path = config.DATA_DIR / f"{self.country}_processed_data.csv"
        self.data = None
        
    def load_data(self) -> pd.DataFrame:
        """Load and prepare dataset"""
        try:
            if not self.data_path.exists():
                logger.error(f"Data file not found: {self.data_path}")
                return None
            
            self.data = pd.read_csv(self.data_path)
            logger.info(f"Loaded {len(self.data)} records from {self.country} dataset")
            
            # Convert datetime column if exists
            datetime_columns = ['timestamp', 'date', 'datetime', 'time']
            for col in datetime_columns:
                if col in self.data.columns:
                    self.data[col] = pd.to_datetime(self.data[col], errors='coerce')
                    break
            
            return self.data
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return None
    
    def clean_data(self) -> pd.DataFrame:
        """Clean and preprocess data"""
        if self.data is None:
            self.load_data()
        
        if self.data is None:
            return None
        
        try:
            # Remove duplicates
            original_len = len(self.data)
            self.data = self.data.drop_duplicates()
            logger.info(f"Removed {original_len - len(self.data)} duplicate rows")
            
            # Handle missing values
            numeric_columns = self.data.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                if self.data[col].isnull().sum() > 0:
                    # Fill with median for numeric columns
                    self.data[col].fillna(self.data[col].median(), inplace=True)
            
            # Remove rows with too many missing values
            threshold = len(self.data.columns) * 0.5
            self.data = self.data.dropna(thresh=threshold)
            
            logger.info(f"Cleaned data shape: {self.data.shape}")
            return self.data
            
        except Exception as e:
            logger.error(f"Error cleaning data: {e}")
            return None
    
    def engineer_features(self) -> pd.DataFrame:
        """Create engineered features for ML models"""
        if self.data is None:
            self.clean_data()
        
        if self.data is None:
            return None
        
        try:
            # Find datetime column
            datetime_col = None
            for col in ['timestamp', 'date', 'datetime', 'time']:
                if col in self.data.columns:
                    datetime_col = col
                    break
            
            if datetime_col:
                # Time-based features
                self.data['hour'] = self.data[datetime_col].dt.hour
                self.data['day_of_week'] = self.data[datetime_col].dt.dayofweek
                self.data['day_of_month'] = self.data[datetime_col].dt.day
                self.data['month'] = self.data[datetime_col].dt.month
                self.data['quarter'] = self.data[datetime_col].dt.quarter
                self.data['is_weekend'] = self.data['day_of_week'].isin([5, 6]).astype(int)
                
                # Cyclical encoding for time features
                self.data['hour_sin'] = np.sin(2 * np.pi * self.data['hour'] / 24)
                self.data['hour_cos'] = np.cos(2 * np.pi * self.data['hour'] / 24)
                self.data['month_sin'] = np.sin(2 * np.pi * self.data['month'] / 12)
                self.data['month_cos'] = np.cos(2 * np.pi * self.data['month'] / 12)
            
            # Create lag features if enough data
            if len(self.data) > 48:
                target_columns = [col for col in self.data.columns 
                                if any(keyword in col.lower() 
                                      for keyword in ['demand', 'load', 'consumption', 'generation', 'solar'])]
                
                for col in target_columns:
                    if pd.api.types.is_numeric_dtype(self.data[col]):
                        # Lag features
                        self.data[f'{col}_lag_1'] = self.data[col].shift(1)
                        self.data[f'{col}_lag_24'] = self.data[col].shift(24)
                        
                        # Rolling statistics
                        self.data[f'{col}_rolling_mean_24'] = self.data[col].rolling(window=24, min_periods=1).mean()
                        self.data[f'{col}_rolling_std_24'] = self.data[col].rolling(window=24, min_periods=1).std()
            
            # Drop rows with NaN created by lag features
            self.data = self.data.dropna()
            
            logger.info(f"Feature engineering complete. Shape: {self.data.shape}")
            return self.data
            
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return None
    
    def prepare_ml_data(self, target_column: str, 
                       test_size: float = 0.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare data for machine learning
        Returns: X_train, X_test, y_train, y_test
        """
        if self.data is None:
            self.engineer_features()
        
        if self.data is None or target_column not in self.data.columns:
            logger.error(f"Target column {target_column} not found")
            return None, None, None, None
        
        try:
            # Separate features and target
            exclude_columns = [target_column, 'timestamp', 'date', 'datetime', 'time']
            feature_columns = [col for col in self.data.columns 
                             if col not in exclude_columns and pd.api.types.is_numeric_dtype(self.data[col])]
            
            X = self.data[feature_columns].values
            y = self.data[target_column].values
            
            # Split data (time series split)
            split_idx = int(len(X) * (1 - test_size))
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            logger.info(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")
            
            return X_train, X_test, y_train, y_test
            
        except Exception as e:
            logger.error(f"Error preparing ML data: {e}")
            return None, None, None, None
    
    def get_feature_names(self, target_column: str) -> List[str]:
        """Get list of feature names"""
        if self.data is None:
            self.engineer_features()
        
        exclude_columns = [target_column, 'timestamp', 'date', 'datetime', 'time']
        return [col for col in self.data.columns 
                if col not in exclude_columns and pd.api.types.is_numeric_dtype(self.data[col])]
    
    @staticmethod
    def normalize_data(X_train: np.ndarray, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray, object]:
        """Normalize features using StandardScaler"""
        from sklearn.preprocessing import StandardScaler
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, scaler
    
    @staticmethod
    def get_available_datasets() -> List[str]:
        """Get list of available country datasets"""
        datasets = []
        for file in config.DATA_DIR.glob("*_processed_data.csv"):
            country = file.stem.replace("_processed_data", "")
            datasets.append(country)
        return datasets
