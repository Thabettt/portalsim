# Simulated University Portal Admin Frontend

This is the frontend control panel for the Simulated University Portal backend. It's a React Single Page Application (SPA) built with Vite and Tailwind CSS. It is designed to act as an operator/presenter tool for live demos.

## Running Locally

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

## Configuration

The application expects the FastAPI backend to be running on `http://localhost:8000` by default.
To point it at a different backend URL, create or edit the `.env` file in this directory and set the `VITE_API_BASE_URL` variable:
```env
VITE_API_BASE_URL=https://your-custom-backend-url.com
```

## Features and Pages

- **Dashboard**: System overview, webhook delivery health, scheduled jobs, and simulation triggers (Seed Data, Day-End, Reminders).
- **Attendance**: Manual attendance marking form and a viewer for course attendance rosters.
- **Payments**: Actionable queue of overdue payments for at-risk students.
- **Internships**: Actionable queue of pending internship applications with inline approve/reject functionality.
- **Grades & Deadlines**: Assessment publishing controls and deadline check triggers.
- **Webhook Log**: Auto-refreshing log of all webhook deliveries with payload inspection and retry functionality.
- **Settings**: Configuration for the target webhook URL and shared secret.

## Note on Authentication
This is an internal demo tool built to drive a presentation. It intentionally has no authentication or login screen, matching the backend's lack of auth on the `/admin/*` routes.
