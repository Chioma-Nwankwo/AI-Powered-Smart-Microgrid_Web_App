"""
Time Series Cross-Validation Module
Implements expanding window and rolling window CV for time series forecasting
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Generator
from sklearn.model_selection import TimeSeriesSplit


class TimeSeriesCV:
    """Time series cross-validation with expanding and rolling windows"""
    
    def __init__(self, n_splits: int = 5, test_size: int = 24):
        """
        Initialize time series cross-validator
        
        Args:
            n_splits: Number of splits for cross-validation
            test_size: Size of test set (number of time steps)
        """
        self.n_splits = n_splits
        self.test_size = test_size
        
    def expanding_window_split(self, data: pd.DataFrame) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
        """
        Expanding window split: training set grows, test set moves forward
        
        Example with 100 samples, 5 splits, test_size=20:
        Split 1: Train[0:20],   Test[20:40]
        Split 2: Train[0:40],   Test[40:60]
        Split 3: Train[0:60],   Test[60:80]
        Split 4: Train[0:80],   Test[80:100]
        
        Args:
            data: Time series dataframe
            
        Yields:
            (train_df, test_df) tuples
        """
        n_samples = len(data)
        initial_train_size = n_samples // (self.n_splits + 1)
        
        for i in range(self.n_splits):
            train_end = initial_train_size + (i * self.test_size)
            test_end = min(train_end + self.test_size, n_samples)
            
            if test_end >= n_samples:
                break
                
            train_df = data.iloc[:train_end]
            test_df = data.iloc[train_end:test_end]
            
            yield train_df, test_df
    
    def rolling_window_split(self, data: pd.DataFrame, window_size: int = 168) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
        """
        Rolling (sliding) window split: both training and test sets move forward
        Useful when only recent data is relevant (e.g., last week for hourly forecast)
        
        Args:
            data: Time series dataframe
            window_size: Size of training window (e.g., 168 hours = 1 week)
            
        Yields:
            (train_df, test_df) tuples
        """
        n_samples = len(data)
        step = self.test_size
        
        for i in range(0, n_samples - window_size - self.test_size, step):
            train_start = i
            train_end = i + window_size
            test_end = min(train_end + self.test_size, n_samples)
            
            train_df = data.iloc[train_start:train_end]
            test_df = data.iloc[train_end:test_end]
            
            yield train_df, test_df
    
    def blocked_cv_split(self, data: pd.DataFrame, gap: int = 0) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
        """
        Blocked cross-validation with optional gap between train and test
        Gap prevents data leakage when features use lagged values
        
        Args:
            data: Time series dataframe
            gap: Number of time steps to skip between train and test
            
        Yields:
            (train_df, test_df) tuples
        """
        tscv = TimeSeriesSplit(n_splits=self.n_splits, test_size=self.test_size, gap=gap)
        
        for train_idx, test_idx in tscv.split(data):
            train_df = data.iloc[train_idx]
            test_df = data.iloc[test_idx]
            yield train_df, test_df


def evaluate_cv_performance(model, cv_method, X: pd.DataFrame, y: pd.Series, 
                           metric_func) -> List[float]:
    """
    Evaluate model performance across CV splits
    
    Args:
        model: ML model with fit() and predict() methods
        cv_method: Generator yielding (train, test) splits
        X: Feature dataframe
        y: Target series
        metric_func: Function to compute error metric (e.g., MAE, RMSE)
        
    Returns:
        List of error scores for each split
    """
    scores = []
    
    for train_df, test_df in cv_method:
        # Get indices
        train_idx = train_df.index
        test_idx = test_df.index
        
        # Split X and y
        X_train, y_train = X.loc[train_idx], y.loc[train_idx]
        X_test, y_test = X.loc[test_idx], y.loc[test_idx]
        
        # Train and predict
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        # Calculate metric
        score = metric_func(y_test, y_pred)
        scores.append(score)
    
    return scores


# Example usage:
if __name__ == "__main__":
    # Create sample time series data
    dates = pd.date_range('2024-01-01', periods=1000, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'load': np.random.randn(1000).cumsum() + 100,
        'temperature': np.random.randn(1000) * 5 + 25
    })
    data.set_index('timestamp', inplace=True)
    
    # Initialize CV
    cv = TimeSeriesCV(n_splits=5, test_size=24)
    
    # Expanding window
    print("Expanding Window Splits:")
    for i, (train, test) in enumerate(cv.expanding_window_split(data), 1):
        print(f"Split {i}: Train size={len(train)}, Test size={len(test)}")
    
    # Rolling window
    print("\nRolling Window Splits:")
    for i, (train, test) in enumerate(cv.rolling_window_split(data, window_size=168), 1):
        print(f"Split {i}: Train size={len(train)}, Test size={len(test)}")
