import requests

url = "http://localhost:8001/api/grades/lookup"
headers = {"X-API-Key": "test-grades-key"}

# 1. Valid lookup
print("1. Valid:")
res = requests.get(url, headers=headers, params={"student_id": "STU-2024-0001", "course_id": "CS-101", "assessment_type": "midterm"})
print(res.status_code, res.text)

# 2. Not found combo
print("2. Not found:")
res = requests.get(url, headers=headers, params={"student_id": "STU-2024-0001", "course_id": "CS-999", "assessment_type": "midterm"})
print(res.status_code, res.text)

# 3. Invalid auth
print("3. Invalid auth:")
res = requests.get(url, headers={"X-API-Key": "wrong"}, params={"student_id": "STU-2024-0001", "course_id": "CS-101", "assessment_type": "midterm"})
print(res.status_code, res.text)

# 4. Invalid enum
print("4. Invalid enum:")
res = requests.get(url, headers=headers, params={"student_id": "STU-2024-0001", "course_id": "CS-101", "assessment_type": "invalid"})
print(res.status_code, res.text)
