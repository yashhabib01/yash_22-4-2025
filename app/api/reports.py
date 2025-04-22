from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta,time
import uuid
import logging
from app.core import get_db, settings
from app.models import Report,ReportStatus 
import os
from celery import shared_task
from celery_app import celery_app
from fastapi.responses import FileResponse, JSONResponse
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/trigger_report")
async def trigger_report(db: Session = Depends(get_db)):
    try:
        # Adding new Report instance in db 
        report_id = str(uuid.uuid4())
        report = Report(report_id=report_id, status=ReportStatus.running)
        db.add(report)
        db.commit()
        db.refresh(report)
        
        # Call report_generation as a Celery task with just the report_id
        celery_app.send_task('report_generation', args=[report_id])
        
        return {
            "report_id": report_id
        }
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        report.status = ReportStatus.failed
        db.commit()
        db.refresh(report)  
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/get_report/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    try:
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if report.status == ReportStatus.running:
            return {"status": "Running"}
        elif report.status == ReportStatus.completed:
            file_path = report.url
            if not file_path or not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="Report file not found")
            
            return {
                "status": "Complete",
                "file_path": file_path
            }
        elif report.status == ReportStatus.failed:
            return {"status": "Failed"}
        else:
            raise HTTPException(status_code=500, detail="Unknown error")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_report")
async def download_report(file_path: str):
    try:
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


