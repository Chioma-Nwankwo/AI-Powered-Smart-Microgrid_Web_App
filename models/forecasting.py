"""
Machine Learning models for demand and generation forecasting
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
try:
    from tensorflow import keras
    from tensorflow.keras import layers
    _HAS_TENSORFLOW = True
except ImportError:
    keras = None
    layers = None
    _HAS_TENSORFLOW = False
import joblib
from pathlib import Path
from typing import Dict, Tuple, Optional
from config import config
import logging

logger = logging.getLogger(__name__)


class ForecastModel:
    """Base class for forecasting models"""
    
    def __init__(self, model_type: str = "random_forest"):
        """Initialize forecasting model"""
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = None
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
             feature_names: list = None) -> Dict:
        """Train the model"""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        if self.model is None:
            raise ValueError("Model not trained")
        return self.model.predict(X)
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate model performance"""
        predictions = self.predict(X_test)
        
        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        r2 = r2_score(y_test, predictions)
        mape = np.mean(np.abs((y_test - predictions) / (y_test + 1e-10))) * 100
        
        metrics = {
            'mae': float(mae),
            'rmse': float(rmse),
            'r2': float(r2),
            'mape': float(mape)
        }
        
        logger.info(f"Model evaluation - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R²: {r2:.4f}")
        return metrics
    
    def save(self, filepath: Path):
        """Save model to disk"""
        raise NotImplementedError
    
    def load(self, filepath: Path):
        """Load model from disk"""
        raise NotImplementedError


class RandomForestModel(ForecastModel):
    """Random Forest forecasting model"""
    
    def __init__(self):
        super().__init__("random_forest")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
             feature_names: list = None) -> Dict:
        """Train Random Forest model"""
        try:
            self.feature_names = feature_names
            
            self.model = RandomForestRegressor(
                n_estimators=200,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=config.RANDOM_STATE,
                n_jobs=-1
            )
            
            logger.info("Training Random Forest model...")
            self.model.fit(X_train, y_train)
            
            logger.info("Random Forest training complete")
            return {"status": "success", "model_type": "random_forest"}
            
        except Exception as e:
            logger.error(f"Error training Random Forest: {e}")
            return {"status": "error", "message": str(e)}
    
    def save(self, filepath: Path):
        """Save Random Forest model"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names
        }, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load Random Forest model"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.feature_names = data.get('feature_names')
        logger.info(f"Model loaded from {filepath}")


class XGBoostModel(ForecastModel):
    """XGBoost forecasting model"""
    
    def __init__(self):
        super().__init__("xgboost")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
             feature_names: list = None) -> Dict:
        """Train XGBoost model"""
        try:
            self.feature_names = feature_names
            
            self.model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=config.RANDOM_STATE,
                n_jobs=-1
            )
            
            logger.info("Training XGBoost model...")
            self.model.fit(X_train, y_train, verbose=False)
            
            logger.info("XGBoost training complete")
            return {"status": "success", "model_type": "xgboost"}
            
        except Exception as e:
            logger.error(f"Error training XGBoost: {e}")
            return {"status": "error", "message": str(e)}
    
    def save(self, filepath: Path):
        """Save XGBoost model"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names
        }, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load XGBoost model"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.feature_names = data.get('feature_names')
        logger.info(f"Model loaded from {filepath}")


class LSTMModel(ForecastModel):
    """LSTM neural network forecasting model"""
    
    def __init__(self, sequence_length: int = 24):
        super().__init__("lstm")
        self.sequence_length = sequence_length
    
    def prepare_sequences(self, X: np.ndarray, y: np.ndarray = None) -> Tuple:
        """Prepare sequences for LSTM"""
        X_seq, y_seq = [], []
        
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])
            if y is not None:
                y_seq.append(y[i + self.sequence_length])
        
        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq) if y is not None else None
        
        return X_seq, y_seq
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
             feature_names: list = None) -> Dict:
        """Train LSTM model"""
        try:
            self.feature_names = feature_names
            
            # Prepare sequences
            X_seq, y_seq = self.prepare_sequences(X_train, y_train)
            
            logger.info(f"Training LSTM with sequence shape: {X_seq.shape}")
            
            # Build model
            self.model = keras.Sequential([
                layers.LSTM(128, activation='relu', return_sequences=True, 
                          input_shape=(X_seq.shape[1], X_seq.shape[2])),
                layers.Dropout(0.2),
                layers.LSTM(64, activation='relu'),
                layers.Dropout(0.2),
                layers.Dense(32, activation='relu'),
                layers.Dense(1)
            ])
            
            self.model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='mse',
                metrics=['mae']
            )
            
            # Train model
            history = self.model.fit(
                X_seq, y_seq,
                epochs=50,
                batch_size=32,
                validation_split=0.2,
                verbose=0,
                callbacks=[
                    keras.callbacks.EarlyStopping(
                        monitor='val_loss',
                        patience=10,
                        restore_best_weights=True
                    )
                ]
            )
            
            logger.info("LSTM training complete")
            return {
                "status": "success", 
                "model_type": "lstm",
                "final_loss": float(history.history['loss'][-1])
            }
            
        except Exception as e:
            logger.error(f"Error training LSTM: {e}")
            return {"status": "error", "message": str(e)}
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with LSTM"""
        if self.model is None:
            raise ValueError("Model not trained")
        
        X_seq, _ = self.prepare_sequences(X)
        predictions = self.model.predict(X_seq, verbose=0)
        return predictions.flatten()
    
    def save(self, filepath: Path):
        """Save LSTM model"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(filepath)
        
        # Save metadata
        metadata_path = filepath.parent / f"{filepath.stem}_metadata.pkl"
        joblib.dump({
            'sequence_length': self.sequence_length,
            'feature_names': self.feature_names
        }, metadata_path)
        
        logger.info(f"Model saved to {filepath}")
    
    def load(self, filepath: Path):
        """Load LSTM model"""
        self.model = keras.models.load_model(filepath)
        
        # Load metadata
        metadata_path = filepath.parent / f"{filepath.stem}_metadata.pkl"
        if metadata_path.exists():
            metadata = joblib.load(metadata_path)
            self.sequence_length = metadata['sequence_length']
            self.feature_names = metadata.get('feature_names')
        
        logger.info(f"Model loaded from {filepath}")


class EnsembleForecaster:
    """Ensemble of multiple forecasting models"""
    
    def __init__(self):
        self.models = {
            'random_forest': RandomForestModel(),
            'xgboost': XGBoostModel(),
            'lstm': LSTMModel()
        }
        self.weights = {'random_forest': 0.3, 'xgboost': 0.4, 'lstm': 0.3}
    
    def train_all(self, X_train: np.ndarray, y_train: np.ndarray, 
                 feature_names: list = None) -> Dict:
        """Train all models in ensemble"""
        results = {}
        
        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            result = model.train(X_train, y_train, feature_names)
            results[name] = result
        
        return results
    
    def predict(self, X: np.ndarray, method: str = "weighted") -> np.ndarray:
        """Make ensemble predictions"""
        predictions = {}
        
        for name, model in self.models.items():
            try:
                predictions[name] = model.predict(X)
            except Exception as e:
                logger.warning(f"Prediction failed for {name}: {e}")
        
        if not predictions:
            raise ValueError("No models available for prediction")
        
        if method == "weighted":
            # Weighted average
            ensemble_pred = np.zeros_like(list(predictions.values())[0])
            total_weight = 0
            
            for name, pred in predictions.items():
                weight = self.weights.get(name, 1.0)
                ensemble_pred += weight * pred
                total_weight += weight
            
            ensemble_pred /= total_weight
            return ensemble_pred
        
        elif method == "average":
            # Simple average
            return np.mean(list(predictions.values()), axis=0)
        
        else:
            raise ValueError(f"Unknown ensemble method: {method}")
