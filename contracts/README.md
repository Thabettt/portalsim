# Webhook Contracts (v0.1)

This directory contains the versioned webhook payload contracts for the University Portal Simulator.

## Versioning

- **v0.1** (current) — Baseline contracts. Breaking changes will bump to v0.2, v1.0, etc.
- Contracts are defined as Pydantic models in `app/schemas/webhook_payloads.py`
- Example payloads in `examples.json`

## Event Types

### 1. payment_reminder

Fired when a payment is due within the reminder window (default 7 days).

```json
{
  "event_id": "uuid",
  "event_type": "payment_reminder",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "payment_id": 123,
  "payment_type": "tuition",
  "amount_due": 5000.00,
  "due_date": "2026-07-24",
  "days_overdue": 0,
  "invoice_number": "INV-STU-2024-0001-TUITION-1"
}
```

**Reminder Types**: `7_days_before`, `3_days_before`, `1_day_before`, `overdue`

### 2. internship_status_update

Fired when an admin approves or rejects an internship application.

```json
{
  "event_id": "uuid",
  "event_type": "internship_status_update",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "internship_id": 456,
  "company_name": "TechCorp Egypt",
  "position": "Software Engineering Intern",
  "previous_status": "pending",
  "new_status": "approved",
  "approved_by": "Dr. Ahmed El-Sayed",
  "approved_at": "2026-07-18T10:00:00Z",
  "rejection_reason": null
}
```

**Status Values**: `pending`, `approved`, `rejected`, `in_progress`, `completed`

### 3. attendance_alert

Fired when a student's absence count crosses a warning threshold.

```json
{
  "event_id": "uuid",
  "event_type": "attendance_alert",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "course_code": "CS-201",
  "course_name": "Data Structures and Algorithms",
  "date": "2026-07-17",
  "status": "absent",
  "warning_level": "first_warning",
  "total_absences": 3
}
```

**Warning Levels**: `first_warning` (3 absences), `second_warning` (5), `final_warning` (7)

### 4. grade_published

Fired when an admin publishes an assessment grade.

```json
{
  "event_id": "uuid",
  "event_type": "grade_published",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "assessment_id": 789,
  "assessment_title": "Midterm Exam",
  "assessment_type": "midterm",
  "course_code": "CS-201",
  "course_name": "Data Structures and Algorithms",
  "score": 85.0,
  "max_score": 100.0,
  "weight": 1.5,
  "percentage": 85.0
}
```

### 5. deadline_reminder

Fired when an assessment deadline is approaching (1, 3, or 7 days before).

```json
{
  "event_id": "uuid",
  "event_type": "deadline_reminder",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "assessment_id": 789,
  "assessment_title": "Project 2",
  "assessment_type": "project",
  "course_code": "CS-201",
  "course_name": "Data Structures and Algorithms",
  "due_date": "2026-07-25",
  "days_until_due": 3,
  "max_score": 100.0,
  "weight": 1.5
}
```

**Reminder Offsets**: `1_day_before`, `3_days_before`, `1_week_before`

### 6. attendance_marked

Fired for any attendance change (manual or automatic).

```json
{
  "event_id": "uuid",
  "event_type": "attendance_marked",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "course_code": "CS-201",
  "course_name": "Data Structures and Algorithms",
  "date": "2026-07-17",
  "status": "absent",
  "warning_level": "first_warning",
  "marked_by": "System"
}
```

### 7. payment_status_change

Fired when a payment status changes (e.g., pending → paid).

```json
{
  "event_id": "uuid",
  "event_type": "payment_status_change",
  "timestamp": "2026-07-18T10:00:00Z",
  "student_id": "STU-2024-0001",
  "student_name": "Ahmed Hassan",
  "student_email": "ahmed.hassan@student.edu.eg",
  "payment_id": 123,
  "payment_type": "tuition",
  "previous_status": "pending",
  "new_status": "paid",
  "amount_paid": 5000.00,
  "total_amount": 5000.00,
  "due_date": "2026-07-24",
  "invoice_number": "INV-STU-2024-0001-TUITION-1"
}
```

**Status Values**: `pending`, `paid`, `overdue`, `partial`, `waived`

---

## Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string (UUID) | Unique identifier for idempotency |
| `event_type` | string (enum) | Discriminator for payload type |
| `timestamp` | string (ISO8601) | When the event was generated |