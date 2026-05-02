"""
Energy optimization engine using linear programming
"""
import numpy as np
from scipy.optimize import linprog
from pulp import LpMaximize, LpMinimize, LpProblem, LpVariable, lpSum, LpStatus
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EnergyOptimizer:
    """Optimize energy allocation and storage"""
    
    def __init__(self, battery_capacity: float = 100.0, 
                 max_charge_rate: float = 20.0,
                 max_discharge_rate: float = 20.0,
                 user_data: Optional[Dict] = None):
        """
        Initialize optimizer
        
        Args:
            battery_capacity: Maximum battery capacity (kWh)
            max_charge_rate: Maximum charging rate (kW)
            max_discharge_rate: Maximum discharging rate (kW)
            user_data: User profile with location and rate information
        """
        self.battery_capacity = battery_capacity
        self.max_charge_rate = max_charge_rate
        self.max_discharge_rate = max_discharge_rate
        self.user_data = user_data or {}
        
        # Get location-specific rates
        from config import config
        country = self.user_data.get('country', 'Nigeria')
        state = self.user_data.get('state', '')
        self.base_rate = config.get_electricity_rate(country, state, 'base_rate')
        self.peak_rate = config.get_electricity_rate(country, state, 'peak_rate')
        self.off_peak_rate = config.get_electricity_rate(country, state, 'off_peak_rate')
        
        # Nigeria band adjustment
        if country == "Nigeria" and 'band_rate' in self.user_data:
            band_rate_usd = self.user_data['band_rate'] / 1500  # Convert Naira to USD
            self.base_rate = band_rate_usd
            self.peak_rate = band_rate_usd * 1.5
            self.off_peak_rate = band_rate_usd * 0.7
        
    def optimize_energy_allocation(self, 
                                   demand_forecast: np.ndarray,
                                   generation_forecast: np.ndarray,
                                   current_battery_level: float,
                                   grid_prices: Optional[np.ndarray] = None,
                                   time_horizon: int = 24) -> Dict:
        """
        Optimize energy allocation for the next time horizon
        
        Args:
            demand_forecast: Predicted energy demand (kWh)
            generation_forecast: Predicted renewable generation (kWh)
            current_battery_level: Current battery state of charge (kWh)
            grid_prices: Electricity prices per hour (optional)
            time_horizon: Number of hours to optimize
            
        Returns:
            Dictionary with optimization results
        """
        try:
            # Ensure arrays are correct length
            demand = demand_forecast[:time_horizon]
            generation = generation_forecast[:time_horizon]
            
            if grid_prices is None:
                # Use location-specific time-of-use pricing
                grid_prices = np.array([
                    self.peak_rate if 9 <= h % 24 < 17 else  # Peak hours: 9 AM - 5 PM
                    self.off_peak_rate if (h % 24 < 6 or h % 24 >= 22) else  # Off-peak: 10 PM - 6 AM
                    self.base_rate  # Standard hours
                    for h in range(time_horizon)
                ])
            else:
                grid_prices = grid_prices[:time_horizon]
            
            # Create optimization problem
            prob = LpProblem("Energy_Optimization", LpMinimize)
            
            # Decision variables
            grid_import = [LpVariable(f"grid_import_{t}", lowBound=0) 
                          for t in range(time_horizon)]
            grid_export = [LpVariable(f"grid_export_{t}", lowBound=0) 
                          for t in range(time_horizon)]
            battery_charge = [LpVariable(f"battery_charge_{t}", lowBound=0, 
                                        upBound=self.max_charge_rate) 
                             for t in range(time_horizon)]
            battery_discharge = [LpVariable(f"battery_discharge_{t}", lowBound=0, 
                                           upBound=self.max_discharge_rate) 
                                for t in range(time_horizon)]
            battery_level = [LpVariable(f"battery_level_{t}", lowBound=0, 
                                       upBound=self.battery_capacity) 
                            for t in range(time_horizon)]
            
            # Objective: Minimize cost (import cost - export revenue)
            import_cost = lpSum([grid_import[t] * grid_prices[t] 
                               for t in range(time_horizon)])
            export_revenue = lpSum([grid_export[t] * grid_prices[t] * 0.8 
                                  for t in range(time_horizon)])
            prob += import_cost - export_revenue
            
            # Constraints
            for t in range(time_horizon):
                # Energy balance
                prob += (generation[t] + grid_import[t] + battery_discharge[t] == 
                        demand[t] + grid_export[t] + battery_charge[t])
                
                # Battery dynamics
                if t == 0:
                    prob += battery_level[t] == (current_battery_level + 
                                                 battery_charge[t] - 
                                                 battery_discharge[t])
                else:
                    prob += battery_level[t] == (battery_level[t-1] + 
                                                 battery_charge[t] - 
                                                 battery_discharge[t])
            
            # Solve
            prob.solve()
            
            if LpStatus[prob.status] == 'Optimal':
                # Extract results
                results = {
                    'status': 'optimal',
                    'timestamp': datetime.now().isoformat(),
                    'objective_value': prob.objective.value(),
                    'grid_import': [var.value() for var in grid_import],
                    'grid_export': [var.value() for var in grid_export],
                    'battery_charge': [var.value() for var in battery_charge],
                    'battery_discharge': [var.value() for var in battery_discharge],
                    'battery_level': [var.value() for var in battery_level],
                    'total_cost': sum([grid_import[t].value() * grid_prices[t] 
                                     for t in range(time_horizon)]),
                    'total_revenue': sum([grid_export[t].value() * grid_prices[t] * 0.8 
                                        for t in range(time_horizon)]),
                    'energy_saved': sum([generation[t] - demand[t] 
                                       for t in range(time_horizon) 
                                       if generation[t] > demand[t]]),
                    'recommendations': self._generate_recommendations(
                        demand, generation, 
                        [var.value() for var in battery_level]
                    )
                }
                
                logger.info(f"Optimization successful. Cost: ${results['total_cost']:.2f}")
                return results
            else:
                logger.warning(f"Optimization failed: {LpStatus[prob.status]}")
                return {'status': 'failed', 'message': LpStatus[prob.status]}
                
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _generate_recommendations(self, demand: np.ndarray, 
                                 generation: np.ndarray, 
                                 battery_levels: List[float]) -> List[str]:
        """Generate actionable recommendations based on optimization"""
        recommendations = []
        
        # Check for high demand periods
        high_demand_hours = np.where(demand > np.percentile(demand, 75))[0]
        if len(high_demand_hours) > 0:
            recommendations.append(
                f"High demand expected at hours {high_demand_hours.tolist()}. "
                "Consider pre-charging battery."
            )
        
        # Check for excess generation
        excess_gen = generation - demand
        surplus_hours = np.where(excess_gen > 0)[0]
        if len(surplus_hours) > 0:
            recommendations.append(
                f"Surplus generation at hours {surplus_hours.tolist()}. "
                "Optimal to charge battery or export to grid."
            )
        
        # Battery management
        avg_battery = np.mean(battery_levels)
        if avg_battery < self.battery_capacity * 0.2:
            recommendations.append(
                "Battery levels consistently low. Consider increasing charging rate."
            )
        elif avg_battery > self.battery_capacity * 0.8:
            recommendations.append(
                "Battery frequently near capacity. Consider exporting excess energy."
            )
        
        # Grid interaction
        deficit_hours = np.where(generation < demand)[0]
        if len(deficit_hours) > len(demand) * 0.5:
            recommendations.append(
                "Renewable generation insufficient for majority of period. "
                "Grid import or additional generation capacity recommended."
            )
        
        return recommendations if recommendations else ["Energy system operating optimally."]
    
    def simulate_scenario(self, scenario_params: Dict) -> Dict:
        """
        Simulate different grid scenarios
        
        Args:
            scenario_params: Dictionary with scenario parameters
                - demand_multiplier: Scale demand by this factor
                - generation_multiplier: Scale generation by this factor
                - battery_capacity_change: Percentage change in battery capacity
                
        Returns:
            Simulation results
        """
        try:
            # Get multipliers
            demand_mult = scenario_params.get('demand_multiplier', 1.0)
            gen_mult = scenario_params.get('generation_multiplier', 1.0)
            battery_change = scenario_params.get('battery_capacity_change', 0)
            
            # Adjust battery capacity
            original_capacity = self.battery_capacity
            self.battery_capacity *= (1 + battery_change / 100)
            
            # Generate sample data for simulation
            hours = 24
            base_demand = np.random.uniform(50, 100, hours)
            base_generation = np.random.uniform(30, 80, hours)
            
            # Apply multipliers
            demand = base_demand * demand_mult
            generation = base_generation * gen_mult
            
            # Run optimization
            result = self.optimize_energy_allocation(
                demand, generation, 
                self.battery_capacity * 0.5  # Start at 50%
            )
            
            # Restore original capacity
            self.battery_capacity = original_capacity
            
            # Add scenario info
            result['scenario'] = scenario_params
            
            return result
            
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def calculate_efficiency_metrics(self, optimization_result: Dict) -> Dict:
        """Calculate efficiency metrics from optimization results"""
        try:
            metrics = {}
            
            if optimization_result.get('status') != 'optimal':
                return metrics
            
            # Self-sufficiency ratio
            total_generation = sum(optimization_result.get('grid_export', [])) + \
                             sum(optimization_result.get('battery_charge', []))
            total_demand = sum(optimization_result.get('grid_import', []))
            
            if total_demand > 0:
                metrics['self_sufficiency'] = (total_generation / total_demand) * 100
            
            # Battery utilization
            battery_levels = optimization_result.get('battery_level', [])
            if battery_levels:
                metrics['avg_battery_level'] = np.mean(battery_levels)
                metrics['battery_utilization'] = (np.mean(battery_levels) / 
                                                 self.battery_capacity) * 100
            
            # Cost efficiency
            total_cost = optimization_result.get('total_cost', 0)
            total_revenue = optimization_result.get('total_revenue', 0)
            metrics['net_cost'] = total_cost - total_revenue
            
            # Energy waste
            energy_saved = optimization_result.get('energy_saved', 0)
            metrics['energy_saved_kwh'] = energy_saved
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}


class RealTimeOptimizer(EnergyOptimizer):
    """Real-time optimization with adaptive parameters"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.historical_data = []
        
    def add_historical_data(self, actual_demand: float, actual_generation: float):
        """Add actual data point for learning"""
        self.historical_data.append({
            'timestamp': datetime.now(),
            'demand': actual_demand,
            'generation': actual_generation
        })
        
        # Keep last 168 hours (1 week)
        if len(self.historical_data) > 168:
            self.historical_data.pop(0)
    
    def adaptive_optimize(self, demand_forecast: np.ndarray,
                         generation_forecast: np.ndarray,
                         current_battery_level: float) -> Dict:
        """
        Optimization with adaptive learning from historical data
        """
        # Adjust forecasts based on historical accuracy
        if len(self.historical_data) > 24:
            recent_data = self.historical_data[-24:]
            
            # Calculate forecast bias
            avg_demand = np.mean([d['demand'] for d in recent_data])
            avg_generation = np.mean([d['generation'] for d in recent_data])
            
            # Adjust current forecasts
            demand_adjusted = demand_forecast * (avg_demand / np.mean(demand_forecast))
            generation_adjusted = generation_forecast * (avg_generation / np.mean(generation_forecast))
            
            # Use adjusted forecasts
            return self.optimize_energy_allocation(
                demand_adjusted, generation_adjusted, current_battery_level
            )
        else:
            # Not enough data, use standard optimization
            return self.optimize_energy_allocation(
                demand_forecast, generation_forecast, current_battery_level
            )


class BatteryOptimizer:
    """
    Battery optimization using convex optimization (CVXPY)
    
    Optimizes battery charging/discharging schedule to:
    - Minimize electricity costs
    - Maximize renewable energy usage
    - Maintain battery health
    - Meet load demand
    """
    
    def __init__(
        self,
        battery_capacity: float,
        max_charge_rate: float,
        max_discharge_rate: float,
        charge_efficiency: float = 0.95,
        discharge_efficiency: float = 0.95,
        min_soc: float = 0.2,
        max_soc: float = 0.95
    ):
        """
        Initialize battery optimizer
        
        Args:
            battery_capacity: Battery capacity in MWh
            max_charge_rate: Maximum charging rate in MW
            max_discharge_rate: Maximum discharging rate in MW
            charge_efficiency: Charging efficiency (0-1)
            discharge_efficiency: Discharging efficiency (0-1)
            min_soc: Minimum state of charge (0-1)
            max_soc: Maximum state of charge (0-1)
        """
        self.capacity = battery_capacity
        self.max_charge = max_charge_rate
        self.max_discharge = max_discharge_rate
        self.charge_eff = charge_efficiency
        self.discharge_eff = discharge_efficiency
        self.min_soc = min_soc * battery_capacity
        self.max_soc = max_soc * battery_capacity
        
    def optimize(
        self,
        solar_forecast: np.ndarray,
        load_forecast: np.ndarray,
        initial_soc: float,
        grid_price: np.ndarray,
        export_price: np.ndarray = None
    ) -> Dict:
        """
        Optimize battery schedule
        
        Args:
            solar_forecast: Solar generation forecast (MW) for each hour
            load_forecast: Load demand forecast (MW) for each hour
            initial_soc: Initial battery state of charge (MWh)
            grid_price: Grid electricity price ($/MWh) for each hour
            export_price: Export price ($/MWh), defaults to 70% of grid price
        
        Returns:
            Dictionary with optimization results
        """
        try:
            import cvxpy as cp
            
            n_hours = len(solar_forecast)
            
            if export_price is None:
                export_price = grid_price * 0.7
            
            # Decision variables
            charge = cp.Variable(n_hours, nonneg=True)  # Charging power (MW)
            discharge = cp.Variable(n_hours, nonneg=True)  # Discharging power (MW)
            soc = cp.Variable(n_hours + 1, nonneg=True)  # State of charge (MWh)
            grid_import = cp.Variable(n_hours, nonneg=True)  # Grid import (MW)
            grid_export = cp.Variable(n_hours, nonneg=True)  # Grid export (MW)
            
            # Constraints
            constraints = []
            
            # Initial SOC
            constraints.append(soc[0] == initial_soc)
            
            # SOC dynamics
            for t in range(n_hours):
                constraints.append(
                    soc[t + 1] == soc[t] + charge[t] * self.charge_eff - discharge[t] / self.discharge_eff
                )
            
            # SOC limits
            constraints.append(soc >= self.min_soc)
            constraints.append(soc <= self.max_soc)
            
            # Charge/discharge rate limits
            constraints.append(charge <= self.max_charge)
            constraints.append(discharge <= self.max_discharge)
            
            # Power balance: solar + discharge + grid_import = load + charge + grid_export
            for t in range(n_hours):
                constraints.append(
                    solar_forecast[t] + discharge[t] + grid_import[t] ==
                    load_forecast[t] + charge[t] + grid_export[t]
                )
            
            # Objective: minimize cost
            cost = cp.sum(cp.multiply(grid_price, grid_import)) - cp.sum(cp.multiply(export_price, grid_export))
            
            # Solve optimization problem
            problem = cp.Problem(cp.Minimize(cost), constraints)
            problem.solve(solver=cp.ECOS)
            
            if problem.status in ['optimal', 'optimal_inaccurate']:
                # Calculate additional metrics
                renewable_used = np.sum(np.minimum(solar_forecast, load_forecast + charge.value))
                total_solar = np.sum(solar_forecast)
                renewable_usage = (renewable_used / total_solar * 100) if total_solar > 0 else 0
                
                # Calculate battery cycles
                total_discharged = np.sum(discharge.value)
                battery_cycles = total_discharged / self.capacity if self.capacity > 0 else 0
                
                return {
                    'status': 'optimal',
                    'total_cost': float(cost.value),
                    'charge': charge.value,
                    'discharge': discharge.value,
                    'soc': soc.value[:-1],  # Exclude final SOC
                    'grid_import': grid_import.value,
                    'grid_export': grid_export.value,
                    'renewable_usage': float(renewable_usage),
                    'battery_cycles': float(battery_cycles)
                }
            else:
                logger.warning(f"Optimization status: {problem.status}")
                return {
                    'status': 'failed',
                    'message': f"Optimization failed with status: {problem.status}"
                }
                
        except Exception as e:
            logger.error(f"Battery optimization error: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def simulate_baseline(
        self,
        solar_forecast: np.ndarray,
        load_forecast: np.ndarray
    ) -> Dict:
        """
        Simulate baseline scenario without battery optimization
        (All excess solar exported, all deficit imported)
        
        Returns:
            Dictionary with baseline metrics
        """
        try:
            net_power = solar_forecast - load_forecast
            grid_import = np.maximum(-net_power, 0)  # Import when load > solar
            grid_export = np.maximum(net_power, 0)   # Export when solar > load
            
            return {
                'grid_import': grid_import,
                'grid_export': grid_export,
                'total_import': float(np.sum(grid_import)),
                'total_export': float(np.sum(grid_export))
            }
            
        except Exception as e:
            logger.error(f"Baseline simulation error: {e}", exc_info=True)
            return {
                'error': str(e)
            }
