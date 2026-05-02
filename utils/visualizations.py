"""
Visualization utilities for dashboard charts and graphs
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def create_demand_forecast_chart(timestamps: List, 
                                 actual: Optional[List] = None,
                                 predicted: List = None,
                                 title: str = "Energy Demand Forecast") -> go.Figure:
    """Create demand forecast visualization"""
    fig = go.Figure()
    
    if actual is not None:
        fig.add_trace(go.Scatter(
            x=timestamps[:len(actual)],
            y=actual,
            mode='lines',
            name='Actual Demand',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='<b>Actual</b><br>Time: %{x}<br>Demand: %{y:.2f} kWh<extra></extra>'
        ))
    
    if predicted is not None:
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=predicted,
            mode='lines',
            name='Predicted Demand',
            line=dict(color='#A23B72', width=2, dash='dash'),
            hovertemplate='<b>Predicted</b><br>Time: %{x}<br>Demand: %{y:.2f} kWh<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='#1a1a1a')),
        xaxis_title="Time",
        yaxis_title="Energy Demand (kWh)",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    
    return fig


def create_generation_forecast_chart(timestamps: List,
                                     solar: List,
                                     predicted: Optional[List] = None,
                                     title: str = "Renewable Generation Forecast") -> go.Figure:
    """Create generation forecast visualization"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=solar,
        mode='lines',
        name='Solar Generation',
        fill='tozeroy',
        line=dict(color='#F18F01', width=2),
        hovertemplate='<b>Solar</b><br>Time: %{x}<br>Generation: %{y:.2f} kWh<extra></extra>'
    ))
    
    if predicted is not None:
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=predicted,
            mode='lines',
            name='Predicted Generation',
            line=dict(color='#C73E1D', width=2, dash='dot'),
            hovertemplate='<b>Predicted</b><br>Time: %{x}<br>Generation: %{y:.2f} kWh<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='#1a1a1a')),
        xaxis_title="Time",
        yaxis_title="Energy Generation (kWh)",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    
    return fig


def create_battery_status_chart(timestamps: List,
                                battery_levels: List,
                                capacity: float = 100) -> go.Figure:
    """Create battery status visualization"""
    fig = go.Figure()
    
    # Battery level
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=battery_levels,
        mode='lines',
        name='Battery Level',
        fill='tozeroy',
        line=dict(color='#06A77D', width=3),
        fillcolor='rgba(6, 167, 125, 0.3)',
        hovertemplate='<b>Battery</b><br>Time: %{x}<br>Level: %{y:.1f} kWh<extra></extra>'
    ))
    
    # Capacity line
    fig.add_shape(
        type="line",
        x0=timestamps[0], x1=timestamps[-1],
        y0=capacity, y1=capacity,
        line=dict(color="red", width=2, dash="dash")
    )
    
    fig.add_annotation(
        x=timestamps[-1], y=capacity,
        text=f"Capacity: {capacity} kWh",
        showarrow=False,
        xanchor='left',
        font=dict(color='red', size=10)
    )
    
    fig.update_layout(
        title=dict(text="Battery Storage Status", font=dict(size=20, color='#1a1a1a')),
        xaxis_title="Time",
        yaxis_title="Battery Level (kWh)",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        height=350,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    
    return fig


def create_energy_flow_chart(generation: float, demand: float, 
                            battery_charge: float, grid_import: float,
                            grid_export: float) -> go.Figure:
    """Create Sankey diagram for energy flow"""
    
    # Define nodes
    nodes = ['Solar', 'Battery Discharge', 'Grid Import', 
            'Demand', 'Battery Charge', 'Grid Export']
    
    # Define flows
    sources = []
    targets = []
    values = []
    colors = []
    
    # Solar to demand
    if generation > 0:
        sources.append(0)  # Solar
        targets.append(3)  # Demand
        values.append(min(generation, demand))
        colors.append('rgba(241, 143, 1, 0.4)')
    
    # Solar to battery
    if battery_charge > 0:
        sources.append(0)  # Solar
        targets.append(4)  # Battery Charge
        values.append(battery_charge)
        colors.append('rgba(6, 167, 125, 0.4)')
    
    # Solar to grid export
    if grid_export > 0:
        sources.append(0)  # Solar
        targets.append(5)  # Grid Export
        values.append(grid_export)
        colors.append('rgba(46, 134, 171, 0.4)')
    
    # Grid import to demand
    if grid_import > 0:
        sources.append(2)  # Grid Import
        targets.append(3)  # Demand
        values.append(grid_import)
        colors.append('rgba(162, 59, 114, 0.4)')
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes,
            color=['#F18F01', '#06A77D', '#A23B72', '#2E86AB', '#06A77D', '#2E86AB']
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors
        )
    )])
    
    fig.update_layout(
        title=dict(text="Real-Time Energy Flow", font=dict(size=20, color='#1a1a1a')),
        font=dict(family='Inter, sans-serif', size=12),
        height=400,
        margin=dict(l=20, r=20, t=80, b=20),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_cost_analysis_chart(timestamps: List, costs: List, 
                               revenues: List) -> go.Figure:
    """Create cost and revenue analysis chart"""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=timestamps,
        y=costs,
        name='Costs',
        marker_color='#C73E1D',
        hovertemplate='<b>Cost</b><br>Time: %{x}<br>Amount: $%{y:.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        x=timestamps,
        y=revenues,
        name='Revenue',
        marker_color='#06A77D',
        hovertemplate='<b>Revenue</b><br>Time: %{x}<br>Amount: $%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text="Cost vs Revenue Analysis", font=dict(size=20, color='#1a1a1a')),
        xaxis_title="Time",
        yaxis_title="Amount ($)",
        barmode='group',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        height=350,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    
    return fig


def create_performance_metrics_chart(metrics: Dict) -> go.Figure:
    """Create performance metrics comparison chart"""
    metric_names = list(metrics.keys())
    metric_values = list(metrics.values())
    
    fig = go.Figure(data=[
        go.Bar(
            x=metric_names,
            y=metric_values,
            marker=dict(
                color=metric_values,
                colorscale='Viridis',
                showscale=True
            ),
            text=[f"{v:.2f}" for v in metric_values],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Value: %{y:.4f}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=dict(text="Model Performance Metrics", font=dict(size=20, color='#1a1a1a')),
        xaxis_title="Metric",
        yaxis_title="Value",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    
    return fig


def create_gauge_chart(value: float, max_value: float, 
                      title: str, unit: str = "%") -> go.Figure:
    """Create gauge chart for single metric"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 18}},
        number={'suffix': f" {unit}"},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "#06A77D"},
            'steps': [
                {'range': [0, max_value * 0.33], 'color': "#FFE5E5"},
                {'range': [max_value * 0.33, max_value * 0.66], 'color': "#FFF4E5"},
                {'range': [max_value * 0.66, max_value], 'color': "#E5F9F5"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif'),
        height=250,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig


def create_comparison_chart(data: pd.DataFrame, x_col: str, 
                           y_cols: List[str], title: str) -> go.Figure:
    """Create multi-line comparison chart"""
    fig = go.Figure()
    
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#06A77D', '#C73E1D']
    
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=data[x_col],
            y=data[col],
            mode='lines+markers',
            name=col,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='#1a1a1a')),
        xaxis_title=x_col,
        yaxis_title="Value",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E0E0E0')
    
    return fig
