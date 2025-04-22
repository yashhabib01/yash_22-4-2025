from fastapi import  HTTPException
from datetime import datetime
import logging
import pytz
from app.models import Report, StoreStatusLog, BusinessHours, StoreTimezone, ReportStatus 
from datetime import datetime
import os
from celery import shared_task
from celery_app import celery_app
from app.utils import get_uptime_downtime_for_store,get_store_logs_within_week,generate_report_for_all_stores,convert_to_local_time,is_within_business_hours
from app.core.database import SessionLocal
logger = logging.getLogger(__name__)

@celery_app.task(name='report_generation')
def report_generation(report_id: str):
    try:
      
        
        db = SessionLocal()
        
        # Get the report from the database
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if not report:
            raise Exception(f"Report with ID {report_id} not found")
            
        logger.info(f"Starting report generation for report_id: {report_id}")
        
        # Fetch all stores and their timezones
        stores = db.query(StoreTimezone).all()
        business_hours = db.query(BusinessHours).all()

        if not stores:
            raise HTTPException(status_code=404, detail="No stores found")
        if not business_hours:
            raise HTTPException(status_code=404, detail="No business hours found")

        timezone = {}
        store_data = {}
        time_range_for_dayofweek = {}
        result = []
        
        # Step 1: Initialize store_data with timezone and validate timezone
        for store in stores:
            try:
                # Validate timezone
                store_tz = pytz.timezone(store.timezone_str)
                timezone[store.store_id] = {
                    "timeZone": store.timezone_str
                }
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Invalid timezone {store.timezone_str} for store {store.store_id}")
                # Use America/Chicago as fallback
                timezone[store.store_id] = {
                    "timeZone": "America/Chicago"
                }
            
            # Initialize time_range_for_dayofweek for each store
            time_range_for_dayofweek[store.store_id] = {}
            for dayofweek in range(7):
                time_range_for_dayofweek[store.store_id][dayofweek] = {
                    "start_time": "00:00:00",
                    "end_time": "23:59:59"
                }
       
        # Step 2: Get the time range for each day of week
        for business_hour in business_hours:
            store_id = business_hour.store_id
            dayofweek = business_hour.day_of_week
            start_time = business_hour.start_time_local
            end_time = business_hour.end_time_local
            if store_id not in time_range_for_dayofweek:
                time_range_for_dayofweek[store_id] = {}
            time_range_for_dayofweek[store_id][dayofweek] = {
                "start_time": start_time,
                "end_time": end_time
            }
        
        # Step 3: Get store logs for each store
        for store in stores:
            store_id = store.store_id
            
            try:
                last_store_log = db.query(StoreStatusLog).filter(StoreStatusLog.store_id == store_id).order_by(StoreStatusLog.timestamp_utc.desc()).first()
                if not last_store_log:
                    continue
                
                last_store_log_time = last_store_log.timestamp_utc
                store_logs = get_store_logs_within_week(db, store_id, last_store_log_time)
                
                store_data[store_id] = {}
                
                for log in store_logs:
                    try:
                        # check timezone exists 
                        if store_id not in timezone:
                            timezone[store_id] = {"timeZone": "America/Chicago"}
                        
                        # Convert timestamp to local time
                        timestamp_in_local = convert_to_local_time(log["timestamp"], timezone[store_id]["timeZone"])
                        date = timestamp_in_local.strftime("%Y-%m-%d")
                        
                        # Check if timestamp is within business hours
                        if is_within_business_hours(timestamp_in_local, time_range_for_dayofweek[store_id], timezone[store_id]["timeZone"]):
                            if date not in store_data[store_id]:
                                store_data[store_id][date] = []
                                
                            store_data[store_id][date].append({
                                "timestamp": timestamp_in_local,
                                "status": log["status"],
                                "utc": log["timestamp"]
                            })
                            
                    except Exception as e:
                        logger.error(f"Error processing log for store {store_id}: {str(e)}")
                        raise e

                # Get the end time for the last log of the day
                last_log_day = last_store_log_time.weekday()
                business_hours = time_range_for_dayofweek[store_id].get(last_log_day, {
                    "end_time": "23:59:59"
                })
                last_date_str = last_store_log_time.strftime("%Y-%m-%d")
                end_time_str = f"{last_date_str} {business_hours['end_time']}"
                # Create datetime with timezone
                store_tz = pytz.timezone(timezone[store_id]["timeZone"])
                last_date = store_tz.localize(datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S"))

                result.append(get_uptime_downtime_for_store(store_data[store_id], time_range_for_dayofweek[store_id], last_date, timezone[store_id]["timeZone"] , store_id))        
            
            except Exception as e:
                logger.error(f"Error processing store {store_id}: {str(e)}")
                raise e

        
        file_url = generate_report_for_all_stores(result,report.report_id)
        if(file_url):
            report.status = ReportStatus.completed
            report.completed_at = datetime.now()
            report.url = file_url
            db.commit()
            db.refresh(report)
        else:
            report.status = ReportStatus.failed
            db.commit()
            db.refresh(report)

        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        if 'db' in locals() and 'report' in locals():
            report.status = ReportStatus.failed
            db.commit()
        raise