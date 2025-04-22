import pandas as pd
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from datetime import datetime

def load_csv_to_mysql():
    
    load_dotenv()
    
    
    db_config = {
        'host': os.getenv('MYSQL_HOST'),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': "tasd",
        'port': int(os.getenv('MYSQL_PORT'))
    }
    
    try:
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_status_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                store_id VARCHAR(36),
                timestamp_utc DATETIME NOT NULL,
                status ENUM('active', 'inactive') NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_store_id (store_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_hours (
                id INT AUTO_INCREMENT PRIMARY KEY,
                store_id VARCHAR(36),
                day_of_week INT NOT NULL,
                start_time_local TIME NOT NULL,
                end_time_local TIME NOT NULL,
                INDEX idx_store_id (store_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_timezones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                store_id VARCHAR(36) UNIQUE,
                timezone_str VARCHAR(50) NOT NULL DEFAULT 'America/Chicago',
                INDEX idx_store_id (store_id)
            )
        """)
        
        # Load data
        print("Loading store_status.csv...")
        store_status_df = pd.read_csv('dumps/store_status.csv')
        for _, row in store_status_df.iterrows():
            # Convert UTC timestamp string to datetime object
            timestamp_str = row['timestamp_utc'].replace(' UTC', '')
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
            
            cursor.execute("""
                INSERT INTO store_status_logs (store_id, timestamp_utc, status)
                VALUES (%s, %s, %s)
            """, (row['store_id'], timestamp, row['status']))
        
        
        print("Loading menu_hours.csv...")
        menu_hours_df = pd.read_csv('dumps/menu_hours.csv')
        for _, row in menu_hours_df.iterrows():
            cursor.execute("""
                INSERT INTO business_hours (store_id, day_of_week, start_time_local, end_time_local)
                VALUES (%s, %s, %s, %s)
            """, (row['store_id'], row['dayOfWeek'], row['start_time_local'], row['end_time_local']))
        
        
        print("Loading timezones.csv...")
        timezones_df = pd.read_csv('dumps/timezones.csv')
        for _, row in timezones_df.iterrows():
            cursor.execute("""
                INSERT INTO store_timezones (store_id, timezone_str)
                VALUES (%s, %s)
            """, (row['store_id'], row['timezone_str']))
        
        # Commit the transaction
        connection.commit()
        print("Data loaded successfully!")
        
    except Error as e:
        print(f"Error: {e}")
        connection.rollback()
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

if __name__ == "__main__":
    load_csv_to_mysql() 