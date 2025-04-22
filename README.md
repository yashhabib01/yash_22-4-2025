# Store Monitoring System

## Introduction

A robust store monitoring system that tracks store uptime and downtime, generating comprehensive reports based on business hours and timezone data. The system processes store status data, business hours, and timezone information to calculate uptime and downtime metrics for different time periods.

Note: The generated reports are in the reports folder

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Installation Guide](#installation-guide)
- [API Endpoints](#api-endpoints)
- [Core Logic](#core-logic)
- [Workflow](#workflow)
- [Database Structure](#database-structure)
- [Improvements](#improvements)

## Overview

- Generates reports based on business hours and timezone data
- Calculates metrics for last hour, last day, and last week
- Handles multiple timezones for accurate reporting
- Provides RESTful API endpoints for report generation and retrieval
- Stores data in MySQL database for persistence
- Uses Celery for asynchronous report generation

## Tech Stack

- **Languate**: Python
- **Backend Framework**: FastAPI
- **Task Queue**: Celery
- **Message Broker**: Redis
- **Database**: Mysql
- **ORM**: SQLAlchemy

## Installation Guide

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>

# Navigate to project directory
cd store-monitoring

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Create database
mysql -u root -p
CREATE DATABASE store_monitor;
```

### 3. Environment Configuration

Create `.env` file with:

```env
# Database Configuration
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=store_monitor

# Redis Configuration
REDIS_URL=redis://default:password@host:port
```

### 4. Initialize Database

```bash
# Create tables
python -m app.core.init_db

# Load initial data
python -m dump_csv.py
```

### 5. Run Application

```bash
# Start Celery worker
celery -A celery_app worker --loglevel=info --pool=solo

# Start FastAPI server
uvicorn app.main:app --reload
```

Access API at: http://localhost:8000/docs

## API Endpoints

### 1. Trigger Report Generation

Endpoint: POST /trigger_report
Description: Initiates the generation of a new store monitoring report.

Response:

```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. Get Report Status

Endpoint: GET /get_report/{report_id}
Description: Retrieves the status and data of a generated report.

Request:

```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response Examples:

When report is running:

```json
{
  "status": "Running"
}
```

When report is comleted:

```json
{
  "status": "Completed",
  "filepath": "reports/store_report_550e8400-e29b-41d4-a716-446655440000.csv"
}
```

When report failed:

```json
{
  "status": "Failed"
}
```

### 3. Download Report

Endpoint: GET /download_report
Description: Downloads the generated report file.

Query Parameters:

- `file_path`: The path to the report file (obtained from get_report endpoint)

Response:

- Returns the report file as a downloadable attachment

Example Usage:

```http
GET /download_report?file_path=reports/store_report_550e8400-e29b-41d4-a716-446655440000.csv
```

## Core Logic

### Uptime/Downtime Calculation

1. **Daily Log Processing**

   - Process logs day by day
   - Sort logs by timestamp for each day
   - Calculate intervals between consecutive logs
   - Add interval duration to uptime/downtime based on current log's status

2. **Edge Case Handling**

   - First log of day: Calculate interval from day's start time
   - Last log of day: Calculate interval to day's end time
   - No logs in day: Consider full day as off

3. **Time Period Aggregation**

   - Last Hour: Sum relevant intervals from current day
   - Last Day: Sum all intervals from current day
   - Last Week: Sum all intervals from last 7 days

4. **Business Hours**
   - Only consider intervals within business hours
   - Default to 24/7 if no business hours specified
   - Handle timezone conversions for accurate calculations

## Workflow

### Report Generation Process

1. **Trigger Report (FastAPI Endpoint)**

   - User makes POST request to `/trigger_report`
   - System creates a new report record in database with status "Running"
   - System generates a unique report_id
   - System sends task to Celery via Redis

2. **Celery Task Queue (Redis)**

   - Redis acts as message broker between FastAPI and Celery
   - Stores task messages in queue

3. **Celery Worker Processing**

   - Celery worker picks up task from Redis queue
   - Executes report_generation task asynchronously
   - Processes store data, business hours, and timezone information
   - Generates CSV report with uptime/downtime calculations
   - Updates report status in database

4. **Status Checking**
   - User can check report status via GET `/get_report/{report_id}`
   - System returns current status (Running/Completed/Failed)
   - When completed, includes path to generated CSV file

### Data Flow

```
[User] → [FastAPI] → [Redis] → [Celery Worker] → [Database]
↑                                                      ↓
└──────────────────[Status Check]──────────────────────┘
```

## Database Structure

### Reports Table (`reports`)

Tracks report generation status and metadata:

- `report_id`: Unique identifier for each report
- `status`: Current state of report generation (Running/Complete/Failed)
- `created_at`: When the report generation was initiated
- `completed_at`: When the report was completed (null if still running)
- `url`: Path to the generated CSV file (null if not completed)

## Improvements

### 1. Avoid Unnecessary Recomputations Using Sync Delta Check

Introduce a mechanism to track the replication delta — i.e., the range of timestamps for which new or updated records were synced.

Before triggering recalculation, check whether the delta overlaps with the time window used in the metric computation (e.g., last hour, day).

If there's no overlap, return the previously cached calculation.

This avoids unnecessary computation and improves performance, especially as the dataset grows.

### 2. AWS S3 Bucket for Report Storage

- Store generated reports in S3 bucket
- Benefits:
  - Scalable storage solution
  - Easy access to reports
  - Reduced local storage usage
  - Better file management

### 3. Store Calculated Metrics in Database

- Save uptime/downtime metrics in database
- Benefits:
  - Backup for damaged report files
  - Quick access to historical data
  - Easy data recovery
  - Reduced recalculation needs
