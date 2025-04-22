from fastapi import FastAPI
from app.api import reports
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Store Monitoring API",
    description="API for monitoring store uptime and downtime",
    version="1.0.0"
)

# Include routers
app.include_router(reports.router, prefix="/api", tags=["reports"]) 