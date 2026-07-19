// In production, the frontend is served from the same origin as the API.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? "" : "http://localhost:8000");

async function fetchApi(endpoint, options = {}) {
  const urlObj = new URL(`${API_BASE_URL}${endpoint}`);
  urlObj.searchParams.append("_t", Date.now());
  const url = urlObj.toString();
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = "An error occurred";
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData);
    } catch (e) {
      errorMessage = await response.text();
    }
    throw new Error(errorMessage);
  }

  // Handle empty responses
  if (response.status === 204) return null;

  try {
    return await response.json();
  } catch (e) {
    return null;
  }
}

// ==== MISC ====
export async function getHealth() {
  return fetchApi("/health");
}

export async function getSystemState() {
  return fetchApi("/admin/state");
}

export async function seedData() {
  return fetchApi("/admin/seed", { method: "POST" });
}

export async function resetDatabase() {
  return fetchApi("/admin/reset", { method: "POST" });
}

// ==== SIMULATION TRIGGERS ====
export async function simulateDayEnd() {
  return fetchApi("/admin/simulate/day-end", { method: "POST" });
}

export async function simulatePaymentReminders() {
  return fetchApi("/admin/simulate/payment-reminders", { method: "POST" });
}

export async function simulateDeadlineCheck() {
  return fetchApi("/admin/simulate/deadline-check", { method: "POST" });
}

export async function getSchedulerJobs() {
  return fetchApi("/admin/scheduler/jobs");
}

export async function runSchedulerJob(jobId) {
  return fetchApi(`/admin/scheduler/jobs/${jobId}/run`, { method: "POST" });
}

// ==== ATTENDANCE ====
export async function markAttendance(payload) {
  return fetchApi("/admin/attendance/mark", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCourseAttendanceByDate(courseId, date) {
  return fetchApi(`/admin/courses/${courseId}/attendance-by-date?date=${date}`);
}

export async function batchMarkAttendance(payload) {
  return fetchApi("/admin/attendance/batch-mark", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ==== INTERNSHIPS ====
export async function getPendingInternships(page = 1, pageSize = 50) {
  return fetchApi(`/admin/internships/pending?page=${page}&page_size=${pageSize}`);
}

export async function makeInternshipDecision(internshipId, payload) {
  return fetchApi(`/admin/internships/${internshipId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ==== GRADES & DEADLINES ====
export async function publishAssessment(assessmentId, payload) {
  return fetchApi(`/admin/assessments/${assessmentId}/publish`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ==== READ ENDPOINTS ====
export async function getStudents(page = 1, pageSize = 50, role = 'student') {
  return fetchApi(`/admin/students?page=${page}&page_size=${pageSize}&role=${role}`);
}

export async function getCourses(page = 1, pageSize = 50) {
  return fetchApi(`/admin/courses?page=${page}&page_size=${pageSize}`);
}

export async function getOverduePayments(page = 1, pageSize = 50) {
  return fetchApi(`/admin/payments/overdue?page=${page}&page_size=${pageSize}`);
}

export async function getStudentSummary(studentId) {
  return fetchApi(`/admin/students/${studentId}/summary`);
}

export async function getCourseAttendance(courseCode) {
  return fetchApi(`/admin/courses/${courseCode}/attendance`);
}

// ==== WEBHOOK LOGS ====
export async function getWebhookLogs(page = 1, pageSize = 50, eventType = null) {
  const url = new URL(`${API_BASE_URL}/admin/webhook-logs`);
  url.searchParams.append("page", page);
  url.searchParams.append("page_size", pageSize);
  if (eventType) {
    url.searchParams.append("event_type", eventType);
  }
  return fetchApi(url.pathname + url.search, { method: 'GET' });
}

export async function retryWebhookLog(logId) {
  return fetchApi(`/admin/webhook-logs/${logId}/retry`, { method: "POST" });
}

export async function getWebhookLogStats() {
  return fetchApi("/admin/webhook-logs/stats");
}

// ==== SETTINGS ====
export async function getSettings() {
  return fetchApi("/admin/settings");
}

export async function updateSettings(payload) {
  return fetchApi("/admin/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
