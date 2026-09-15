export function safeDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDate(value, options = {}) {
  const parsed = safeDate(value);
  if (!parsed) return 'Not available';
  return parsed.toLocaleDateString(undefined, options);
}

export function formatDateTime(value) {
  const parsed = safeDate(value);
  if (!parsed) return 'Not available';
  return parsed.toLocaleString();
}

export function formatISODate(value) {
  const parsed = safeDate(value);
  if (!parsed) return 'Not available';
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, '0');
  const day = String(parsed.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function getStatusMeta(status) {
  switch (status) {
    case 'approved':
      return { label: 'Approved', variant: 'success' };
    case 'completed':
      return { label: 'Completed', variant: 'success' };
    case 'in_progress':
      return { label: 'In Progress', variant: 'warning' };
    case 'rejected':
      return { label: 'Rejected', variant: 'danger' };
    default:
      return { label: 'Pending Review', variant: 'secondary' };
  }
}

export function getReportStatusMeta(status) {
  switch (status) {
    case 'approved':
      return { label: 'Reviewed', variant: 'success' };
    case 'rejected':
      return { label: 'Needs Revision', variant: 'danger' };
    default:
      return { label: 'Awaiting Review', variant: 'warning' };
  }
}

export function normalizeInternshipRecord(item, source) {
  const status = String(item.status || source || 'pending').toLowerCase();
  const studentName = item.student_name || item.studentName || 'Unknown Student';
  const studentId = item.student_string_id || item.studentId || item.student_id || item.id;
  const studentDisplayName = item.student_display_name || (studentId ? `(${studentId}) ${studentName}` : studentName);

  return {
    id: item.id,
    studentDbId: item.student_db_id || item.studentDbId || null,
    studentId,
    studentName,
    studentEmail: item.student_email || item.studentEmail || '',
    studentStringId: item.student_string_id || item.studentStringId || item.student_id || '',
    studentDisplayName,
    companyName: item.organization || item.company_name || 'Not available',
    position: item.training || item.position || 'Not available',
    startDate: item.duration_from || item.start_date || null,
    endDate: item.duration_to || item.end_date || null,
    status,
    academicSupervisorName: item.academic_supervisor_name || item.academicSupervisorName || 'Not provided',
    academicSupervisorId: item.academic_supervisor_id || item.academicSupervisorId || '',
    supervisorName: item.supervisor_name || item.organizational_supervisor_name || 'Not provided',
    supervisorEmail: item.supervisor_email || item.organizational_supervisor_email || '',
    supervisorPhone: item.supervisor_mobile || item.organizational_supervisor_mobile || '',
    supervisorTitle: item.supervisor_job_title || item.organizational_supervisor_job_title || '',
    location: item.country || item.location || 'Not provided',
    programName: item.faculty || item.programName || 'Not provided',
    academicYear: item.first_major || item.academicYear || 'Not provided',
    revisionStatus: item.revision_status || 'pending',
    careerCenterReviewStatus: item.career_center_review_status || 'pending',
    careerCenterReviewReason: item.career_center_review_reason || '',
    supervisorReviewStatus: item.supervisor_review_status || 'pending',
    supervisorReviewReason: item.supervisor_review_reason || '',
    proofOfAcceptanceUploadedAt: item.proof_of_acceptance_uploaded_at || item.proof_of_acceptance_upload_date || null,
    evaluationFormUploadedAt: item.evaluation_form_uploaded_at || item.evaluation_form_upload_date || null,
    academicFinalStatus: item.academic_final_status || 'waiting',
    careerCenterFinalStatus: item.career_center_final_status || 'waiting',
    next_progress_report_number: item.next_progress_report_number || 1,
    approvedAt: item.approved_at || null,
    rejectionReason: item.rejection_reason || '',
    reports: [],
    canSubmitReport: ['approved', 'in_progress', 'completed'].includes(status),
    finalStatus: status,
    sourceOfInternship: item.source_of_internship || 'Not provided',
    workplace: item.workplace || 'Not provided',
    departments: item.departments || '',
    daysPerWeek: item.days_per_week ?? 'Not provided',
    hoursPerDay: item.hours_per_day ?? 'Not provided',
    jobDescription: item.job_description || item.description || 'Not provided',
    entryDate: item.entry_date || item.created_at || null,
    country: item.country || 'Not provided',
    faculty: item.faculty || 'Not provided',
    firstMajor: item.first_major || 'Not provided',
    secondMajor: item.second_major || '',
    reportSummary: item.report_summary || { total_reports: 0, waiting_for_review: 0, accepted: 0, rejected: 0 },
  };
}

export function studentRecordMatchesReport(record, report) {
  if (report.internship_id != null && String(report.internship_id) === String(record.id)) return true;
  if (report.student_db_id != null && record.studentDbId != null && String(report.student_db_id) === String(record.studentDbId)) return true;
  if (report.student_id != null && record.studentDbId != null && String(report.student_id) === String(record.studentDbId)) return true;
  return false;
}

export function normalizeReport(report, record, index) {
  const status = report.status || 'pending';
  return {
    ...report,
    id: report.id ?? `report-${record.id}-${report.report_number ?? index + 1}`,
    report_number: report.report_number ?? Number(record.next_progress_report_number || 1) + index,
    summary: report.summary || 'No summary provided.',
    submitted_at: report.submitted_at || report.created_at || null,
    status,
    statusMeta: getReportStatusMeta(status),
  };
}
