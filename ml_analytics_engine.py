"""
Machine Learning Analytics Engine for Industrial SCADA Systems
Advanced predictive analytics, anomaly detection, and optimization algorithms
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
import joblib
import json
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Conv1D, MaxPooling1D, Flatten
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsType(Enum):
    """Types of analytics operations"""
    ANOMALY_DETECTION = "anomaly_detection"
    PREDICTIVE_MAINTENANCE = "predictive_maintenance"
    PROCESS_OPTIMIZATION = "process_optimization"
    TREND_ANALYSIS = "trend_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    QUALITY_CONTROL = "quality_control"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class AnalyticsResult:
    """Analytics operation result"""
    analysis_type: AnalyticsType
    timestamp: datetime
    confidence: float
    predictions: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    alerts: List[Dict[str, Any]]

class TimeSeriesAnomalyDetector:
    """Advanced anomaly detection for time series data"""

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=200
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.baseline_stats = {}

    def train(self, data: pd.DataFrame, features: List[str]):
        """Train anomaly detection model"""
        try:
            # Prepare training data
            X = data[features].fillna(method='ffill').fillna(method='bfill')
            X_scaled = self.scaler.fit_transform(X)

            # Train isolation forest
            self.isolation_forest.fit(X_scaled)

            # Calculate baseline statistics
            self.baseline_stats = {
                feature: {
                    'mean': X[feature].mean(),
                    'std': X[feature].std(),
                    'min': X[feature].min(),
                    'max': X[feature].max(),
                    'q25': X[feature].quantile(0.25),
                    'q75': X[feature].quantile(0.75)
                }
                for feature in features
            }

            self.is_trained = True
            logger.info(f"Anomaly detector trained on {len(data)} samples")
            return True

        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}")
            return False

    def detect_anomalies(self, data: pd.DataFrame, features: List[str]) -> List[Dict[str, Any]]:
        """Detect anomalies in new data"""
        if not self.is_trained:
            logger.error("Model not trained. Call train() first.")
            return []

        try:
            anomalies = []
            X = data[features].fillna(method='ffill').fillna(method='bfill')
            X_scaled = self.scaler.transform(X)

            # Get anomaly scores
            scores = self.isolation_forest.decision_function(X_scaled)
            predictions = self.isolation_forest.predict(X_scaled)

            # Identify anomalous points
            anomaly_indices = np.where(predictions == -1)[0]

            for idx in anomaly_indices:
                anomaly_record = {
                    'timestamp': data.index[idx] if hasattr(data.index[idx], 'isoformat') else str(data.index[idx]),
                    'anomaly_score': float(scores[idx]),
                    'affected_features': [],
                    'severity': self._calculate_severity(scores[idx]),
                    'description': 'Anomalous behavior detected'
                }

                # Identify which features contributed to the anomaly
                for i, feature in enumerate(features):
                    value = X.iloc[idx, i]
                    stats = self.baseline_stats[feature]

                    # Check if value is outside normal range
                    if value > stats['q75'] + 1.5 * (stats['q75'] - stats['q25']) or \
                       value < stats['q25'] - 1.5 * (stats['q75'] - stats['q25']):
                        anomaly_record['affected_features'].append({
                            'feature': feature,
                            'value': float(value),
                            'expected_range': [float(stats['q25']), float(stats['q75'])],
                            'deviation': abs(value - stats['mean']) / stats['std']
                        })

                anomalies.append(anomaly_record)

            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    def _calculate_severity(self, score: float) -> AlertSeverity:
        """Calculate alert severity based on anomaly score"""
        if score < -0.7:
            return AlertSeverity.EMERGENCY
        elif score < -0.5:
            return AlertSeverity.CRITICAL
        elif score < -0.3:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

class PredictiveMaintenanceEngine:
    """Predictive maintenance using ML algorithms"""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.equipment_profiles = {}

    def create_equipment_profile(self, equipment_id: str, sensor_features: List[str],
                                maintenance_history: pd.DataFrame):
        """Create equipment profile for maintenance prediction"""
        try:
            # Analyze maintenance patterns
            if not maintenance_history.empty:
                avg_time_between_failures = maintenance_history['days_since_last_maintenance'].mean()
                failure_frequency = len(maintenance_history) / (
                    (maintenance_history['maintenance_date'].max() -
                     maintenance_history['maintenance_date'].min()).days / 365
                )
            else:
                avg_time_between_failures = 180  # Default 6 months
                failure_frequency = 2  # Default 2 times per year

            self.equipment_profiles[equipment_id] = {
                'sensor_features': sensor_features,
                'avg_mtbf': avg_time_between_failures,  # Mean Time Between Failures
                'failure_frequency': failure_frequency,
                'criticality_score': self._calculate_criticality(equipment_id),
                'maintenance_cost': self._estimate_maintenance_cost(equipment_id)
            }

            logger.info(f"Equipment profile created for {equipment_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating equipment profile: {e}")
            return False

    def train_maintenance_model(self, equipment_id: str, sensor_data: pd.DataFrame,
                               maintenance_events: pd.DataFrame):
        """Train predictive maintenance model"""
        try:
            if equipment_id not in self.equipment_profiles:
                logger.error(f"Equipment profile not found for {equipment_id}")
                return False

            # Prepare training data
            features = self.equipment_profiles[equipment_id]['sensor_features']
            X, y = self._prepare_maintenance_training_data(
                sensor_data, maintenance_events, features
            )

            if len(X) < 50:  # Minimum samples required
                logger.warning(f"Insufficient training data for {equipment_id}")
                return False

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train LSTM model for time series prediction
            model = self._build_lstm_model(X_train_scaled.shape[1])

            # Reshape for LSTM (samples, time steps, features)
            X_train_lstm = X_train_scaled.reshape((X_train_scaled.shape[0], 1, X_train_scaled.shape[1]))
            X_test_lstm = X_test_scaled.reshape((X_test_scaled.shape[0], 1, X_test_scaled.shape[1]))

            # Train model
            history = model.fit(
                X_train_lstm, y_train,
                epochs=100,
                batch_size=32,
                validation_data=(X_test_lstm, y_test),
                verbose=0
            )

            # Evaluate model
            predictions = model.predict(X_test_lstm)
            mse = mean_squared_error(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)

            # Store model and scaler
            self.models[equipment_id] = model
            self.scalers[equipment_id] = scaler

            logger.info(f"Maintenance model trained for {equipment_id} - MSE: {mse:.4f}, MAE: {mae:.4f}")
            return True

        except Exception as e:
            logger.error(f"Error training maintenance model: {e}")
            return False

    def predict_maintenance_needs(self, equipment_id: str,
                                 current_sensor_data: Dict[str, float]) -> Dict[str, Any]:
        """Predict maintenance needs for equipment"""
        try:
            if equipment_id not in self.models:
                logger.error(f"No trained model found for {equipment_id}")
                return {}

            model = self.models[equipment_id]
            scaler = self.scalers[equipment_id]
            profile = self.equipment_profiles[equipment_id]

            # Prepare input data
            features = profile['sensor_features']
            X = np.array([[current_sensor_data.get(feature, 0) for feature in features]])
            X_scaled = scaler.transform(X)
            X_lstm = X_scaled.reshape((1, 1, len(features)))

            # Make prediction
            remaining_useful_life = model.predict(X_lstm)[0][0]

            # Calculate maintenance recommendations
            maintenance_urgency = self._calculate_maintenance_urgency(
                remaining_useful_life, profile
            )

            # Generate recommendations
            recommendations = self._generate_maintenance_recommendations(
                equipment_id, remaining_useful_life, maintenance_urgency, current_sensor_data
            )

            return {
                'equipment_id': equipment_id,
                'remaining_useful_life_days': float(remaining_useful_life),
                'maintenance_urgency': maintenance_urgency.value,
                'confidence_score': self._calculate_prediction_confidence(X_scaled, features),
                'recommendations': recommendations,
                'estimated_cost': profile['maintenance_cost'],
                'risk_factors': self._identify_risk_factors(current_sensor_data, features)
            }

        except Exception as e:
            logger.error(f"Error predicting maintenance needs: {e}")
            return {}

    def _build_lstm_model(self, n_features: int):
        """Build LSTM model for maintenance prediction"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(1, n_features)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])

        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model

    def _prepare_maintenance_training_data(self, sensor_data: pd.DataFrame,
                                         maintenance_events: pd.DataFrame,
                                         features: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for maintenance prediction"""
        X, y = [], []

        for _, event in maintenance_events.iterrows():
            event_date = event['maintenance_date']

            # Get sensor data before maintenance event
            before_event = sensor_data[sensor_data.index <= event_date]
            if len(before_event) < 30:  # Need at least 30 data points
                continue

            # Use data from 30 days before maintenance
            training_window = before_event.tail(30)

            # Calculate features (mean, std, trend)
            feature_vector = []
            for feature in features:
                if feature in training_window.columns:
                    feature_vector.extend([
                        training_window[feature].mean(),
                        training_window[feature].std(),
                        training_window[feature].iloc[-1] - training_window[feature].iloc[0]  # trend
                    ])
                else:
                    feature_vector.extend([0, 0, 0])

            X.append(feature_vector)

            # Target is days until maintenance (from start of window)
            y.append(event.get('days_until_maintenance', 0))

        return np.array(X), np.array(y)

    def _calculate_criticality(self, equipment_id: str) -> float:
        """Calculate equipment criticality score"""
        # In production, this would be based on business rules
        criticality_map = {
            'pump': 0.8,
            'motor': 0.7,
            'valve': 0.6,
            'sensor': 0.4,
            'transformer': 0.9
        }

        for key, score in criticality_map.items():
            if key in equipment_id.lower():
                return score

        return 0.5  # Default

    def _estimate_maintenance_cost(self, equipment_id: str) -> float:
        """Estimate maintenance cost"""
        # In production, this would be based on historical data
        base_costs = {
            'pump': 5000,
            'motor': 3000,
            'valve': 1000,
            'sensor': 500,
            'transformer': 15000
        }

        for key, cost in base_costs.items():
            if key in equipment_id.lower():
                return cost

        return 2000  # Default

    def _calculate_maintenance_urgency(self, remaining_life: float,
                                     profile: Dict[str, Any]) -> AlertSeverity:
        """Calculate maintenance urgency"""
        criticality = profile['criticality_score']

        # Adjust threshold based on criticality
        if criticality > 0.8:
            if remaining_life < 7:
                return AlertSeverity.EMERGENCY
            elif remaining_life < 14:
                return AlertSeverity.CRITICAL
            elif remaining_life < 30:
                return AlertSeverity.WARNING
        else:
            if remaining_life < 3:
                return AlertSeverity.EMERGENCY
            elif remaining_life < 7:
                return AlertSeverity.CRITICAL
            elif remaining_life < 14:
                return AlertSeverity.WARNING

        return AlertSeverity.INFO

    def _generate_maintenance_recommendations(self, equipment_id: str, remaining_life: float,
                                            urgency: AlertSeverity, sensor_data: Dict[str, float]) -> List[str]:
        """Generate maintenance recommendations"""
        recommendations = []

        if urgency == AlertSeverity.EMERGENCY:
            recommendations.append("IMMEDIATE ACTION REQUIRED: Schedule emergency maintenance within 24 hours")
            recommendations.append("Consider temporary shutdown if safe operating conditions cannot be maintained")

        elif urgency == AlertSeverity.CRITICAL:
            recommendations.append("Schedule maintenance within 1 week")
            recommendations.append("Increase monitoring frequency")
            recommendations.append("Prepare spare parts and maintenance crew")

        elif urgency == AlertSeverity.WARNING:
            recommendations.append("Schedule preventive maintenance within 2-4 weeks")
            recommendations.append("Review maintenance procedures")

        # Add specific recommendations based on sensor readings
        for sensor, value in sensor_data.items():
            if 'temperature' in sensor.lower() and value > 80:
                recommendations.append("High temperature detected - check cooling systems")
            elif 'vibration' in sensor.lower() and value > 10:
                recommendations.append("Excessive vibration - inspect bearings and alignment")
            elif 'pressure' in sensor.lower() and value < 50:
                recommendations.append("Low pressure detected - check for leaks or blockages")

        return recommendations

    def _calculate_prediction_confidence(self, scaled_data: np.ndarray, features: List[str]) -> float:
        """Calculate confidence in prediction"""
        # Simple confidence based on data quality and feature completeness
        data_quality = 1.0 - np.sum(np.isnan(scaled_data)) / scaled_data.size
        feature_completeness = len(features) / 10  # Assume 10 is optimal

        return min(data_quality * feature_completeness, 1.0)

    def _identify_risk_factors(self, sensor_data: Dict[str, float], features: List[str]) -> List[str]:
        """Identify risk factors from current sensor readings"""
        risk_factors = []

        for feature in features:
            value = sensor_data.get(feature, 0)

            if 'temperature' in feature.lower():
                if value > 100:
                    risk_factors.append(f"Extreme temperature: {value}°C")
                elif value > 80:
                    risk_factors.append(f"High temperature: {value}°C")

            elif 'vibration' in feature.lower():
                if value > 15:
                    risk_factors.append(f"Severe vibration: {value} mm/s")
                elif value > 10:
                    risk_factors.append(f"High vibration: {value} mm/s")

            elif 'pressure' in feature.lower():
                if value < 30:
                    risk_factors.append(f"Low pressure: {value} bar")
                elif value > 150:
                    risk_factors.append(f"High pressure: {value} bar")

        return risk_factors

class ProcessOptimizationEngine:
    """Process optimization using advanced analytics"""

    def __init__(self):
        self.optimization_models = {}
        self.process_parameters = {}
        self.optimization_history = []

    def define_process_parameters(self, process_id: str, parameters: Dict[str, Dict[str, Any]]):
        """Define process parameters and constraints"""
        self.process_parameters[process_id] = parameters
        logger.info(f"Process parameters defined for {process_id}")

    def optimize_process(self, process_id: str, current_data: pd.DataFrame,
                        objective: str = 'efficiency') -> Dict[str, Any]:
        """Optimize process parameters"""
        try:
            if process_id not in self.process_parameters:
                logger.error(f"Process parameters not defined for {process_id}")
                return {}

            parameters = self.process_parameters[process_id]

            # Analyze current performance
            current_performance = self._analyze_current_performance(current_data, objective)

            # Generate optimization recommendations
            recommendations = self._generate_optimization_recommendations(
                current_data, parameters, objective
            )

            # Calculate potential improvements
            potential_improvement = self._estimate_improvement_potential(
                current_performance, recommendations
            )

            optimization_result = {
                'process_id': process_id,
                'current_performance': current_performance,
                'recommended_changes': recommendations,
                'potential_improvement': potential_improvement,
                'confidence_score': 0.85,  # Would be calculated based on data quality
                'implementation_priority': self._calculate_implementation_priority(recommendations),
                'estimated_roi': self._calculate_roi(potential_improvement, recommendations)
            }

            self.optimization_history.append(optimization_result)
            return optimization_result

        except Exception as e:
            logger.error(f"Error optimizing process {process_id}: {e}")
            return {}

    def _analyze_current_performance(self, data: pd.DataFrame, objective: str) -> Dict[str, float]:
        """Analyze current process performance"""
        performance = {}

        if objective == 'efficiency':
            # Calculate various efficiency metrics
            if 'energy_consumption' in data.columns and 'production_rate' in data.columns:
                performance['energy_efficiency'] = (
                    data['production_rate'].mean() / data['energy_consumption'].mean()
                )

            if 'waste_percentage' in data.columns:
                performance['material_efficiency'] = 100 - data['waste_percentage'].mean()

        elif objective == 'quality':
            if 'defect_rate' in data.columns:
                performance['quality_score'] = 100 - data['defect_rate'].mean()

        elif objective == 'throughput':
            if 'production_rate' in data.columns:
                performance['throughput'] = data['production_rate'].mean()

        return performance

    def _generate_optimization_recommendations(self, data: pd.DataFrame,
                                             parameters: Dict[str, Dict[str, Any]],
                                             objective: str) -> List[Dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []

        for param_name, param_config in parameters.items():
            if param_name in data.columns:
                current_value = data[param_name].mean()
                optimal_range = param_config.get('optimal_range', [])

                if optimal_range and len(optimal_range) == 2:
                    if current_value < optimal_range[0]:
                        recommendations.append({
                            'parameter': param_name,
                            'current_value': current_value,
                            'recommended_value': optimal_range[0],
                            'change_type': 'increase',
                            'expected_impact': param_config.get('impact_coefficient', 0.1)
                        })
                    elif current_value > optimal_range[1]:
                        recommendations.append({
                            'parameter': param_name,
                            'current_value': current_value,
                            'recommended_value': optimal_range[1],
                            'change_type': 'decrease',
                            'expected_impact': param_config.get('impact_coefficient', 0.1)
                        })

        return recommendations

    def _estimate_improvement_potential(self, current_performance: Dict[str, float],
                                       recommendations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Estimate potential improvement from recommendations"""
        improvements = {}

        for metric, current_value in current_performance.items():
            total_impact = sum(rec['expected_impact'] for rec in recommendations)
            potential_improvement = current_value * (1 + total_impact)
            improvements[f"{metric}_improvement"] = potential_improvement - current_value
            improvements[f"{metric}_improvement_percentage"] = (
                (potential_improvement - current_value) / current_value * 100
            )

        return improvements

    def _calculate_implementation_priority(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate implementation priority for recommendations"""
        prioritized = []

        for rec in recommendations:
            priority_score = rec['expected_impact'] * 100  # Simple priority calculation

            if priority_score > 10:
                priority = "High"
            elif priority_score > 5:
                priority = "Medium"
            else:
                priority = "Low"

            prioritized.append({
                **rec,
                'priority': priority,
                'priority_score': priority_score
            })

        return sorted(prioritized, key=lambda x: x['priority_score'], reverse=True)

    def _calculate_roi(self, improvements: Dict[str, float],
                      recommendations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate return on investment for optimizations"""
        # Simplified ROI calculation
        total_benefit = sum(improvements.values()) * 1000  # Convert to monetary value
        implementation_cost = len(recommendations) * 500  # Estimated cost per change

        if implementation_cost > 0:
            roi = (total_benefit - implementation_cost) / implementation_cost * 100
        else:
            roi = 0

        return {
            'estimated_annual_benefit': total_benefit,
            'implementation_cost': implementation_cost,
            'roi_percentage': roi,
            'payback_period_months': implementation_cost / (total_benefit / 12) if total_benefit > 0 else 0
        }

class MLAnalyticsEngine:
    """Main ML analytics engine coordinator"""

    def __init__(self):
        self.anomaly_detector = TimeSeriesAnomalyDetector()
        self.maintenance_engine = PredictiveMaintenanceEngine()
        self.optimization_engine = ProcessOptimizationEngine()
        self.analytics_history = []

    def run_comprehensive_analysis(self, process_data: pd.DataFrame,
                                  equipment_data: Dict[str, pd.DataFrame],
                                  analysis_config: Dict[str, Any]) -> AnalyticsResult:
        """Run comprehensive analytics analysis"""
        try:
            timestamp = datetime.now()
            predictions = {}
            anomalies = []
            recommendations = []
            alerts = []

            # Anomaly Detection
            if AnalyticsType.ANOMALY_DETECTION in analysis_config.get('enabled_analyses', []):
                features = analysis_config.get('anomaly_features', [])
                if features and not process_data.empty:
                    detected_anomalies = self.anomaly_detector.detect_anomalies(process_data, features)
                    anomalies.extend(detected_anomalies)

            # Predictive Maintenance
            if AnalyticsType.PREDICTIVE_MAINTENANCE in analysis_config.get('enabled_analyses', []):
                for equipment_id, data in equipment_data.items():
                    if not data.empty:
                        current_readings = data.iloc[-1].to_dict()
                        maintenance_prediction = self.maintenance_engine.predict_maintenance_needs(
                            equipment_id, current_readings
                        )
                        if maintenance_prediction:
                            predictions[f"{equipment_id}_maintenance"] = maintenance_prediction

            # Process Optimization
            if AnalyticsType.PROCESS_OPTIMIZATION in analysis_config.get('enabled_analyses', []):
                for process_id in analysis_config.get('optimization_processes', []):
                    optimization_result = self.optimization_engine.optimize_process(
                        process_id, process_data
                    )
                    if optimization_result:
                        predictions[f"{process_id}_optimization"] = optimization_result

            # Generate overall recommendations
            recommendations = self._generate_overall_recommendations(
                anomalies, predictions
            )

            # Create alerts
            alerts = self._generate_alerts(anomalies, predictions)

            # Calculate overall confidence
            confidence = self._calculate_overall_confidence(predictions, anomalies)

            result = AnalyticsResult(
                analysis_type=AnalyticsType.PATTERN_RECOGNITION,  # Comprehensive analysis
                timestamp=timestamp,
                confidence=confidence,
                predictions=predictions,
                anomalies=anomalies,
                recommendations=recommendations,
                alerts=alerts
            )

            self.analytics_history.append(result)
            logger.info(f"Comprehensive analysis completed with {len(anomalies)} anomalies and {len(predictions)} predictions")

            return result

        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return AnalyticsResult(
                analysis_type=AnalyticsType.PATTERN_RECOGNITION,
                timestamp=datetime.now(),
                confidence=0.0,
                predictions={},
                anomalies=[],
                recommendations=[],
                alerts=[]
            )

    def _generate_overall_recommendations(self, anomalies: List[Dict[str, Any]],
                                        predictions: Dict[str, Any]) -> List[str]:
        """Generate overall recommendations based on all analyses"""
        recommendations = []

        # Recommendations from anomalies
        if anomalies:
            recommendations.append(f"Investigate {len(anomalies)} detected anomalies immediately")

            critical_anomalies = [a for a in anomalies if a.get('severity') in ['critical', 'emergency']]
            if critical_anomalies:
                recommendations.append("URGENT: Address critical anomalies within 2 hours")

        # Recommendations from predictions
        maintenance_predictions = {k: v for k, v in predictions.items() if 'maintenance' in k}
        if maintenance_predictions:
            urgent_maintenance = [
                v for v in maintenance_predictions.values()
                if v.get('maintenance_urgency') in ['critical', 'emergency']
            ]
            if urgent_maintenance:
                recommendations.append(f"Schedule urgent maintenance for {len(urgent_maintenance)} equipment items")

        optimization_predictions = {k: v for k, v in predictions.items() if 'optimization' in k}
        if optimization_predictions:
            recommendations.append("Review process optimization recommendations to improve efficiency")

        return recommendations

    def _generate_alerts(self, anomalies: List[Dict[str, Any]],
                        predictions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on analysis results"""
        alerts = []

        # Alerts from anomalies
        for anomaly in anomalies:
            if anomaly.get('severity') in ['critical', 'emergency']:
                alerts.append({
                    'type': 'anomaly',
                    'severity': anomaly['severity'],
                    'message': f"Critical anomaly detected: {anomaly.get('description')}",
                    'timestamp': anomaly.get('timestamp'),
                    'action_required': True
                })

        # Alerts from maintenance predictions
        for pred_name, prediction in predictions.items():
            if 'maintenance' in pred_name:
                urgency = prediction.get('maintenance_urgency')
                if urgency in ['critical', 'emergency']:
                    alerts.append({
                        'type': 'maintenance',
                        'severity': urgency,
                        'message': f"Maintenance required for {prediction.get('equipment_id')}",
                        'timestamp': datetime.now().isoformat(),
                        'action_required': True,
                        'remaining_life': prediction.get('remaining_useful_life_days')
                    })

        return alerts

    def _calculate_overall_confidence(self, predictions: Dict[str, Any],
                                    anomalies: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in analysis results"""
        if not predictions and not anomalies:
            return 0.0

        # Average confidence from predictions
        pred_confidences = [
            pred.get('confidence_score', 0.5) for pred in predictions.values()
            if isinstance(pred, dict)
        ]

        # Simple confidence calculation
        if pred_confidences:
            return sum(pred_confidences) / len(pred_confidences)
        else:
            return 0.7  # Default confidence when only anomalies are detected

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get summary of recent analytics results"""
        if not self.analytics_history:
            return {}

        recent_results = self.analytics_history[-10:]  # Last 10 analyses

        return {
            'total_analyses': len(self.analytics_history),
            'recent_analyses': len(recent_results),
            'average_confidence': np.mean([r.confidence for r in recent_results]),
            'total_anomalies': sum(len(r.anomalies) for r in recent_results),
            'total_predictions': sum(len(r.predictions) for r in recent_results),
            'critical_alerts': sum(
                len([a for a in r.alerts if a.get('severity') in ['critical', 'emergency']])
                for r in recent_results
            ),
            'last_analysis': recent_results[-1].timestamp.isoformat() if recent_results else None
        }

# Example usage
if __name__ == "__main__":
    # Initialize ML Analytics Engine
    analytics_engine = MLAnalyticsEngine()

    # Generate sample data
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='H')
    process_data = pd.DataFrame({
        'timestamp': dates,
        'temperature': np.random.normal(75, 10, len(dates)),
        'pressure': np.random.normal(100, 15, len(dates)),
        'flow_rate': np.random.normal(50, 5, len(dates)),
        'energy_consumption': np.random.normal(1000, 100, len(dates)),
        'production_rate': np.random.normal(100, 10, len(dates))
    })
    process_data.set_index('timestamp', inplace=True)

    # Add some anomalies
    anomaly_indices = np.random.choice(len(process_data), 5, replace=False)
    process_data.iloc[anomaly_indices, 0] += 50  # Temperature spikes

    # Configure analysis
    analysis_config = {
        'enabled_analyses': [
            AnalyticsType.ANOMALY_DETECTION,
            AnalyticsType.PREDICTIVE_MAINTENANCE,
            AnalyticsType.PROCESS_OPTIMIZATION
        ],
        'anomaly_features': ['temperature', 'pressure', 'flow_rate'],
        'optimization_processes': ['main_process']
    }

    # Run analysis
    results = analytics_engine.run_comprehensive_analysis(
        process_data, {}, analysis_config
    )

    print(f"Analysis Results:")
    print(f"Confidence: {results.confidence:.2f}")
    print(f"Anomalies detected: {len(results.anomalies)}")
    print(f"Predictions made: {len(results.predictions)}")
    print(f"Recommendations: {len(results.recommendations)}")
    print(f"Alerts generated: {len(results.alerts)}")

    # Get summary
    summary = analytics_engine.get_analytics_summary()
    print(f"\nAnalytics Summary: {json.dumps(summary, indent=2)}")