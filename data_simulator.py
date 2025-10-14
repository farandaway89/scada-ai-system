import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
import getpass
from datetime import datetime, timedelta

# --- 설정 부분 ---
DB_NAME = '''scada_db'''
DB_USER = "root"
DB_HOST = "localhost"
NUM_DAYS = 365  # 1년치 데이터 생성
# --------------------------------

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

def generate_data(num_days):
    """현실적인 시계열 데이터를 생성합니다."""
    print(f"Generating {num_days} days of hourly data...")
    end_time = datetime.now()
    start_time = end_time - timedelta(days=num_days)
    
    # 시간당 데이터 포인트 생성
    timestamps = pd.date_range(start=start_time, end=end_time, freq='H')
    num_records = len(timestamps)
    df = pd.DataFrame({'timestamp': timestamps})

    # --- 날씨 데이터 생성 ---
    # 계절성 반영 (sine wave)
    seasonal_cycle = np.sin(2 * np.pi * df.index / (365 * 24))
    df['temperature'] = 15 + 10 * seasonal_cycle + np.random.randn(num_records) * 2
    df['humidity'] = 60 - 20 * seasonal_cycle + np.random.randn(num_records) * 5
    
    # 무작위 강수량 생성 (가끔 비가 옴)
    df['precipitation_mm'] = np.random.choice([0, 0.1, 0.5, 1, 2, 5], size=num_records, p=[0.9, 0.04, 0.03, 0.01, 0.01, 0.01])
    df['wind_speed'] = np.random.rand(num_records) * 5 + 2
    df['precipitation_prob'] = (df['precipitation_mm'] > 0) * np.random.randint(30, 90, size=num_records)

    # --- 수질 데이터 생성 ---
    # 날씨와 일부 상관관계 부여
    df['ph_value'] = 7.2 - df['precipitation_mm'] * 0.05 + np.random.randn(num_records) * 0.1
    df['do_value'] = 8.0 - df['temperature'] * 0.1 + np.random.randn(num_records) * 0.2
    df['turbidity'] = 1.0 + df['precipitation_mm'] * 2 + np.random.rand(num_records) * 0.5
    df['tds_value'] = 300 + df['temperature'] * 2 + np.random.randn(num_records) * 10
    df['flow_rate'] = 25 + np.random.randn(num_records) * 2
    df['pressure'] = 2.5 + np.random.randn(num_records) * 0.1
    df['chlorine_level'] = 0.5 + np.random.randn(num_records) * 0.05
    df['sensor_id'] = 'sim_sensor_01'

    # 테이블 스키마에 맞게 데이터 분리
    weather_cols = ['timestamp', 'temperature', 'precipitation_mm', 'precipitation_prob', 'humidity', 'wind_speed']
    water_cols = ['sensor_id', 'timestamp', 'ph_value', 'do_value', 'turbidity', 'tds_value', 'temperature', 'flow_rate', 'pressure', 'chlorine_level']
    
    weather_df = df[weather_cols].rename(columns={'timestamp': 'forecast_time'})
    water_quality_df = df[water_cols]

    print("Data generation complete.")
    return weather_df, water_quality_df

def insert_data_bulk(conn, df, table_name):
    """DataFrame의 데이터를 DB에 대량으로 저장합니다."""
    if df.empty:
        print(f"No data to insert into {table_name}.")
        return

    print(f"Inserting {len(df)} rows into '{table_name}'...")
    try:
        cursor = conn.cursor()
        data_tuples = [tuple(row) for row in df.to_numpy()]
        
        # SQL 쿼리 생성
        cols = ",".join(df.columns)
        placeholders = ",".join(['%s'] * len(df.columns))
        query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

        cursor.executemany(query, data_tuples)
        conn.commit()
        print(f"Successfully inserted {cursor.rowcount} rows.")

    except Error as e:
        print(f"Error during bulk insert into '{table_name}': {e}")
    finally:
        if cursor:
            cursor.close()

if __name__ == "__main__":
    print("--- Data Simulator for SCADA AI Project ---")
    
    # 1. 데이터 생성
    weather_df, water_quality_df = generate_data(NUM_DAYS)
    
    # 2. 데이터베이스 연결
    connection = connect_to_db(DB_USER, DB_HOST, DB_NAME)
    
    if connection:
        # 3. 기존 데이터 삭제 (선택적)
        try:
            print("Clearing old data from tables...")
            cursor = connection.cursor()
            cursor.execute("DELETE FROM weather_data")
            cursor.execute("DELETE FROM water_quality_data")
            connection.commit()
            cursor.close()
            print("Old data cleared.")
        except Error as e:
            print(f"Error clearing data: {e}")

        # 4. 새 데이터 삽입
        insert_data_bulk(connection, weather_df, 'weather_data')
        insert_data_bulk(connection, water_quality_df, 'water_quality_data')
        
        if connection.is_connected():
            connection.close()
            print("Database connection closed.")
    else:
        print("\nFailed to connect to the database. Cannot insert data.")
