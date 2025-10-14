import mysql.connector
from mysql.connector import Error
import getpass
import pandas as pd

# --- 사용자가 수정해야 할 부분 ---
DB_NAME = '''scada_db'''
TABLE_NAME = '''water_quality_data'''
# --------------------------------

def connect_to_db(user, host, db_name):
    """
    데이터베이스에 안전하게 연결합니다.
    비밀번호는 실행 시점에 안전하게 입력받습니다.
    """
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

def fetch_data(conn, table_name):
    """
    데이터베이스에서 데이터를 읽어와 Pandas DataFrame으로 반환합니다.
    """
    if conn is None:
        return None
        
    try:
        # LIMIT 10을 사용하여 처음 10개의 행만 가져와서 연결을 테스트합니다.
        query = f"SELECT * FROM {table_name} LIMIT 10"
        df = pd.read_sql(query, conn)
        print(f"\n--- First 10 rows from '{table_name}' ---")
        print(df)
        print("------------------------------------")
        return df
    except Error as e:
        print(f"Error reading data from table '{table_name}': {e}")
        return None
    finally:
        if conn.is_connected():
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    # MySQL 연결 정보 (사용자, 호스트)
    DB_USER = "root"
    DB_HOST = "localhost"

    print("--- SCADA AI Project: Database Connector ---")
    
    # 데이터베이스 연결
    connection = connect_to_db(DB_USER, DB_HOST, DB_NAME)

    # 데이터 가져오기
    if connection:
        fetch_data(connection, TABLE_NAME)
    else:
        print("\nFailed to connect to the database. Please check your credentials and database status.")
        print(f"Ensure database '{DB_NAME}' and table '{TABLE_NAME}' exist.")
