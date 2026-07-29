import requests
from sqlmodel import Session, create_engine, select
from app.models import User, Course, Assessment, AssessmentType

# 1. Setup unpublished grade in the DB
engine = create_engine("sqlite:///./university_portal.db")
with Session(engine) as session:
    user = session.exec(select(User).where(User.student_id == "STU-2024-0001")).first()
    course = session.exec(select(Course).where(Course.code == "CS-101")).first()
    
    if user and course:
        user_id = user.id
        course_id = course.id
        # check if unpublished grade exists, if not create one
        a = session.exec(select(Assessment).where(
            Assessment.student_id == user_id,
            Assessment.course_id == course_id,
            Assessment.assessment_type == AssessmentType.FINAL
        )).first()
        
        if not a:
            a = Assessment(
                student_id=user.id,
                course_id=course.id,
                assessment_type=AssessmentType.FINAL,
                title="Final Exam",
                max_score=100.0,
                is_published=False
            )
            session.add(a)
            session.commit()
            print("Created unpublished Final exam.")
        else:
            a.is_published = False
            session.add(a)
            session.commit()
            print("Set existing Final exam to unpublished.")

# 2. Test the API for this unpublished grade
url = "http://localhost:8001/api/grades/lookup"
headers = {"X-API-Key": "test-grades-key"}

print("\n--- Test 1: Querying Unpublished Grade ---")
res = requests.get(url, headers=headers, params={"student_id": "STU-2024-0001", "course_id": "CS-101", "assessment_type": "final"})
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text}")

print("\n--- Test 2: Publishing the Grade ---")
# Normally the UI calls POST /admin/assessments/{id}/publish but I will just do it in DB for testing
# Wait, I should publish it in DB and query again to confirm.
with Session(engine) as session:
    user = session.exec(select(User).where(User.student_id == "STU-2024-0001")).first()
    course = session.exec(select(Course).where(Course.code == "CS-101")).first()
    a = session.exec(select(Assessment).where(
        Assessment.student_id == user.id,
        Assessment.course_id == course.id,
        Assessment.assessment_type == AssessmentType.FINAL
    )).first()
    a.is_published = True
    a.score = 95.0
    session.add(a)
    session.commit()

print("\n--- Test 3: Querying Published Grade ---")
res = requests.get(url, headers=headers, params={"student_id": "STU-2024-0001", "course_id": "CS-101", "assessment_type": "final"})
print(f"Status Code: {res.status_code}")
print(f"Response: {res.text}")
