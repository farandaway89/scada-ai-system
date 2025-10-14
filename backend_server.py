import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import pandas as pd
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import numpy as np

# --- 설정 부분 ---
DB_NAME = '''scada_db'''
DB_USER = "root"
DB_HOST = "localhost"
# 경고: 이 방식은 데모용이며, 실제 제품에서는 절대 사용하면 안 됩니다!
DB_PASSWORD = "1234"

MODEL_PATH = "turbidity_model.pkl"
# --------------------------------

# FastAPI 앱 생성
app = FastAPI()

# CORS 미들웨어 추가 (모든 출처 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI 모델 로드
try:
    model = joblib.load(MODEL_PATH)
    print(f"Model '{MODEL_PATH}' loaded successfully.")
except FileNotFoundError:
    print(f"Error: Model file not found at '{MODEL_PATH}'. Please run model_trainer.py first.")
    model = None

def get_db_connection():
    """데이터베이스 연결을 생성합니다."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def generate_future_predictions(current_features, model, num_steps=10, interval_hours=1):
    """
    현재 특성값을 기반으로 미래 예측값을 시뮬레이션하여 생성합니다.
    (간단한 선형 변화 및 노이즈 추가)
    """
    future_predictions = []
    current_data = current_features.iloc[0].copy() # 현재 데이터 복사

    for i in range(num_steps):
        # 시간 경과에 따른 특성값 변화 시뮬레이션 (간단한 선형 변화 + 노이즈)
        # 실제로는 더 복잡한 시계열 모델이나 외부 요인 예측이 필요
        current_data['ph_value'] += (0.01 * (i+1)) + (0.01 * (0.5 - np.random.rand()))
        current_data['do_value'] -= (0.02 * (i+1)) + (0.01 * (0.5 - np.random.rand()))
        current_data['tds_value'] += (0.5 * (i+1)) + (0.5 * (0.5 - np.random.rand()))
        current_data['temperature_x'] += (0.1 * (i+1)) + (0.1 * (0.5 - np.random.rand()))
        # 강수량과 습도는 미래 예측이 어려우므로 현재 값 유지 또는 간단한 변화
        # current_data['precipitation_mm'] = current_data['precipitation_mm'] # 유지
        # current_data['humidity'] = current_data['humidity'] # 유지

        # 예측을 위한 DataFrame 생성
        future_features = pd.DataFrame([current_data[feature] for feature in current_features.columns]).T
        future_features.columns = current_features.columns # 컬럼명 유지

        # 예측 수행
        prediction = model.predict(future_features)
        future_predictions.append(round(prediction[0], 2))
    
    return future_predictions

@app.get("/predict")
async def predict():
    """최신 데이터를 기반으로 예측을 수행하고 결과를 반환합니다."""
    if model is None:
        return {"error": "Model not loaded."}

    conn = get_db_connection()
    if conn is None:
        return {"error": "Database connection failed."}

    try:
        # 가장 최신의 수질 및 날씨 데이터 1개씩 가져오기
        water_query = "SELECT * FROM water_quality_data ORDER BY timestamp DESC LIMIT 1"
        weather_query = "SELECT * FROM weather_data ORDER BY forecast_time DESC LIMIT 1"
        
        water_df = pd.read_sql(water_query, conn)
        weather_df = pd.read_sql(weather_query, conn)

        if water_df.empty or weather_df.empty:
            return {"error": "Not enough data in tables."}

        # 모델 훈련 시 사용했던 특성(features)과 동일한 순서로 데이터 준비
        features_for_prediction = pd.DataFrame({
            'ph_value': [water_df.iloc[0]['ph_value']],
            'do_value': [water_df.iloc[0]['do_value']],
            'tds_value': [water_df.iloc[0]['tds_value']],
            'temperature_x': [water_df.iloc[0]['temperature']],
            'precipitation_mm': [weather_df.iloc[0]['precipitation_mm']],
            'humidity': [weather_df.iloc[0]['humidity']]
        })

        # AI 모델로 현재 예측 수행
        prediction = model.predict(features_for_prediction)
        predicted_turbidity = prediction[0]

        # 미래 예측 생성
        future_turbidity_predictions = generate_future_predictions(features_for_prediction, model, num_steps=10, interval_hours=1)

        # UI에 보낼 최종 결과 구성
        result = {
            "actual_ph": water_df.iloc[0]['ph_value'],
            "actual_do": water_df.iloc[0]['do_value'],
            "actual_turbidity": water_df.iloc[0]['turbidity'],
            "actual_tds": water_df.iloc[0]['tds_value'],
            "predicted_turbidity": round(predicted_turbidity, 2),
            "future_turbidity_predictions": future_turbidity_predictions # Add future predictions
        }
        return result

    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.get("/")
def read_root():
    return {"message": "Water Quality AI Prediction Server is running."}

if __name__ == "__main__":
    print("Starting backend server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)