# scheduler_microservice.py
#
# This single file contains a complete, production-ready scheduler microservice.
# In a real-world project, these components would be split into separate files/directories
# for better organization (e.g., `main.py`, `api/`, `crud/`, `models/`, `core/`).
#
# To run this application:
# 1. Install the necessary libraries:
#    pip install "fastapi[all]" "sqlmodel" "apscheduler" "psycopg2-binary" # Use psycopg2 for postgres
#    # For SQLite (as used in this example), no extra driver is needed.
#
# 2. Run the server:
#    uvicorn scheduler_microservice:app --reload
#
# 3. Access the interactive API documentation (Swagger UI) at:
#    http://127.0.0.1:8000/docs

import os
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import validator
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy import Column, JSON # <-- IMPORTED JSON TYPE
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from contextlib import asynccontextmanager

# --- Configuration ---
# In a real app, this would be loaded from environment variables or a config file.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./scheduler.db")
# For PostgreSQL, the URL would look like:
# DATABASE_URL = "postgresql://user:password@host:port/database"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. DATABASE MODELS (models/job.py)
#    Defines the data structure for a Job in the database using SQLModel.
# ==============================================================================

class JobBase(SQLModel):
    """Base model for a Job, containing shared fields."""
    name: str = Field(index=True, description="A human-readable name for the job.")
    job_type: str = Field(description="The type of the job to be executed (e.g., 'email_notification').")
    cron_string: str = Field(description="A cron-style string for scheduling (e.g., '0 9 * * MON').")
    # --- FIX APPLIED HERE ---
    # We explicitly tell SQLAlchemy to use the JSON column type for this field.
    job_params: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON), description="A JSON object of parameters for the job."
    )

    @validator('cron_string')
    def validate_cron_string(cls, v):
        """Validates that the cron_string is a valid cron expression."""
        try:
            CronTrigger.from_crontab(v)
        except ValueError as e:
            raise ValueError(f"Invalid cron string format: {e}")
        return v

class Job(JobBase, table=True):
    """Database model for a Job, representing the 'jobs' table."""
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True, description="Whether the job is currently scheduled to run.")
    last_run_at: Optional[datetime] = Field(default=None, description="Timestamp of the last time the job was run.")
    next_run_at: Optional[datetime] = Field(default=None, description="Timestamp of the next scheduled run.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class JobCreate(JobBase):
    """Schema for creating a new job via the API."""
    pass

class JobRead(JobBase):
    """Schema for reading a job's details from the API."""
    id: int
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime

# ==============================================================================
# 2. DATABASE SESSION MANAGEMENT (db/session.py)
# ==============================================================================

# The `connect_args` is for SQLite only. It's not needed for other databases.
connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def create_db_and_tables():
    """Creates the database and tables if they don't exist."""
    logger.info("Creating database and tables...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database and tables created successfully.")

def get_session():
    """FastAPI dependency to get a database session for a request."""
    with Session(engine) as session:
        yield session

# ==============================================================================
# 3. DUMMY JOB SERVICES (services/job_executors.py)
#    This section defines the actual logic that the scheduler will execute.
#    It's designed to be extensible (Open/Closed Principle).
# ==============================================================================

def send_email_notification(to: str, subject: str, body: str):
    """Dummy job to simulate sending an email."""
    logger.info(f"--- JOB EXECUTING: Sending Email ---")
    logger.info(f"To: {to}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Body: {body}")
    logger.info(f"--- JOB COMPLETE ---")

def perform_number_crunching(numbers: List[float]):
    """Dummy job to simulate a data processing task."""
    logger.info(f"--- JOB EXECUTING: Number Crunching ---")
    logger.info(f"Processing {len(numbers)} numbers...")
    result = sum(numbers)
    logger.info(f"Result of crunching: {result}")
    logger.info(f"--- JOB COMPLETE ---")

# A registry to map job_type strings to actual callable functions.
# This makes the system extensible. To add a new job type, just add it here.
JOB_EXECUTOR_REGISTRY: Dict[str, Callable] = {
    "email_notification": send_email_notification,
    "number_crunching": perform_number_crunching,
}

# ==============================================================================
# 4. CRUD OPERATIONS (crud/crud_job.py)
#    Functions for Create, Read, Update, Delete operations on the Job model.
# ==============================================================================

def create_job(session: Session, job_in: JobCreate) -> Job:
    """Creates a new job record in the database."""
    if job_in.job_type not in JOB_EXECUTOR_REGISTRY:
        raise ValueError(f"Invalid job_type: '{job_in.job_type}'. Must be one of {list(JOB_EXECUTOR_REGISTRY.keys())}")
        
    db_job = Job.from_orm(job_in)
    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job

def get_job_by_id(session: Session, job_id: int) -> Optional[Job]:
    """Retrieves a single job by its ID."""
    return session.get(Job, job_id)

def get_all_jobs(session: Session) -> List[Job]:
    """Retrieves all jobs from the database."""
    return session.exec(select(Job)).all()

def update_job_run_times(session: Session, job_id: int, last_run: datetime, next_run: datetime) -> Optional[Job]:
    """Updates the last and next run timestamps for a job."""
    db_job = get_job_by_id(session, job_id)
    if db_job:
        db_job.last_run_at = last_run
        db_job.next_run_at = next_run
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
    return db_job

# ==============================================================================
# 5. SCHEDULER LOGIC (core/scheduler.py)
#    Manages the APScheduler instance, including scheduling and executing jobs.
# ==============================================================================

class JobScheduler:
    def __init__(self):
        # For production scalability with multiple workers, use a persistent job store
        # like SQLAlchemyJobStore and a proper database. This ensures that only one
        # scheduler instance runs a given job at the scheduled time.
        jobstores = {
            'default': SQLAlchemyJobStore(url=DATABASE_URL)
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

    def _execute_and_update_job(self, job_id: int):
        """
        A wrapper function that is actually scheduled. It executes the job
        and updates its timestamps in the database.
        """
        with Session(engine) as session:
            db_job = get_job_by_id(session, job_id)
            if not db_job or not db_job.is_active:
                logger.warning(f"Job {job_id} not found or is inactive. Skipping execution.")
                return

            executor = JOB_EXECUTOR_REGISTRY.get(db_job.job_type)
            if not executor:
                logger.error(f"No executor found for job type '{db_job.job_type}' (Job ID: {job_id}).")
                return

            logger.info(f"Executing job {db_job.id}: '{db_job.name}'")
            try:
                # Execute the actual job logic with its parameters
                executor(**db_job.job_params)
                
                # Update run times in the database
                aps_job = self.scheduler.get_job(str(job_id))
                next_run = aps_job.next_run_time if aps_job else None
                update_job_run_times(session, job_id, datetime.now(timezone.utc), next_run)
                logger.info(f"Successfully executed and updated job {db_job.id}.")

            except Exception as e:
                logger.error(f"Error executing job {db_job.id}: {e}", exc_info=True)

    def add_job_to_scheduler(self, db_job: Job):
        """Adds a single job from the database to the APScheduler instance."""
        if not db_job.is_active:
            return
        
        try:
            self.scheduler.add_job(
                self._execute_and_update_job,
                trigger=CronTrigger.from_crontab(db_job.cron_string, timezone="UTC"),
                id=str(db_job.id),
                name=db_job.name,
                replace_existing=True,
                args=[db_job.id]
            )
            # Update the next_run_at time after scheduling
            with Session(engine) as session:
                aps_job = self.scheduler.get_job(str(db_job.id))
                if aps_job:
                    db_job.next_run_at = aps_job.next_run_time
                    session.add(db_job)
                    session.commit()
            
            logger.info(f"Scheduled job {db_job.id}: '{db_job.name}' with cron '{db_job.cron_string}'.")
        except Exception as e:
            logger.error(f"Failed to schedule job {db_job.id}: {e}", exc_info=True)

    def load_and_schedule_all_jobs(self):
        """Loads all active jobs from the database and schedules them."""
        logger.info("Loading and scheduling all jobs from the database...")
        with Session(engine) as session:
            all_db_jobs = get_all_jobs(session)
            for db_job in all_db_jobs:
                self.add_job_to_scheduler(db_job)
        logger.info("All jobs loaded.")

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

# Global scheduler instance
job_scheduler = JobScheduler()

# ==============================================================================
# 6. FASTAPI APPLICATION SETUP (main.py)
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("Application startup...")
    create_db_and_tables()
    job_scheduler.load_and_schedule_all_jobs()
    job_scheduler.start()
    yield
    logger.info("Application shutdown...")
    job_scheduler.shutdown()

app = FastAPI(
    title="Scheduler Microservice",
    description="A microservice to schedule and manage custom jobs via a REST API.",
    version="1.0.0",
    lifespan=lifespan
)

# --- API Endpoints (api/v1/endpoints/jobs.py) ---

@app.post("/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED, tags=["Jobs"])
def api_create_job(job_in: JobCreate, session: Session = Depends(get_session)):
    """
    Create a new job and add it to the scheduler.

    - **name**: A descriptive name for the job.
    - **job_type**: The type of job to run. Available types: `email_notification`, `number_crunching`.
    - **cron_string**: A standard cron expression (e.g., `* * * * *` for every minute, `0 9 * * MON` for 9 AM every Monday).
    - **job_params**: A JSON object with parameters required by the `job_type`.
      - For `email_notification`: `{"to": "...", "subject": "...", "body": "..."}`
      - For `number_crunching`: `{"numbers": [1, 2, 3]}`
    """
    try:
        db_job = create_job(session, job_in)
        job_scheduler.add_job_to_scheduler(db_job)
        return db_job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create job.")

@app.get("/jobs", response_model=List[JobRead], tags=["Jobs"])
def api_list_jobs(session: Session = Depends(get_session)):
    """
    Retrieve a list of all jobs in the system.
    """
    return get_all_jobs(session)

@app.get("/jobs/{job_id}", response_model=JobRead, tags=["Jobs"])
def api_get_job_details(job_id: int, session: Session = Depends(get_session)):
    """
    Retrieve detailed information for a specific job by its ID.
    """
    db_job = get_job_by_id(session, job_id)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return db_job

@app.get("/", tags=["Health Check"])
def health_check():
    """
    A simple health check endpoint to confirm the service is running.
    """
    return {"status": "ok", "timestamp": datetime.now(timezone.utc)}

