from sqlalchemy.orm import Session
from datetime import datetime, timedelta,time
import logging
import pytz
from app.models import StoreStatusLog, StoreStatus
from typing import List, Dict
import csv
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def get_uptime_downtime_for_store(store_data: Dict, time_range_for_dayofweek: Dict, last_date: datetime, store_timezone: str,store_id:str) -> Dict:
    try:
        
        uptime_last_hour = downtime_last_hour = 0
        uptime_last_day = downtime_last_day = 0
        uptime_last_week = downtime_last_week = 0

        
        store_tz = pytz.timezone(store_timezone)
        
        # convert last_date to store timezone
        last_date = last_date.astimezone(store_tz)
        
        # calculate time windows in store timezone
        hour_start_time = last_date - timedelta(hours=1)
       
        # for each days logs
        for day_str, logs in store_data.items():
           
            if not logs:
                continue

            # sort logs 
            sorted_logs = sorted(logs, key=lambda x: x["timestamp"])
            
            is_last_day = last_date.strftime("%Y-%m-%d") == day_str
            
            day_of_week = datetime.strptime(day_str, "%Y-%m-%d").weekday()
            
            # Getting business hours for this day
            business_hours = time_range_for_dayofweek.get(day_of_week, {
                "start_time": "00:00:00",
                "end_time": "23:59:59"
            })

            # Handle first interval 
            if sorted_logs:
                
                first_log_time = sorted_logs[0]["timestamp"]
                start_time_str = f"{day_str} {business_hours['start_time']}"
                
                # Create start of day in store timezone
                start_of_day = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                start_of_day = store_tz.localize(start_of_day)
                
                first_interval = (first_log_time - start_of_day).total_seconds() / 60
                if first_interval > 0:  # Only if there's a gap between start and first log
                    # Add to week 
                    if sorted_logs[0]["status"] == StoreStatus.active:
                        uptime_last_week += first_interval  
                    else:
                        downtime_last_week += first_interval
                    
                    # Add to day 
                    if is_last_day:
                        if sorted_logs[0]["status"] == StoreStatus.active:
                            uptime_last_day += first_interval
                        else:
                            downtime_last_day += first_interval
                    
                    # Check for last hour overlap
                    overlap_start = max(start_of_day, hour_start_time)
                    overlap_end = min(first_log_time, last_date)
                    if overlap_end > overlap_start:
                        overlap_duration = (overlap_end - overlap_start).total_seconds() / 60
                        if sorted_logs[0]["status"] == StoreStatus.active:
                            uptime_last_hour += overlap_duration
                        else:
                            downtime_last_hour += overlap_duration
                

            # Process each log 
            for i in range(len(sorted_logs)):
                
                current_log = sorted_logs[i]
                current_time = current_log["timestamp"]
                # Determine next time
                if i + 1 < len(sorted_logs):
                    next_time = sorted_logs[i + 1]["timestamp"]
                else:
                    # If last log of the day, use end of business hours
                    end_time_str = f"{day_str} {business_hours['end_time']}"
                    # Create end of day in store's timezone
                    end_of_day = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                    end_of_day = store_tz.localize(end_of_day)
                    next_time = end_of_day
                
                # interval in minutes
                interval = (next_time - current_time).total_seconds() / 60
                
                # Add to week totals 
                if current_log["status"] == StoreStatus.active:
                    uptime_last_week += interval
                else:
                    downtime_last_week += interval
                
                # Add to day totals if  last day
                if is_last_day:
                    if current_log["status"] == StoreStatus.active:
                        uptime_last_day += interval
                    else:
                        downtime_last_day += interval
                
                # Checking for last hour overlap
                overlap_start = max(current_time, hour_start_time)
                overlap_end = min(next_time, last_date)
                
                if overlap_end > overlap_start:
                    overlap_duration = (overlap_end - overlap_start).total_seconds() / 60    
                    if current_log["status"] == StoreStatus.active:
                        uptime_last_hour += overlap_duration
                    else:
                        downtime_last_hour += overlap_duration
                    
            

        return {
            "store_id":store_id,
            "uptime_last_hour": int(uptime_last_hour),
            "downtime_last_hour": int(downtime_last_hour),
            "uptime_last_day": round(uptime_last_day/60),
            "downtime_last_day": round(downtime_last_day/60),
            "uptime_last_week": round(uptime_last_week/60),
            "downtime_last_week": round(downtime_last_week/60),
        }
    except Exception as e:
        logger.error(f"Error in get_uptime_downtime_for_store: {str(e)}")
        raise e

def generate_report_for_all_stores(result,report_id:str):
    try:
        # Create reports directory if it no  exist
        os.makedirs("reports", exist_ok=True)

        # report_id as  filename 

        filename = f"reports/store_report_{report_id}.csv"

        
        headers = [
            "store_id",
            "uptime_last_hour(minutes)",
            "uptime_last_day(hours)",
            "uptime_last_week(hours)",
            "downtime_last_hour(minutes)",
            "downtime_last_day(hours)",
            "downtime_last_week(hours)"
        ]

       
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for store_result in result:
                writer.writerow([
                    store_result.get("store_id", "N/A"),
                    store_result.get("uptime_last_hour", 0),
                    store_result.get("uptime_last_day", 0),
                    store_result.get("uptime_last_week", 0),
                    store_result.get("downtime_last_hour", 0),
                    store_result.get("downtime_last_day", 0),
                    store_result.get("downtime_last_week", 0)
                ])

        print(f"Report generated successfully: {filename}")
        return filename
    except Exception as e:
        print(f"Error generating report: {e}")
        raise e



def convert_to_local_time(timestamp_str: str, timezone_str: str) -> datetime:
    try:
       
        utc = pytz.utc
        utc_dt = utc.localize(datetime.fromisoformat(timestamp_str))

      
        local_tz = pytz.timezone(timezone_str)
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt

    except pytz.UnknownTimeZoneError as timezone_error:
        logger.warning(f"Invalid timezone: {timezone_str}, defaulting to UTC")
        raise timezone_error
    except Exception as e:
        logger.error(f"Error converting time: {str(e)}")
        raise e

def is_within_business_hours(timestamp: datetime, business_hours: Dict, store_timezone: str) -> bool:
    try:
       
        store_tz = pytz.timezone(store_timezone)
        
      
        local_time = timestamp.astimezone(store_tz)
        
      
        day_of_week = local_time.weekday()
        hours = business_hours.get(day_of_week, {
            "start_time": "00:00:00",
            "end_time": "23:59:59"
        })
        
      
        start_time_str = f"{local_time.strftime('%Y-%m-%d')} {hours['start_time']}"
        end_time_str = f"{local_time.strftime('%Y-%m-%d')} {hours['end_time']}"
        
        start_of_day = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_of_day = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        
        start_of_day = store_tz.localize(start_of_day)
        end_of_day = store_tz.localize(end_of_day)
        
        return start_of_day <= local_time <= end_of_day
        
    except Exception as e:
        logger.error(f"Error checking business hours: {str(e)}")
        raise e

def get_store_logs_within_week(db: Session, store_id: str, last_store_log_time: datetime) -> List[Dict]:
   
    try:
        # Calculate the start of the week (7 days ago from last_store_log_time)
        week_start = last_store_log_time.replace(hour=23, minute=59, second=59) - timedelta(days=6)
            
        logs = db.query(StoreStatusLog).filter(
            StoreStatusLog.store_id == store_id,
            StoreStatusLog.timestamp_utc >= week_start,
        ).order_by(StoreStatusLog.timestamp_utc).all()
        
        return [{
            "timestamp": log.timestamp_utc.isoformat(),
            "status": log.status
        } for log in logs]
    except Exception as e:
        logger.error(f"Error getting store logs within week: {str(e)}")
        raise e
        