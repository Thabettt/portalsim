# University Portal Simulator

A mock backend simulating a university portal for ERPNext integration testing. This service provides realistic, stateful data and fires webhooks on state changes — perfect for developing and demoing an ERPNext-based university system without needing real APIs.

## Features

- **Stateful Simulation**: SQLite database with students, courses, enrollments, attendance, payments, grades, internships
- **Webhook Events**: 7 event types with HMAC-SHA256 signed payloads
- **Automated Scheduling**: Daily jobs for attendance, payment reminders, deadline checks
- **Admin Control Panel**: REST endpoints for manual triggering and inspection
- **Demo Data**: Seed script creates a full semester of realistic historical data
- **Zero External Deps**: Runs entirely self-contained (SQLite, in-process scheduler)

---

## Quick Start

```bash
# 1. Clone and navigate
cd university-portal-sim

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (optional)
cp .env.example .env
# Edit .env to set WEBHOOK_TARGET_URL if you have a receiver

# 5. Seed database
python seed.py

# 6. Run server
uvicorn app.main:app --reload

# 7. Open Swagger UI
# http://localhost:8000/docs
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_TARGET_URL` | *(empty)* | URL to POST webhooks to. Leave empty to log locally only. |
| `SHARED_SECRET` | `dev-secret-change-in-production` | HMAC secret for webhook signatures |
| `DATABASE_URL` | `sqlite:///./university_portal.db` | SQLite file path |
| `SCHEDULER_TIMEZONE` | `UTC` | Timezone for scheduled jobs |
| `WEBHOOK_MAX_RETRIES` | `3` | Max delivery attempts |
| `WEBHOOK_RETRY_DELAYS` | `5,30,120` | Seconds between retries |

---

## API Endpoints

All admin endpoints under `/admin` (no auth — local demo only).

### System State

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/seed` | Wipe DB and reseed demo data |
| `POST` | `/admin/reset` | Wipe DB to empty |
| `GET` | `/admin/state` | Summary counts of all entities |

### Simulations (Manual Triggers)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/simulate/day-end` | Run daily attendance simulation |
| `POST` | `/admin/simulate/payment-reminders` | Check and fire payment reminders |
| `POST` | `/admin/simulate/deadline-check` | Check and fire deadline reminders |

### Manual State Changes

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/admin/attendance/mark` | `{student_id, course_id, date, status, notes?}` | Mark attendance |
| `POST` | `/admin/internships/{id}/decision` | `{status, rejection_reason?}` | Approve/reject internship |
| `POST` | `/admin/assessments/{id}/publish` | `{score}` | Publish a grade |

### Inspection

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/webhook-logs` | Paginated webhook delivery logs |
| `GET` | `/admin/webhook-logs/stats` | Delivery success/failure stats |
| `GET` | `/admin/settings` | View webhook config |
| `PUT` | `/admin/settings` | Update webhook URL/secret |
| `GET` | `/admin/scheduler/jobs` | List scheduled jobs |
| `POST` | `/admin/scheduler/jobs/{id}/run` | Run a job immediately |

### Data Browsing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/students` | List students |
| `GET` | `/admin/courses` | List courses |
| `GET` | `/admin/payments/overdue` | Overdue payments |
| `GET` | `/admin/internships/pending` | Pending internships |
| `GET` | `/admin/students/{id}/summary` | Full student profile |

---

## Webhook Contracts

See [`contracts/README.md`](contracts/README.md) for full payload schemas and examples.

### Event Types

| Event | Trigger | Key Fields |
|-------|---------|------------|
| `payment_reminder` | Daily / manual | `amount_due`, `due_date`, `reminder_type` |
| `internship_status_update` | Admin decision | `new_status`, `approved_by`, `rejection_reason` |
| `attendance_alert` | Absence threshold crossed | `warning_level`, `total_absences` |
| `grade_published` | Admin publishes grade | `score`, `max_score`, `percentage` |
| `deadline_reminder` | Daily / manual | `days_until_due`, `reminder_offset` |
| `attendance_marked` | Any attendance change | `status`, `marked_by` |
| `payment_status_change` | Payment updated | `previous_status`, `new_status` |

### Headers

```
Content-Type: application/json
X-University-Signature: <HMAC-SHA256>
X-University-Event: payment_reminder
X-University-Event-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Retry Policy

- 3 attempts: 5s → 30s → 120s
- All attempts logged to `/admin/webhook-logs`
- No crash on delivery failure (background task)

---

## Demo Data (After Seeding)

- **15 students** (STU-2024-0001 … STU-2024-0015)
- **5 instructors**
- **10 courses** (CS, MA, PH, EN)
- **~60 enrollments** (4-6 courses per student)
- **8 weeks** of attendance (Mon-Fri, ~85% present)
- **4 payment types** × 2-3 installments each
- **3-5 assessments** per enrollment (some published)
- **~30% students** with 1-3 internship applications

Attendance warnings already triggered for some students (check `/admin/webhook-logs` for `attendance_alert` events).

---

## Scheduler Jobs

| Job | Schedule | Manual Trigger |
|-----|----------|----------------|
| Daily Attendance | 23:00 UTC | `POST /admin/simulate/day-end` |
| Payment Reminders | 09:00 UTC | `POST /admin/simulate/payment-reminders` |
| Deadline Check | 10:00 UTC | `POST /admin/simulate/deadline-check` |

---

## Project Structure

```
university-portal-sim/
├── app/
│   ├── main.py              # FastAPI app, lifespan, routers
│   ├── config.py            # Pydantic settings
│   ├── db.py                # SQLAlchemy engine/session
│   ├── models.py            # SQLModel ORM models
│   ├── schemas/
│   │   ├── __init__.py      # Request/response models
│   │   └── webhook_payloads.py  # Versioned webhook contracts
│   ├── routers/
│   │   └── admin.py         # All /admin endpoints
│   ├── services/
│   │   ├── webhook_sender.py   # HMAC, retry, logging
│   │   ├── attendance.py       # Attendance logic + alerts
│   │   ├── payments.py         # Payment reminders
│   │   └── grades_internships.py # Grades, deadlines, internships
│   └── scheduler.py         # APScheduler jobs
├── seed.py                  # Demo data generator
├── contracts/
│   ├── README.md            # Webhook schema docs
│   └── examples.json        # Example payloads
├── requirements.txt
├── .env.example
└── README.md
```

---

## Acceptance Checklist

- [ ] `python seed.py` → server runs → `/docs` shows all endpoints
- [ ] `POST /admin/attendance/mark` 3× same course → `attendance_alert` webhook with `first_warning`
- [ ] `POST /admin/simulate/payment-reminders` → only payments due within 7 days fire
- [ ] `POST /admin/internships/{id}/decision` → exactly one `internship_status_update`
- [ ] Kill webhook receiver → fire event → 3 retries logged in `/admin/webhook-logs`
- [ ] `/admin/state` and `/admin/webhook-logs` show enough info to narrate demo
- [ ] No hardcoded webhook URL/secret in code — all from `/admin/settings` or `.env`

---

## Security Notice

**This is a local development/demo tool.** The `/admin/*` endpoints have **no authentication** by design. Do not expose to the internet. For production use, add proper auth (OAuth2, API keys, mTLS).

---

## License

MIT — Use freely for integration testing and demos.