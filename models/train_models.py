"""
Model training script
Run this to train ML models on available datasets
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_processor import DataProcessor
from models.forecasting import RandomForestModel, XGBoostModel, LSTMModel
from config import config
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_models_for_country(country: str, target_column: str = None):
    """Train all models for a specific country dataset"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Training models for {country.upper()}")
    logger.info(f"{'='*60}\n")
    
    # Load and process data
    processor = DataProcessor(country)
    data = processor.engineer_features()
    
    if data is None:
        logger.error(f"Failed to load data for {country}")
        return
    
    # Auto-detect target column if not specified
    if target_column is None:
        possible_targets = [col for col in data.columns 
                          if any(keyword in col.lower() 
                                for keyword in ['demand', 'load', 'consumption'])]
        if possible_targets:
            target_column = possible_targets[0]
            logger.info(f"Auto-detected target column: {target_column}")
        else:
            logger.error("Could not auto-detect target column")
            return
    
    # Prepare ML data
    X_train, X_test, y_train, y_test = processor.prepare_ml_data(target_column)
    
    if X_train is None:
        logger.error("Failed to prepare ML data")
        return
    
    # Normalize data
    X_train_scaled, X_test_scaled, scaler = DataProcessor.normalize_data(X_train, X_test)
    
    # Get feature names
    feature_names = processor.get_feature_names(target_column)
    
    # Train Random Forest
    logger.info("\n" + "-"*60)
    rf_model = RandomForestModel()
    rf_model.train(X_train_scaled, y_train, feature_names)
    rf_metrics = rf_model.evaluate(X_test_scaled, y_test)
    logger.info(f"Random Forest - MAE: {rf_metrics['mae']:.2f}, R²: {rf_metrics['r2']:.4f}")
    
    # Save Random Forest model
    rf_path = config.MODELS_DIR / f"{country}_random_forest.pkl"
    rf_model.save(rf_path)
    
    # Train XGBoost
    logger.info("\n" + "-"*60)
    xgb_model = XGBoostModel()
    xgb_model.train(X_train_scaled, y_train, feature_names)
    xgb_metrics = xgb_model.evaluate(X_test_scaled, y_test)
    logger.info(f"XGBoost - MAE: {xgb_metrics['mae']:.2f}, R²: {xgb_metrics['r2']:.4f}")
    
    # Save XGBoost model
    xgb_path = config.MODELS_DIR / f"{country}_xgboost.pkl"
    xgb_model.save(xgb_path)
    
    # Train LSTM
    logger.info("\n" + "-"*60)
    lstm_model = LSTMModel(sequence_length=24)
    lstm_model.train(X_train_scaled, y_train, feature_names)
    lstm_metrics = lstm_model.evaluate(X_test_scaled, y_test)
    logger.info(f"LSTM - MAE: {lstm_metrics['mae']:.2f}, R²: {lstm_metrics['r2']:.4f}")
    
    # Save LSTM model
    lstm_path = config.MODELS_DIR / f"{country}_lstm.h5"
    lstm_model.save(lstm_path)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Training complete for {country.upper()}")
    logger.info(f"{'='*60}")
    logger.info(f"Random Forest - MAE: {rf_metrics['mae']:.2f}, RMSE: {rf_metrics['rmse']:.2f}, R²: {rf_metrics['r2']:.4f}")
    logger.info(f"XGBoost      - MAE: {xgb_metrics['mae']:.2f}, RMSE: {xgb_metrics['rmse']:.2f}, R²: {xgb_metrics['r2']:.4f}")
    logger.info(f"LSTM         - MAE: {lstm_metrics['mae']:.2f}, RMSE: {lstm_metrics['rmse']:.2f}, R²: {lstm_metrics['r2']:.4f}")
    logger.info(f"{'='*60}\n")
    
    return {
        'random_forest': rf_metrics,
        'xgboost': xgb_metrics,
        'lstm': lstm_metrics
    }


def main():
    """Train models for all available countries"""
    logger.info("\n" + "="*60)
    logger.info("SMART MICROGRID ML MODEL TRAINING")
    logger.info("="*60 + "\n")
    
    # Get available datasets
    datasets = DataProcessor.get_available_datasets()
    logger.info(f"Found datasets for: {', '.join(datasets)}\n")
    
    if not datasets:
        logger.error("No datasets found!")
        return
    
    # Create models directory
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Train for each country
    all_results = {}
    for country in datasets:
        try:
            results = train_models_for_country(country)
            if results:
                all_results[country] = results
        except Exception as e:
            logger.error(f"Error training models for {country}: {e}")
            continue
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("ALL MODELS TRAINED SUCCESSFULLY")
    logger.info("="*60)
    logger.info(f"\nTrained models for {len(all_results)} countries")
    logger.info(f"Models saved to: {config.MODELS_DIR}")
    logger.info("\nNext steps:")
    logger.info("1. Configure your .env file")
    logger.info("2. Initialize databases: python database/init_db.py")
    logger.info("3. Start backend: cd backend && python app.py")
    logger.info("4. Start frontend: cd microgrid-ui && npm run dev")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    main()
