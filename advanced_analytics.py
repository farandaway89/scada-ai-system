"""
Advanced Analytics and Reporting Engine
고급 데이터 분석 및 리포팅 엔진
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
import mysql.connector
from mysql.connector import Error
import logging
import redis
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

class AnalysisType(Enum):
    TREND_ANALYSIS = "trend_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    CORRELATION_ANALYSIS = "correlation_analysis"
    PERFORMANCE_METRICS = "performance_metrics"
    PREDICTIVE_ANALYSIS = "predictive_analysis"
    CLUSTERING_ANALYSIS = "clustering_analysis"

class ReportFormat(Enum):
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"

@dataclass
class AnalysisResult:
    analysis_type: str
    timestamp: str
    results: Dict[str, Any]
    visualizations: List[str]
    summary: str
    recommendations: List[str]

class DataProcessor:
    """데이터 전처리 및 준비"""

    @staticmethod
    def get_db_connection():
        """데이터베이스 연결"""
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="1234",
                database="scada_db"
            )
            return conn
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return None

    @staticmethod
    def fetch_time_series_data(hours_back: int = 168) -> pd.DataFrame:
        """시계열 데이터 가져오기 (기본 7일)"""
        conn = DataProcessor.get_db_connection()
        if not conn:
            return pd.DataFrame()

        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)

            # 수질 데이터 조회
            water_query = """
            SELECT timestamp, ph_value, do_value, turbidity, tds_value, temperature
            FROM water_quality_data
            WHERE timestamp >= %s
            ORDER BY timestamp
            """

            # 날씨 데이터 조회
            weather_query = """
            SELECT forecast_time as timestamp, precipitation_mm, humidity, temperature_forecast
            FROM weather_data
            WHERE forecast_time >= %s
            ORDER BY forecast_time
            """

            water_df = pd.read_sql(water_query, conn, params=[cutoff_time])
            weather_df = pd.read_sql(weather_query, conn, params=[cutoff_time])

            # 타임스탬프를 datetime으로 변환
            water_df['timestamp'] = pd.to_datetime(water_df['timestamp'])
            weather_df['timestamp'] = pd.to_datetime(weather_df['timestamp'])

            # 가장 가까운 시간으로 병합
            merged_df = pd.merge_asof(
                water_df.sort_values('timestamp'),
                weather_df.sort_values('timestamp'),
                on='timestamp',
                direction='nearest',
                tolerance=pd.Timedelta('1h')
            )

            return merged_df.dropna()

        except Exception as e:
            logger.error(f"Data fetch error: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    @staticmethod
    def clean_and_preprocess(df: pd.DataFrame) -> pd.DataFrame:
        """데이터 정리 및 전처리"""
        if df.empty:
            return df

        # 이상치 제거 (IQR 방법)
        numeric_columns = df.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            if col != 'timestamp':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

        # 결측치 처리 (선형 보간)
        df = df.interpolate(method='linear')

        return df

class TrendAnalyzer:
    """트렌드 분석기"""

    @staticmethod
    def analyze_trends(df: pd.DataFrame, parameter: str) -> Dict[str, Any]:
        """매개변수별 트렌드 분석"""
        if df.empty or parameter not in df.columns:
            return {}

        data = df[parameter].dropna()
        if len(data) < 10:
            return {}

        # 기본 통계
        stats_summary = {
            'mean': float(data.mean()),
            'std': float(data.std()),
            'min': float(data.min()),
            'max': float(data.max()),
            'median': float(data.median())
        }

        # 트렌드 계산 (선형 회귀)
        x = np.arange(len(data))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, data)

        trend_info = {
            'slope': float(slope),
            'r_squared': float(r_value ** 2),
            'p_value': float(p_value),
            'trend_direction': 'increasing' if slope > 0.01 else 'decreasing' if slope < -0.01 else 'stable'
        }

        # 변동성 분석
        volatility = {
            'coefficient_of_variation': float(data.std() / data.mean()) if data.mean() != 0 else 0,
            'rolling_std_7day': float(data.rolling(window=min(168, len(data)//2)).std().mean()) if len(data) > 168 else 0
        }

        # 계절성 분석 (단순한 방법)
        if len(data) >= 24:  # 최소 24시간 데이터
            hourly_means = []
            for hour in range(24):
                hour_data = data.iloc[hour::24]
                if len(hour_data) > 0:
                    hourly_means.append(hour_data.mean())
                else:
                    hourly_means.append(np.nan)

            seasonality = {
                'hourly_pattern': [float(x) if not np.isnan(x) else None for x in hourly_means],
                'peak_hour': int(np.nanargmax(hourly_means)) if not all(np.isnan(hourly_means)) else None,
                'min_hour': int(np.nanargmin(hourly_means)) if not all(np.isnan(hourly_means)) else None
            }
        else:
            seasonality = {'hourly_pattern': [], 'peak_hour': None, 'min_hour': None}

        return {
            'parameter': parameter,
            'statistics': stats_summary,
            'trend': trend_info,
            'volatility': volatility,
            'seasonality': seasonality,
            'data_points': len(data),
            'analysis_period': f"{df['timestamp'].min()} to {df['timestamp'].max()}"
        }

class AnomalyDetector:
    """이상 탐지기"""

    @staticmethod
    def detect_anomalies(df: pd.DataFrame, contamination: float = 0.1) -> Dict[str, Any]:
        """다변량 이상 탐지"""
        if df.empty:
            return {}

        # 수치형 컬럼만 선택
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if 'timestamp' in numeric_cols:
            numeric_cols.remove('timestamp')

        if len(numeric_cols) == 0:
            return {}

        data = df[numeric_cols].dropna()
        if len(data) < 10:
            return {}

        # 데이터 정규화
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        # Isolation Forest로 이상 탐지
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        anomaly_labels = iso_forest.fit_predict(scaled_data)

        # 이상치 인덱스
        anomaly_indices = np.where(anomaly_labels == -1)[0]

        # 이상치 세부 정보
        anomalies = []
        for idx in anomaly_indices:
            anomaly_info = {
                'timestamp': df.iloc[idx]['timestamp'].isoformat() if 'timestamp' in df.columns else str(idx),
                'index': int(idx),
                'values': {col: float(df.iloc[idx][col]) for col in numeric_cols},
                'anomaly_score': float(iso_forest.decision_function(scaled_data[idx:idx+1])[0])
            }
            anomalies.append(anomaly_info)

        # 매개변수별 이상치 통계
        parameter_stats = {}
        for col in numeric_cols:
            col_anomalies = [a['values'][col] for a in anomalies]
            if col_anomalies:
                parameter_stats[col] = {
                    'anomaly_count': len(col_anomalies),
                    'anomaly_rate': len(col_anomalies) / len(data),
                    'min_anomaly': min(col_anomalies),
                    'max_anomaly': max(col_anomalies),
                    'normal_range': {
                        'min': float(data[col][anomaly_labels == 1].min()),
                        'max': float(data[col][anomaly_labels == 1].max()),
                        'mean': float(data[col][anomaly_labels == 1].mean())
                    }
                }

        return {
            'total_anomalies': len(anomaly_indices),
            'anomaly_rate': len(anomaly_indices) / len(data),
            'anomalies': anomalies[:20],  # 최대 20개만 반환
            'parameter_statistics': parameter_stats,
            'detection_method': 'Isolation Forest',
            'contamination_rate': contamination
        }

class CorrelationAnalyzer:
    """상관관계 분석기"""

    @staticmethod
    def analyze_correlations(df: pd.DataFrame) -> Dict[str, Any]:
        """매개변수 간 상관관계 분석"""
        if df.empty:
            return {}

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if 'timestamp' in numeric_cols:
            numeric_cols.remove('timestamp')

        if len(numeric_cols) < 2:
            return {}

        data = df[numeric_cols].dropna()

        # 피어슨 상관계수 계산
        correlation_matrix = data.corr()

        # 강한 상관관계 찾기 (|r| > 0.7)
        strong_correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    strong_correlations.append({
                        'parameter1': correlation_matrix.columns[i],
                        'parameter2': correlation_matrix.columns[j],
                        'correlation': float(corr_value),
                        'strength': 'very_strong' if abs(corr_value) > 0.9 else 'strong'
                    })

        # 상관관계 매트릭스를 딕셔너리로 변환
        corr_dict = {}
        for col1 in correlation_matrix.columns:
            corr_dict[col1] = {}
            for col2 in correlation_matrix.columns:
                corr_dict[col1][col2] = float(correlation_matrix.loc[col1, col2])

        return {
            'correlation_matrix': corr_dict,
            'strong_correlations': strong_correlations,
            'parameter_count': len(numeric_cols),
            'analysis_method': 'Pearson correlation'
        }

class PerformanceAnalyzer:
    """성능 분석기"""

    @staticmethod
    def analyze_system_performance(df: pd.DataFrame) -> Dict[str, Any]:
        """시스템 성능 분석"""
        if df.empty:
            return {}

        # 수질 기준 정의 (예시)
        quality_standards = {
            'ph_value': {'min': 6.5, 'max': 8.5, 'optimal': 7.0},
            'do_value': {'min': 4.0, 'max': float('inf'), 'optimal': 6.0},
            'turbidity': {'min': 0, 'max': 1.0, 'optimal': 0.1},
            'tds_value': {'min': 0, 'max': 500, 'optimal': 150}
        }

        performance_metrics = {}

        for param, standards in quality_standards.items():
            if param in df.columns:
                data = df[param].dropna()
                if len(data) > 0:
                    # 기준 준수율 계산
                    within_range = data[(data >= standards['min']) & (data <= standards['max'])]
                    compliance_rate = len(within_range) / len(data)

                    # 최적값과의 편차
                    optimal_deviation = abs(data - standards['optimal']).mean()

                    # 안정성 (변동 계수)
                    stability = 1 - (data.std() / data.mean()) if data.mean() != 0 else 0
                    stability = max(0, min(1, stability))  # 0-1 범위로 제한

                    performance_metrics[param] = {
                        'compliance_rate': float(compliance_rate),
                        'optimal_deviation': float(optimal_deviation),
                        'stability_score': float(stability),
                        'current_value': float(data.iloc[-1]),
                        'trend_last_24h': 'improving' if len(data) > 24 and data.iloc[-24:].mean() > data.iloc[-48:-24].mean() else 'stable',
                        'standards': standards
                    }

        # 전체 시스템 성능 점수
        if performance_metrics:
            overall_compliance = np.mean([m['compliance_rate'] for m in performance_metrics.values()])
            overall_stability = np.mean([m['stability_score'] for m in performance_metrics.values()])
            overall_score = (overall_compliance * 0.7 + overall_stability * 0.3)

            performance_grade = 'A' if overall_score > 0.9 else 'B' if overall_score > 0.8 else 'C' if overall_score > 0.7 else 'D'
        else:
            overall_score = 0
            performance_grade = 'N/A'

        return {
            'parameter_performance': performance_metrics,
            'overall_score': float(overall_score),
            'performance_grade': performance_grade,
            'analysis_period': f"{df['timestamp'].min()} to {df['timestamp'].max()}" if 'timestamp' in df.columns else 'N/A'
        }

class ClusteringAnalyzer:
    """클러스터링 분석기"""

    @staticmethod
    def perform_clustering(df: pd.DataFrame, n_clusters: int = 3) -> Dict[str, Any]:
        """운영 상태 클러스터링 분석"""
        if df.empty:
            return {}

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if 'timestamp' in numeric_cols:
            numeric_cols.remove('timestamp')

        if len(numeric_cols) < 2:
            return {}

        data = df[numeric_cols].dropna()
        if len(data) < n_clusters:
            return {}

        # 데이터 정규화
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        # K-means 클러스터링
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(scaled_data)

        # 클러스터별 특성 분석
        cluster_analysis = {}
        for i in range(n_clusters):
            cluster_data = data[cluster_labels == i]
            cluster_analysis[f'cluster_{i}'] = {
                'size': len(cluster_data),
                'percentage': len(cluster_data) / len(data) * 100,
                'characteristics': {
                    col: {
                        'mean': float(cluster_data[col].mean()),
                        'std': float(cluster_data[col].std()),
                        'min': float(cluster_data[col].min()),
                        'max': float(cluster_data[col].max())
                    } for col in numeric_cols
                }
            }

        # PCA로 차원 축소 (시각화용)
        if len(numeric_cols) > 2:
            pca = PCA(n_components=2)
            pca_data = pca.fit_transform(scaled_data)
            explained_variance = pca.explained_variance_ratio_
        else:
            pca_data = scaled_data
            explained_variance = [1.0, 0.0]

        return {
            'n_clusters': n_clusters,
            'cluster_analysis': cluster_analysis,
            'cluster_labels': cluster_labels.tolist(),
            'pca_variance_explained': explained_variance.tolist(),
            'cluster_centers': kmeans.cluster_centers_.tolist()
        }

class ReportGenerator:
    """리포트 생성기"""

    @staticmethod
    def generate_comprehensive_report(hours_back: int = 168) -> AnalysisResult:
        """종합 분석 리포트 생성"""
        # 데이터 로드 및 전처리
        df = DataProcessor.fetch_time_series_data(hours_back)
        df = DataProcessor.clean_and_preprocess(df)

        if df.empty:
            return AnalysisResult(
                analysis_type="comprehensive",
                timestamp=datetime.now().isoformat(),
                results={"error": "No data available"},
                visualizations=[],
                summary="데이터가 없어 분석을 수행할 수 없습니다.",
                recommendations=["데이터 수집 시스템을 확인하세요."]
            )

        # 각종 분석 수행
        results = {}

        # 1. 트렌드 분석
        trend_results = {}
        for param in ['ph_value', 'do_value', 'turbidity', 'tds_value']:
            if param in df.columns:
                trend_results[param] = TrendAnalyzer.analyze_trends(df, param)
        results['trend_analysis'] = trend_results

        # 2. 이상 탐지
        results['anomaly_detection'] = AnomalyDetector.detect_anomalies(df)

        # 3. 상관관계 분석
        results['correlation_analysis'] = CorrelationAnalyzer.analyze_correlations(df)

        # 4. 성능 분석
        results['performance_analysis'] = PerformanceAnalyzer.analyze_system_performance(df)

        # 5. 클러스터링 분석
        results['clustering_analysis'] = ClusteringAnalyzer.perform_clustering(df)

        # 요약 및 권고사항 생성
        summary = ReportGenerator._generate_summary(results)
        recommendations = ReportGenerator._generate_recommendations(results)

        # 결과를 Redis에 캐시
        cache_key = f"analysis_report_{hours_back}h_{datetime.now().strftime('%Y%m%d_%H')}"
        redis_client.setex(cache_key, 3600, json.dumps(results))  # 1시간 캐시

        return AnalysisResult(
            analysis_type="comprehensive",
            timestamp=datetime.now().isoformat(),
            results=results,
            visualizations=[],  # 실제로는 차트 생성 코드 추가
            summary=summary,
            recommendations=recommendations
        )

    @staticmethod
    def _generate_summary(results: Dict[str, Any]) -> str:
        """분석 결과 요약 생성"""
        summary_parts = []

        # 성능 분석 요약
        if 'performance_analysis' in results:
            perf = results['performance_analysis']
            grade = perf.get('performance_grade', 'N/A')
            score = perf.get('overall_score', 0)
            summary_parts.append(f"전체 시스템 성능: {grade} 등급 (점수: {score:.1%})")

        # 이상 탐지 요약
        if 'anomaly_detection' in results:
            anomaly = results['anomaly_detection']
            count = anomaly.get('total_anomalies', 0)
            rate = anomaly.get('anomaly_rate', 0)
            summary_parts.append(f"이상 데이터: {count}건 (전체의 {rate:.1%})")

        # 트렌드 요약
        if 'trend_analysis' in results:
            trends = results['trend_analysis']
            increasing = sum(1 for t in trends.values()
                           if t.get('trend', {}).get('trend_direction') == 'increasing')
            decreasing = sum(1 for t in trends.values()
                           if t.get('trend', {}).get('trend_direction') == 'decreasing')
            summary_parts.append(f"매개변수 트렌드: 증가 {increasing}개, 감소 {decreasing}개")

        return " | ".join(summary_parts) if summary_parts else "분석 데이터가 부족합니다."

    @staticmethod
    def _generate_recommendations(results: Dict[str, Any]) -> List[str]:
        """권고사항 생성"""
        recommendations = []

        # 성능 기반 권고
        if 'performance_analysis' in results:
            perf = results['performance_analysis']
            overall_score = perf.get('overall_score', 0)

            if overall_score < 0.7:
                recommendations.append("시스템 성능이 기준 이하입니다. 즉시 점검이 필요합니다.")
            elif overall_score < 0.9:
                recommendations.append("시스템 성능 개선을 위한 예방적 유지보수를 권장합니다.")

            # 매개변수별 권고
            for param, metrics in perf.get('parameter_performance', {}).items():
                compliance_rate = metrics.get('compliance_rate', 0)
                if compliance_rate < 0.8:
                    recommendations.append(f"{param} 매개변수의 기준 준수율이 낮습니다. 제어 시스템을 점검하세요.")

        # 이상 탐지 기반 권고
        if 'anomaly_detection' in results:
            anomaly = results['anomaly_detection']
            anomaly_rate = anomaly.get('anomaly_rate', 0)

            if anomaly_rate > 0.1:  # 10% 이상
                recommendations.append("이상 데이터 발생률이 높습니다. 센서 캘리브레이션을 확인하세요.")

        # 상관관계 기반 권고
        if 'correlation_analysis' in results:
            corr = results['correlation_analysis']
            strong_corr = corr.get('strong_correlations', [])

            if len(strong_corr) > 0:
                recommendations.append("강한 상관관계가 있는 매개변수들을 통합 모니터링하여 효율성을 높이세요.")

        return recommendations if recommendations else ["현재 시스템이 안정적으로 운영되고 있습니다."]

# 메인 분석 함수
def run_comprehensive_analysis(hours_back: int = 168) -> Dict[str, Any]:
    """종합 분석 실행"""
    try:
        report = ReportGenerator.generate_comprehensive_report(hours_back)
        return {
            "success": True,
            "analysis_result": {
                "analysis_type": report.analysis_type,
                "timestamp": report.timestamp,
                "results": report.results,
                "summary": report.summary,
                "recommendations": report.recommendations
            }
        }
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # 테스트 실행
    result = run_comprehensive_analysis()
    print(json.dumps(result, indent=2, ensure_ascii=False))