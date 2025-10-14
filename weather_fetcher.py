import requests
import mysql.connector
from mysql.connector import Error
import getpass
from datetime import datetime

# --- 설정 부분 ---
DB_NAME = '''scada_db'''
DB_USER = "root"
DB_HOST = "localhost"

# Open-Meteo API URL (서울 기준)
API_URL = "https://api.open-meteo.com/v1/forecast"
API_PARAMS = {
    "latitude": 37.5665,
    "longitude": 126.9780,
    "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"],
    "wind_speed_unit": "ms",
    "timezone": "Asia/Seoul"
}
# --------------------------------

def fetch_weather_data():
    """날씨 API를 호출하여 현재 날씨 데이터를 가져옵니다."""
    try:
        response = requests.get(API_URL, params=API_PARAMS)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킴
        data = response.json()
        print("Successfully fetched weather data from API.")
        return data['current']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def connect_to_db(user, host, db_name):
    """데이터베이스에 안전하게 연결합니다."""
    try:
        password = getpass.getpass(f"Enter password for user '{user}' on host '{host}': ")
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        if conn.is_connected():
            print(f"Successfully connected to database: {db_name}")
            return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def insert_weather_data(conn, weather_data):
    """받아온 날씨 데이터를 DB에 저장합니다."""
    if not conn or not weather_data:
        return

    try:
        cursor = conn.cursor()
        
        # API 응답 키를 DB 테이블 컬럼에 매핑
        # API: temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m
        # DB: temperature, humidity, precipitation_mm, wind_speed
        query = ("""INSERT INTO weather_data 
                 (forecast_time, temperature, precipitation_mm, precipitation_prob, humidity, wind_speed)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        )
        
        # API 응답에서 forecast_time 파싱 및 값 준비
        forecast_time = datetime.fromisoformat(weather_data['time'])
        # precipitation_prob는 API에서 직접 제공하지 않으므로 임의의 값(예: 0)으로 설정
        values = (
            forecast_time,
            weather_data.get('temperature_2m'),
            weather_data.get('precipitation'),
            0, # 강수 확률은 현재 API 응답에 없으므로 0으로 설정
            weather_data.get('relative_humidity_2m'),
            weather_data.get('wind_speed_10m')
        )
        
        cursor.execute(query, values)
        conn.commit()
        print(f"Successfully inserted 1 row of weather data for time {forecast_time.strftime('%Y-%m-%d %H:%M')}")
        
    except Error as e:
        print(f"Error inserting data into table: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    print("--- Weather Data Fetcher ---")
    
    # 1. 날씨 데이터 가져오기
    current_weather = fetch_weather_data()
    
    if current_weather:
        # 2. 데이터베이스 연결
        connection = connect_to_db(DB_USER, DB_HOST, DB_NAME)
        
        # 3. 데이터 저장
        if connection:
            insert_weather_data(connection, current_weather)
