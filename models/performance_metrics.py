"""
Performance Metrics Module
Comprehensive metrics for forecasting, optimization, and anomaly detection
"""
import numpy as np
from typing import Dict, Tuple
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix
)


class ForecastingMetrics:
    """Metrics for evaluating time series forecasts"""
    
    @staticmethod
    def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Mean Absolute Error"""
        return mean_absolute_error(y_true, y_pred)
    
    @staticmethod
    def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Root Mean Squared Error"""
        return np.sqrt(mean_squared_error(y_true, y_pred))
    
    @staticmethod
    def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Mean Absolute Percentage Error"""
        return np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    
    @staticmethod
    def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Symmetric Mean Absolute Percentage Error"""
        return 100 * np.mean(2 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred)))
    
    @staticmethod
    def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """R-squared (coefficient of determination)"""
        return r2_score(y_true, y_pred)
    
    @staticmethod
    def mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray) -> float:
        """
        Mean Absolute Scaled Error
        Compares forecast error to naive forecast (seasonal or simple)
        """
        # Naive forecast: use previous value
        naive_error = np.mean(np.abs(np.diff(y_train)))
        return np.mean(np.abs(y_true - y_pred)) / naive_error
    
    @classmethod
    def compute_all(cls, y_true: np.ndarray, y_pred: np.ndarray, 
                   y_train: np.ndarray = None) -> Dict[str, float]:
        """Compute all forecasting metrics"""
        metrics = {
            'MAE': cls.mae(y_true, y_pred),
            'RMSE': cls.rmse(y_true, y_pred),
            'MAPE': cls.mape(y_true, y_pred),
            'SMAPE': cls.smape(y_true, y_pred),
            'R2': cls.r2(y_true, y_pred)
        }
        
        if y_train is not None:
            metrics['MASE'] = cls.mase(y_true, y_pred, y_train)
        
        return metrics


class OptimizationMetrics:
    """Metrics for evaluating microgrid optimization performance"""
    
    @staticmethod
    def energy_wasted(solar_generated: np.ndarray, load_demand: np.ndarray, 
                     battery_charged: np.ndarray) -> float:
        """
        Calculate energy wasted (kWh)
        Energy that could not be stored or used
        """
        excess = np.maximum(0, solar_generated - load_demand - battery_charged)
        return np.sum(excess)
    
    @staticmethod
    def cost_savings(optimized_cost: float, baseline_cost: float) -> Tuple[float, float]:
        """
        Calculate cost savings
        Returns: (absolute savings, percentage savings)
        """
        absolute_savings = baseline_cost - optimized_cost
        percentage_savings = (absolute_savings / baseline_cost) * 100
        return absolute_savings, percentage_savings
    
    @staticmethod
    def battery_health(charge_cycles: np.ndarray, depth_of_discharge: np.ndarray, 
                      rated_cycles: int = 5000) -> Dict[str, float]:
        """
        Estimate battery health metrics
        
        Args:
            charge_cycles: Array of charge cycle counts
            depth_of_discharge: Array of DoD values (0-1)
            rated_cycles: Rated cycle life at 80% DoD
            
        Returns:
            Dictionary with health metrics
        """
        total_cycles = len(charge_cycles)
        avg_dod = np.mean(depth_of_discharge)
        
        # Cycle life degrades faster with deeper discharge
        # Simplified model: cycle life inversely proportional to DoD
        adjusted_cycles = total_cycles * (avg_dod / 0.8)
        remaining_life = max(0, (rated_cycles - adjusted_cycles) / rated_cycles * 100)
        
        return {
            'total_cycles': total_cycles,
            'average_dod': avg_dod,
            'adjusted_cycle_count': adjusted_cycles,
            'remaining_life_percent': remaining_life
        }
    
    @staticmethod
    def loss_of_load_probability(unmet_demand: np.ndarray, 
                                 total_demand: np.ndarray) -> float:
        """
        Calculate Loss of Load Probability (LOLP)
        Percentage of time when demand cannot be met
        """
        time_steps_failed = np.sum(unmet_demand > 0)
        total_time_steps = len(unmet_demand)
        return (time_steps_failed / total_time_steps) * 100
    
    @staticmethod
    def renewable_penetration(solar_used: np.ndarray, total_energy: np.ndarray) -> float:
        """
        Calculate renewable energy penetration rate
        Percentage of total energy from solar
        """
        return (np.sum(solar_used) / np.sum(total_energy)) * 100
    
    @classmethod
    def compute_all(cls, solar_generated: np.ndarray, load_demand: np.ndarray,
                   battery_charged: np.ndarray, battery_discharged: np.ndarray,
                   grid_import: np.ndarray, optimized_cost: float,
                   baseline_cost: float, depth_of_discharge: np.ndarray) -> Dict:
        """Compute all optimization metrics"""
        unmet_demand = np.maximum(0, load_demand - solar_generated - battery_discharged - grid_import)
        
        return {
            'energy_wasted_kwh': cls.energy_wasted(solar_generated, load_demand, battery_charged),
            'cost_savings': cls.cost_savings(optimized_cost, baseline_cost),
            'battery_health': cls.battery_health(battery_charged, depth_of_discharge),
            'lolp_percent': cls.loss_of_load_probability(unmet_demand, load_demand),
            'renewable_penetration_percent': cls.renewable_penetration(
                solar_generated - np.maximum(0, solar_generated - load_demand),
                load_demand
            )
        }


class AnomalyDetectionMetrics:
    """Metrics for evaluating anomaly detection performance"""
    
    @staticmethod
    def precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate precision, recall, and F1-score"""
        return {
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1_score': f1_score(y_true, y_pred, zero_division=0)
        }
    
    @staticmethod
    def roc_auc(y_true: np.ndarray, y_scores: np.ndarray) -> float:
        """Calculate ROC AUC score"""
        return roc_auc_score(y_true, y_scores)
    
    @staticmethod
    def confusion_matrix_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Calculate confusion matrix and derived metrics"""
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        return {
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_positives': int(tp),
            'specificity': tn / (tn + fp) if (tn + fp) > 0 else 0,
            'false_positive_rate': fp / (fp + tn) if (fp + tn) > 0 else 0,
            'false_negative_rate': fn / (fn + tp) if (fn + tp) > 0 else 0
        }
    
    @classmethod
    def compute_all(cls, y_true: np.ndarray, y_pred: np.ndarray, 
                   y_scores: np.ndarray = None) -> Dict:
        """Compute all anomaly detection metrics"""
        metrics = {
            **cls.precision_recall_f1(y_true, y_pred),
            **cls.confusion_matrix_metrics(y_true, y_pred)
        }
        
        if y_scores is not None:
            metrics['roc_auc'] = cls.roc_auc(y_true, y_scores)
        
        return metrics


# Example usage
if __name__ == "__main__":
    # Forecasting example
    y_true = np.array([100, 105, 110, 108, 112])
    y_pred = np.array([98, 107, 109, 110, 111])
    y_train = np.array([95, 98, 100, 102, 103])
    
    print("Forecasting Metrics:")
    metrics = ForecastingMetrics.compute_all(y_true, y_pred, y_train)
    for name, value in metrics.items():
        print(f"{name}: {value:.2f}")
    
    # Anomaly detection example
    print("\nAnomaly Detection Metrics:")
    y_true_anomaly = np.array([0, 0, 1, 0, 1, 1, 0, 0])
    y_pred_anomaly = np.array([0, 0, 1, 0, 0, 1, 1, 0])
    y_scores_anomaly = np.array([0.1, 0.2, 0.9, 0.3, 0.4, 0.8, 0.6, 0.2])
    
    anomaly_metrics = AnomalyDetectionMetrics.compute_all(
        y_true_anomaly, y_pred_anomaly, y_scores_anomaly
    )
    for name, value in anomaly_metrics.items():
        print(f"{name}: {value}")
