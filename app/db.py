from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import inspect, text
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    if "sqlite" in settings.database_url:
        inspector = inspect(engine)
        if inspector.has_table("internship"):
            existing_columns = {column["name"] for column in inspector.get_columns("internship")}
            migrations = {
                "proof_of_acceptance_uploaded_at": "ALTER TABLE internship ADD COLUMN proof_of_acceptance_uploaded_at DATETIME",
                "evaluation_form_uploaded_at": "ALTER TABLE internship ADD COLUMN evaluation_form_uploaded_at DATETIME",
                "career_center_review_status": "ALTER TABLE internship ADD COLUMN career_center_review_status VARCHAR(20)",
                "career_center_review_reason": "ALTER TABLE internship ADD COLUMN career_center_review_reason VARCHAR(1000)",
                "supervisor_review_status": "ALTER TABLE internship ADD COLUMN supervisor_review_status VARCHAR(20)",
                "supervisor_review_reason": "ALTER TABLE internship ADD COLUMN supervisor_review_reason VARCHAR(1000)",
                "academic_final_status": "ALTER TABLE internship ADD COLUMN academic_final_status VARCHAR(20)",
                "career_center_final_status": "ALTER TABLE internship ADD COLUMN career_center_final_status VARCHAR(20)",
                "academic_supervisor_name": "ALTER TABLE internship ADD COLUMN academic_supervisor_name VARCHAR(150)",
                "academic_supervisor_id": "ALTER TABLE internship ADD COLUMN academic_supervisor_id VARCHAR(50)",
                "supervisor_job_title": "ALTER TABLE internship ADD COLUMN supervisor_job_title VARCHAR(150)",
                "supervisor_mobile": "ALTER TABLE internship ADD COLUMN supervisor_mobile VARCHAR(30)",
                "country": "ALTER TABLE internship ADD COLUMN country VARCHAR(100)",
                "faculty": "ALTER TABLE internship ADD COLUMN faculty VARCHAR(150)",
                "first_major": "ALTER TABLE internship ADD COLUMN first_major VARCHAR(150)",
                "second_major": "ALTER TABLE internship ADD COLUMN second_major VARCHAR(150)",
                "source_of_internship": "ALTER TABLE internship ADD COLUMN source_of_internship VARCHAR(100)",
                "workplace": "ALTER TABLE internship ADD COLUMN workplace VARCHAR(100)",
                "departments": "ALTER TABLE internship ADD COLUMN departments VARCHAR(500)",
                "days_per_week": "ALTER TABLE internship ADD COLUMN days_per_week INTEGER",
                "hours_per_day": "ALTER TABLE internship ADD COLUMN hours_per_day INTEGER",
                "entry_date": "ALTER TABLE internship ADD COLUMN entry_date DATETIME",
            }
            with engine.begin() as connection:
                for column_name, statement in migrations.items():
                    if column_name not in existing_columns:
                        connection.execute(text(statement))


def get_session():
    with Session(engine) as session:
        yield session
