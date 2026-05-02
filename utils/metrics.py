"""
Performance metrics calculator
"""
import numpy as np
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate performance metrics for the system"""
    
    @staticmethod
    def forecast_accuracy_metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict:
        """Calculate forecasting accuracy metrics"""
        try:
            mae = np.mean(np.abs(actual - predicted))
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            mape = np.mean(np.abs((actual - predicted) / (actual + 1e-10))) * 100
            
            # R-squared
            ss_res = np.sum((actual - predicted) ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            r2 = 1 - (ss_res / (ss_tot + 1e-10))
            
            return {
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
                'r2': float(r2)
            }
        except Exception as e:
            logger.error(f"Error calculating forecast metrics: {e}")
            return {}
    
    @staticmethod
    def energy_efficiency_metrics(generation: List[float], 
                                  demand: List[float],
                                  battery_data: Dict) -> Dict:
        """Calculate energy efficiency metrics"""
        try:
            total_generation = sum(generation)
            total_demand = sum(demand)
            
            # Self-sufficiency ratio
            self_sufficiency = (total_generation / (total_demand + 1e-10)) * 100
            
            # Energy waste (excess generation not stored or used)
            excess = [max(0, g - d) for g, d in zip(generation, demand)]
            total_excess = sum(excess)
            waste_ratio = (total_excess / (total_generation + 1e-10)) * 100
            
            # Battery efficiency
            battery_utilization = battery_data.get('avg_level', 0) / battery_data.get('capacity', 100) * 100
            
            return {
                'self_sufficiency': float(self_sufficiency),
                'waste_ratio': float(waste_ratio),
                'battery_utilization': float(battery_utilization),
                'total_generation': float(total_generation),
                'total_demand': float(total_demand)
            }
        except Exception as e:
            logger.error(f"Error calculating efficiency metrics: {e}")
            return {}
    
    @staticmethod
    def cost_savings_metrics(baseline_cost: float, 
                           optimized_cost: float,
                           revenue: float = 0) -> Dict:
        """Calculate cost savings metrics"""
        try:
            savings = baseline_cost - optimized_cost
            savings_percentage = (savings / (baseline_cost + 1e-10)) * 100
            
            net_savings = savings + revenue
            
            return {
                'absolute_savings': float(savings),
                'savings_percentage': float(savings_percentage),
                'revenue': float(revenue),
                'net_savings': float(net_savings),
                'baseline_cost': float(baseline_cost),
                'optimized_cost': float(optimized_cost)
            }
        except Exception as e:
            logger.error(f"Error calculating cost metrics: {e}")
            return {}
    
    @staticmethod
    def system_reliability_metrics(uptime_hours: float, 
                                   total_hours: float,
                                   outages: int) -> Dict:
        """Calculate system reliability metrics"""
        try:
            availability = (uptime_hours / (total_hours + 1e-10)) * 100
            mtbf = uptime_hours / (outages + 1) if outages > 0 else uptime_hours
            
            return {
                'availability': float(availability),
                'uptime_hours': float(uptime_hours),
                'total_hours': float(total_hours),
                'mtbf': float(mtbf),
                'outages': int(outages)
            }
        except Exception as e:
            logger.error(f"Error calculating reliability metrics: {e}")
            return {}
    
    @staticmethod
    def carbon_footprint_metrics(grid_import: List[float],
                                renewable_generation: List[float],
                                grid_carbon_intensity: float = 0.5) -> Dict:
        """
        Calculate carbon footprint metrics
        
        Args:
            grid_import: Energy imported from grid (kWh)
            renewable_generation: Renewable energy generated (kWh)
            grid_carbon_intensity: kg CO2 per kWh (default 0.5)
        """
        try:
            total_grid_import = sum(grid_import)
            total_renewable = sum(renewable_generation)
            
            # Carbon emissions from grid
            carbon_emissions = total_grid_import * grid_carbon_intensity
            
            # Carbon avoided by using renewables
            carbon_avoided = total_renewable * grid_carbon_intensity
            
            # Net carbon savings
            net_savings = carbon_avoided - carbon_emissions
            
            return {
                'carbon_emissions_kg': float(carbon_emissions),
                'carbon_avoided_kg': float(carbon_avoided),
                'net_carbon_savings_kg': float(net_savings),
                'renewable_percentage': float((total_renewable / (total_renewable + total_grid_import + 1e-10)) * 100)
            }
        except Exception as e:
            logger.error(f"Error calculating carbon metrics: {e}")
            return {}
    
    @staticmethod
    def peak_demand_metrics(demand: List[float], 
                          timestamps: List[datetime]) -> Dict:
        """Calculate peak demand metrics"""
        try:
            peak_demand = max(demand)
            peak_index = demand.index(peak_demand)
            peak_time = timestamps[peak_index] if peak_index < len(timestamps) else None
            
            avg_demand = np.mean(demand)
            load_factor = (avg_demand / (peak_demand + 1e-10)) * 100
            
            return {
                'peak_demand': float(peak_demand),
                'peak_time': peak_time.isoformat() if peak_time else None,
                'average_demand': float(avg_demand),
                'load_factor': float(load_factor)
            }
        except Exception as e:
            logger.error(f"Error calculating peak demand metrics: {e}")
            return {}
    
    @staticmethod
    def generate_performance_report(forecast_metrics: Dict,
                                   efficiency_metrics: Dict,
                                   cost_metrics: Dict) -> Dict:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'forecasting_performance': forecast_metrics,
            'energy_efficiency': efficiency_metrics,
            'cost_analysis': cost_metrics,
            'overall_score': MetricsCalculator._calculate_overall_score(
                forecast_metrics, efficiency_metrics, cost_metrics
            )
        }
        
        return report
    
    @staticmethod
    def _calculate_overall_score(forecast_metrics: Dict,
                                efficiency_metrics: Dict,
                                cost_metrics: Dict) -> float:
        """Calculate overall system performance score (0-100)"""
        try:
            scores = []
            
            # Forecasting score (based on R²)
            if 'r2' in forecast_metrics:
                scores.append(max(0, forecast_metrics['r2'] * 100))
            
            # Efficiency score (based on self-sufficiency)
            if 'self_sufficiency' in efficiency_metrics:
                scores.append(min(100, efficiency_metrics['self_sufficiency']))
            
            # Cost score (based on savings percentage)
            if 'savings_percentage' in cost_metrics:
                scores.append(min(100, max(0, cost_metrics['savings_percentage'])))
            
            if not scores:
                return 0.0
            
            return float(np.mean(scores))
            
        except Exception as e:
            logger.error(f"Error calculating overall score: {e}")
            return 0.0
