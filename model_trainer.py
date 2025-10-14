import pandas as pd
import mysql.connector
from mysql.connector import Error
import getpass
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# --- 설정 부분 ---
DB_NAME = '''scada_db'''
DB_USER = "root"
DB_HOST = "localhost"
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

def fetch_table_data(conn, table_name):
    """테이블 전체 데이터를 Pandas DataFrame으로 가져옵니다."""
    if conn is None:
        return None
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, conn)
        print(f"Successfully fetched {len(df)} rows from '{table_name}'.")
        return df
    except Error as e:
        print(f"Error reading data from table '{table_name}': {e}")
        return None

if __name__ == "__main__":
    print("--- AI Model Trainer v2 ---") # 버전 확인용 v2 추가
    
    connection = connect_to_db(DB_USER, DB_HOST, DB_NAME)
    
    if connection:
        # 1. 데이터 로드
        water_df = fetch_table_data(connection, 'water_quality_data')
        weather_df = fetch_table_data(connection, 'weather_data')
        
        if connection.is_connected():
            connection.close()
            print("Database connection closed.")

        # 데이터 로드 실패 시 종료
        if water_df is None or weather_df is None or water_df.empty or weather_df.empty:
            print("\nFailed to load data or tables are empty. Exiting model training.")
            exit()

        # 2. 데이터 전처리 및 병합
        # timestamp 컬럼을 datetime 객체로 변환
        water_df['timestamp'] = pd.to_datetime(water_df['timestamp'])
        weather_df['forecast_time'] = pd.to_datetime(weather_df['forecast_time'])
        
        # 가장 가까운 시간의 날씨 데이터를 수질 데이터에 병합
        # tolerance를 1시간으로 설정하여 1시간 이내의 데이터만 병합
        merged_df = pd.merge_asof(water_df.sort_values('timestamp'), 
                                  weather_df.sort_values('forecast_time'), 
                                  left_on='timestamp', 
                                  right_on='forecast_time', 
                                  direction='nearest', 
                                  tolerance=pd.Timedelta('1h'))

        print(f"\nSuccessfully merged data. Resulting shape: {merged_df.shape}")

        # 3. 모델 훈련
        # 결측치가 있는 행 제거
        merged_df.dropna(inplace=True)

        if len(merged_df) < 2:
            print("Not enough data to train a model after merging and cleaning. Need at least 2 rows.")
            exit()

        # 입력(X)와 정답(y) 설정
        # 날씨 데이터와 다른 수질 데이터를 입력으로 사용
        features = ['ph_value', 'do_value', 'tds_value', 'temperature_x', 'precipitation_mm', 'humidity']
        target = 'turbidity' # 탁도를 예측 목표로 설정

        X = merged_df[features]
        y = merged_df[target]

        # 훈련 데이터와 테스트 데이터 분리
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        print(f"Training model with {len(X_train)} samples, testing with {len(X_test)} samples.")

        # 선형 회귀 모델 생성 및 훈련
        model = LinearRegression()
        model.fit(X_train, y_train)

        # 4. 모델 평가
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)

        print("\n--- Model Training Complete ---")
        print(f"Target variable: {target}")
        print(f"Input features: {features}")
        print(f"Model type: Linear Regression")
        print(f"Mean Squared Error (MSE) on test data: {mse:.4f}")
        print("-----------------------------")
        print("Note: A lower MSE means the model's predictions are closer to the actual values.")

        # 5. 모델 저장
        model_filename = 'turbidity_model.pkl'
        joblib.dump(model, model_filename)
        print(f"\nModel saved to {model_filename}")

    else:
        print("\nFailed to connect to the database. Cannot start model training.")