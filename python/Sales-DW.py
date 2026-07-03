import os
import boto3
import requests
import pandas as pd
import pyodbc
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS credentials
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION")
S3_BUCKET_NAME = "sales-etl-project"

# SQL Server connection details
SQL_SERVER = "DESKTOP-MGMG36V"
DATABASE = "Sales_DE"

# Slack Webhook URL for notifications
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_notification(message):
    """Send a notification to Slack to track process execution."""
    try:
        payload = {"text": message}
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"❌ Slack notification error: {e}")

def download_from_s3(bucket_name, object_name, file_path):
    """Download a raw data file from AWS S3 bucket."""
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        s3_client.download_file(bucket_name, object_name, file_path)
        print(f"✅ File downloaded: {file_path}")
    except Exception as e:
        print(f"❌ Error downloading file: {e}")

def upload_to_s3(file_path, bucket_name, object_name):
    """Upload the cleaned data file to AWS S3."""
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        s3_client.upload_file(file_path, bucket_name, object_name)
        send_slack_notification(f"✅ File '{object_name}' uploaded to S3 successfully!")
        print(f"✅ File uploaded: s3://{bucket_name}/{object_name}")
    except Exception as e:
        send_slack_notification(f"❌ Upload failed: {str(e)}")
        print(f"❌ Error uploading file: {e}")

def clean_data(file_path):
    """Perform ETL (Extract, Transform, Load) process on raw data."""
    try:
        df = pd.read_csv(file_path)
        
        # Rename columns to match the Data Warehouse schema
        df.rename(columns={
            'Date': 'OrderDate',
            'Item Code': 'ProductID',
            'Item Name': 'ProductName',
            'Product Line': 'ProductLine',
            'Client Code': 'CustomerID',
            'Client Name': 'CustomerName',
            'Region': 'Region',
            'QTY': 'Quantity',
            'Sales': 'SalesAmount'
        }, inplace=True)
        
        # Drop duplicate records to ensure data consistency
        df.drop_duplicates(inplace=True)
        
        # Fill missing values with "Unknown" for categorical fields
        df.fillna("Unknown", inplace=True)
        
        # Convert OrderDate column to datetime format
        df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce')
        
        # Remove commas from numeric columns and convert them to proper data types
        df['Quantity'] = df['Quantity'].astype(str).str.replace(',', '').astype(float).astype(int)
        df['SalesAmount'] = df['SalesAmount'].astype(str).str.replace(',', '').astype(float).round(2)
        
        # Save the cleaned data file
        cleaned_file_path = "D:\\DATA\\Sales_Cleaned.csv"
        df.to_csv(cleaned_file_path, index=False)
        print(f"✅ Data cleaned and saved: {cleaned_file_path}")
        return cleaned_file_path, df
    except Exception as e:
        print(f"❌ Error cleaning data: {e}")
        return None, None

def create_tables():
    """Create necessary tables in SQL Server if they do not exist."""
    try:
        conn = pyodbc.connect(
            f'DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
        )
        cursor = conn.cursor()
        
        # Create FactSales table if it does not exist
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='FactSales' AND xtype='U')
            CREATE TABLE FactSales (
                OrderID INT IDENTITY(1,1) PRIMARY KEY,
                OrderDate DATE,
                ProductID VARCHAR(50),
                ProductName VARCHAR(100),
                ProductLine VARCHAR(100),
                CustomerID VARCHAR(50),
                CustomerName VARCHAR(100),
                Region VARCHAR(100),
                Quantity INT,
                SalesAmount DECIMAL(10,2)
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Tables verified/created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

def insert_data_into_sql(df):
    """Insert cleaned data into SQL Server FactSales table and verify the count."""
    try:
        conn = pyodbc.connect(
            f'DRIVER={{SQL Server}};SERVER={SQL_SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
        )
        cursor = conn.cursor()
        
        # Insert each row into the FactSales table
        for _, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO FactSales (OrderDate, ProductID, ProductName, ProductLine, CustomerID, CustomerName, Region, Quantity, SalesAmount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row['OrderDate'], row['ProductID'], row['ProductName'], row['ProductLine'], row['CustomerID'], row['CustomerName'], row['Region'], row['Quantity'], row['SalesAmount']
            )
        
        conn.commit()
        
        # Verify data insertion
        cursor.execute("SELECT COUNT(*) FROM FactSales")
        count = cursor.fetchone()[0]
        print(f"✅ Total records in FactSales: {count}")
        
        cursor.close()
        conn.close()
        send_slack_notification(f"✅ Data inserted into SQL Server successfully! Total records: {count}")
    except Exception as e:
        send_slack_notification(f"❌ Data insertion failed: {str(e)}")
        print(f"❌ Error inserting data: {e}")

# Run ETL process
download_from_s3(S3_BUCKET_NAME, "raw_data/Sales_Test.csv", "D:\\DATA\\Sales Test..csv")
cleaned_file, cleaned_df = clean_data("D:\\DATA\\Sales Test..csv")
if cleaned_file:
    upload_to_s3(cleaned_file, S3_BUCKET_NAME, "processed_data/Sales_Cleaned.csv")
    create_tables()
    insert_data_into_sql(cleaned_df)
