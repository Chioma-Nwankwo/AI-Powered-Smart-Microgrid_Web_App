"""
Models package initialization
"""
try:
    from models.forecasting import (
        RandomForestModel,
        XGBoostModel,
        LSTMModel,
        EnsembleForecaster,
    )
    _HAS_FORECASTING = True
except Exception:
    _HAS_FORECASTING = False
    RandomForestModel = XGBoostModel = LSTMModel = EnsembleForecaster = None

from models.optimization import EnergyOptimizer, RealTimeOptimizer

__all__ = [
    'RandomForestModel', 'XGBoostModel', 'LSTMModel', 'EnsembleForecaster',
    'EnergyOptimizer', 'RealTimeOptimizer',
]
