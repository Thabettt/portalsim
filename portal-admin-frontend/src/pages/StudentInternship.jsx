import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getStudents,
  getAllInternships,
  getInternshipProgressReports,
  submitInternshipProgressReport,
} from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import {
  Briefcase,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  FileCheck2,
  ShieldCheck,
  UserRound,
} from 'lucide-react';

import { formatISODate, formatDateTime, getStatusMeta, normalizeInternshipRecord } from '../lib/internshipUtils';
import { SectionBlock, DetailItem, StudentIdentity } from '../components/InternshipShared';

export default function StudentInternship() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [studentsList, setStudentsList] = useState([]);
  const [internshipCards, setInternshipCards] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('');

  const [reportsByInternship, setReportsByInternship] = useState({});
  const [loadingReportsByInternship, setLoadingReportsByInternship] = useState({});
  const [reportErrorsByInternship, setReportErrorsByInternship] = useState({});
  const [reportsExpandedByInternship, setReportsExpandedByInternship] = useState({});

  const [isSubmitReportExpandedByInternship, setIsSubmitReportExpandedByInternship] = useState({});
  const [submitReportDraftNumber, setSubmitReportDraftNumber] = useState({});
  const [submitReportDraftContent, setSubmitReportDraftContent] = useState({});
  const [isSubmittingReportByInternship, setIsSubmittingReportByInternship] = useState({});
  const [submitReportErrorByInternship, setSubmitReportErrorByInternship] = useState({});

  const [expandedRecordId, setExpandedRecordId] = useState('');
  const [pageError, setPageError] = useState('');

  // 1. Fetch Students and All Internships from Backend
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setPageError('');

      const [studentsRes, internshipsRes] = await Promise.all([
        getStudents(1, 200),
        getAllInternships()
      ]);

      // Populate student selector directly from database without filtering out any student
      const rawStudents = Array.isArray(studentsRes) ? studentsRes : (studentsRes.students || []);
      const formattedStudents = rawStudents
        .filter(s => s.role === 'student' || s.role === 'STUDENT' || !s.role)
        .map(s => ({
          id: s.student_id || String(s.id),
          dbId: s.id,
          name: s.full_name || s.name,
          email: s.email,
        }))
        .sort((a, b) => String(a.id).localeCompare(String(b.id)));

      setStudentsList(formattedStudents);

      // Auto-select first student if none selected
      if (formattedStudents.length > 0 && !selectedStudentId) {
        setSelectedStudentId(formattedStudents[0].id);
      }

      // Normalize internship records from backend
      const rawInternships = Array.isArray(internshipsRes) ? internshipsRes : (internshipsRes.internships || []);
      const normalizedRecords = rawInternships.map(item => normalizeInternshipRecord(item, item.status));
      setInternshipCards(normalizedRecords);

    } catch (err) {
      setPageError(err.message || 'Failed to load data from backend.');
    } finally {
      setLoading(false);
    }
  }, [selectedStudentId]);

  useEffect(() => {
    loadData();
  }, []);

  // Filter records for the selected student
  const currentStudentRecords = useMemo(() => {
    if (!selectedStudentId) return [];
    return internshipCards.filter(record => 
      String(record.studentId) === String(selectedStudentId) ||
      String(record.studentStringId) === String(selectedStudentId)
    );
  }, [internshipCards, selectedStudentId]);

  // Load progress reports for student's internships
  const loadInternshipReports = useCallback(async (internshipId) => {
    try {
      setLoadingReportsByInternship(prev => ({ ...prev, [internshipId]: true }));
      setReportErrorsByInternship(prev => ({ ...prev, [internshipId]: '' }));
      const response = await getInternshipProgressReports(internshipId);
      const reportsList = response.reports || (Array.isArray(response) ? response : []);
      setReportsByInternship(prev => ({ ...prev, [internshipId]: reportsList }));
    } catch (err) {
      setReportErrorsByInternship(prev => ({ ...prev, [internshipId]: err.message || 'Failed to load reports' }));
    } finally {
      setLoadingReportsByInternship(prev => ({ ...prev, [internshipId]: false }));
    }
  }, []);

  // When student switches or records update, auto-expand record & load reports for selected student
  useEffect(() => {
    if (currentStudentRecords.length > 0) {
      const firstRecord = currentStudentRecords[0];
      setExpandedRecordId(firstRecord.id);
      setReportsExpandedByInternship(prev => ({ ...prev, [firstRecord.id]: true }));
      currentStudentRecords.forEach(rec => {
        loadInternshipReports(rec.id);
      });
    } else {
      setExpandedRecordId('');
    }
  }, [selectedStudentId, currentStudentRecords.length]);

  const toggleSubmitReportForm = (internshipId) => {
    setIsSubmitReportExpandedByInternship(prev => {
      const isExpanded = !prev[internshipId];
      if (isExpanded) {
        setSubmitReportDraftNumber(d => ({ ...d, [internshipId]: '' }));
        setSubmitReportDraftContent(d => ({ ...d, [internshipId]: '' }));
        setSubmitReportErrorByInternship(d => ({ ...d, [internshipId]: '' }));
      }
      return { ...prev, [internshipId]: isExpanded };
    });
  };

  const handleSubmitReport = async (internshipId) => {
    const reportDraftNumber = submitReportDraftNumber[internshipId];
    const reportDraftContent = submitReportDraftContent[internshipId];

    if (!reportDraftNumber || !(reportDraftContent || '').trim()) {
      setSubmitReportErrorByInternship(prev => ({
        ...prev,
        [internshipId]: 'Please select a report number and enter report content.'
      }));
      return;
    }

    try {
      setIsSubmittingReportByInternship(prev => ({ ...prev, [internshipId]: true }));
      setSubmitReportErrorByInternship(prev => ({ ...prev, [internshipId]: '' }));

      const record = internshipCards.find(r => r.id === internshipId);
      const studentEmail = record?.studentEmail || '';
      const internshipTitle = record?.position || '';

      await submitInternshipProgressReport(internshipId, {
        student_email: studentEmail,
        internship_title: internshipTitle,
        report_number: parseInt(reportDraftNumber, 10),
        summary: reportDraftContent
      });

      addToast(`Report ${reportDraftNumber} submitted successfully`);

      // Refresh reports & internship counters
      await loadInternshipReports(internshipId);
      
      const internshipsRes = await getAllInternships();
      const rawInternships = Array.isArray(internshipsRes) ? internshipsRes : (internshipsRes.internships || []);
      setInternshipCards(rawInternships.map(item => normalizeInternshipRecord(item, item.status)));

      setIsSubmitReportExpandedByInternship(prev => ({ ...prev, [internshipId]: false }));
    } catch (err) {
      setSubmitReportErrorByInternship(prev => ({ ...prev, [internshipId]: err.message || 'Failed to submit report' }));
    } finally {
      setIsSubmittingReportByInternship(prev => ({ ...prev, [internshipId]: false }));
    }
  };

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  const selectedStudent = studentsList.find(s => s.id === selectedStudentId);

  return (
    <div className="space-y-8 animate-fade-in-up pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Student Internship</h1>
        <p className="text-muted-foreground mt-2">
          View your internship status, submit biweekly reports, and track final approvals.
        </p>
      </div>

      {/* Student Selector Dropdown */}
      <Card className="p-5 border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900/30">
        <div className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
          <div>
            <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100">Portal Simulator</h3>
            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">Select a student to view their portal perspective.</p>
          </div>
          <div className="w-full md:w-80">
            <select
              className="flex h-10 w-full rounded-md border border-blue-300 bg-white px-3 py-2 text-sm text-blue-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-blue-700 dark:bg-slate-900 dark:text-blue-100 font-medium"
              value={selectedStudentId}
              onChange={(e) => {
                setSelectedStudentId(e.target.value);
                setReportsByInternship({});
                setReportErrorsByInternship({});
              }}
            >
              <option value="" disabled>Select Student</option>
              {studentsList.map(s => (
                <option key={s.id} value={s.id}>
                  {s.id} – {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {pageError ? (
        <Card className="border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900/50">
          <CardContent className="p-4">
            <p className="text-sm font-medium text-red-700 dark:text-red-200">Unable to load internship data.</p>
            <p className="mt-1 text-sm text-red-600 dark:text-red-200/80">{pageError}</p>
          </CardContent>
        </Card>
      ) : null}

      {/* Student Internship Records Display */}
      <div className="space-y-4">
        {currentStudentRecords.length === 0 && !pageError && (
          <EmptyState
            icon={Briefcase}
            title="No internships found"
            description={`There are no internship records associated with student ${selectedStudent?.name || selectedStudentId}.`}
          />
        )}

        {currentStudentRecords.map(record => {
          const isExpanded = expandedRecordId === record.id;
          const statusMeta = getStatusMeta(record.status);
          const reports = reportsByInternship[record.id] || [];
          
          const hasLoadedReports = reportsByInternship[record.id] !== undefined;
          const waitingCount = hasLoadedReports
            ? reports.filter(r => r.status === 'pending').length
            : (record.reportSummary?.waiting_for_review || 0);
          const acceptedCount = hasLoadedReports
            ? reports.filter(r => r.status === 'approved' || r.status === 'accepted').length
            : (record.reportSummary?.accepted || 0);
          const rejectedCount = hasLoadedReports
            ? reports.filter(r => r.status === 'rejected').length
            : (record.reportSummary?.rejected || 0);
          const totalReports = hasLoadedReports
            ? reports.length
            : (record.reportSummary?.total_reports || 0);

          return (
            <Card key={record.id} className="overflow-hidden border border-border dark:border-border/60 bg-background">
              <button
                type="button"
                onClick={() => setExpandedRecordId(isExpanded ? '' : record.id)}
                className="flex w-full cursor-pointer items-center justify-between border-b border-border bg-muted/50 p-4 transition-colors hover:bg-muted text-left"
              >
                <div className="flex items-center gap-4">
                  <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${statusMeta.bgColor || 'bg-blue-100 text-blue-600'} ${statusMeta.color || ''}`}>
                    <Briefcase className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">{record.position}</h3>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <span className="font-medium text-foreground">{record.companyName}</span>
                      <span>•</span>
                      <Badge variant="secondary" className="font-normal capitalize">{statusMeta.label || record.status}</Badge>
                      <Badge variant="outline" className="font-normal">{record.location}</Badge>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="hidden text-right sm:block">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">Reports Submitted</div>
                    <div className="text-sm font-medium">{totalReports}</div>
                  </div>
                  {isExpanded ? <ChevronDown className="h-5 w-5 text-muted-foreground" /> : <ChevronRight className="h-5 w-5 text-muted-foreground" />}
                </div>
              </button>

              {isExpanded && (
                <CardContent className="space-y-6 pt-5">
                  {/* 1. Student Information */}
                  <SectionBlock
                    title="Student Information"
                    description="Identity and academic context for the internship record."
                    icon={UserRound}
                  >
                    <StudentIdentity item={record} />
                    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 mt-4">
                      <DetailItem label="Student ID" value={record.studentStringId || record.studentId} />
                      <DetailItem label="Email" value={record.studentEmail} />
                      <DetailItem label="Country" value={record.country} />
                      <DetailItem label="Faculty" value={record.faculty} />
                      <DetailItem label="First Major" value={record.firstMajor} />
                      <DetailItem label="Second Major" value={record.secondMajor || '—'} />
                    </div>
                  </SectionBlock>

                  {/* 2. Internship Information */}
                  <SectionBlock
                    title="Internship Information"
                    description="Core details about the position, location, and dates."
                    icon={Briefcase}
                  >
                    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                      <div className="space-y-3">
                        <DetailItem label="Organization" value={record.companyName} />
                        <DetailItem label="Training Position" value={record.position} />
                        <DetailItem label="Department" value={record.departments || '—'} />
                        <DetailItem label="Duration" value={`${formatISODate(record.startDate)} to ${formatISODate(record.endDate)}`} />
                        <DetailItem label="Entry Date" value={formatDateTime(record.entryDate)} />
                      </div>
                      <div className="space-y-3">
                        <DetailItem label="Source" value={record.sourceOfInternship} />
                        <DetailItem label="Workplace" value={record.workplace} />
                        <DetailItem label="Days per Week" value={record.daysPerWeek} />
                        <DetailItem label="Hours per Day" value={record.hoursPerDay} />
                        <DetailItem label="Job Description" value={record.jobDescription} />
                      </div>
                    </div>
                  </SectionBlock>

                  {/* 3. Organizational Supervisor Information */}
                  <SectionBlock
                    title="Organizational Supervisor Information"
                    description="Contact information for the on-site company supervisor."
                    icon={ShieldCheck}
                  >
                    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                      <div className="space-y-3">
                        <DetailItem label="Supervisor Name" value={record.supervisorName} />
                        <DetailItem label="Job Title" value={record.supervisorTitle} />
                      </div>
                      <div className="space-y-3">
                        <DetailItem label="Mobile" value={record.supervisorPhone} />
                        <DetailItem label="Email" value={record.supervisorEmail} />
                      </div>
                    </div>
                  </SectionBlock>

                  {/* 4. Internship Revision Status */}
                  <SectionBlock
                    title="Internship Revision Status"
                    description="Current review status from the Career Center and Academic Supervisor."
                    icon={FileCheck2}
                  >
                    <div className="space-y-4">
                      {[
                        { key: 'career_center', title: 'Career Center Status', status: record.careerCenterReviewStatus, reason: record.careerCenterReviewReason },
                        { key: 'supervisor', title: 'Academic Supervisor Status', status: record.supervisorReviewStatus, reason: record.supervisorReviewReason },
                      ].map(section => {
                        const statusLower = (section.status || '').toLowerCase();
                        const isAccepted = statusLower === 'accepted' || statusLower === 'approved';
                        const isRejected = statusLower === 'rejected';
                        const displayLabel = isAccepted ? 'Accepted' : isRejected ? 'Rejected' : (statusLower === 'waiting' ? 'Waiting' : 'Pending');

                        return (
                          <div key={section.key} className="rounded-xl border border-border bg-muted/20 p-4">
                            <div className="flex flex-col gap-2 xl:flex-row xl:items-start xl:justify-between">
                              <div>
                                <h4 className="text-sm font-semibold text-foreground">{section.title}</h4>
                                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                                  <Badge variant={isAccepted ? 'success' : isRejected ? 'danger' : 'warning'}>
                                    {displayLabel}
                                  </Badge>
                                </div>
                              </div>
                            </div>
                            <div className="mt-3">
                              <DetailItem label="Reason" value={section.reason || '(none)'} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </SectionBlock>

                  {/* 5. Uploaded Documents */}
                  <SectionBlock
                    title="Uploaded Documents"
                    description="Proof of acceptance and evaluation form upload details."
                    icon={FileCheck2}
                  >
                    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                      <div className="space-y-3">
                        <DetailItem label="Proof of Acceptance" value={record.proofOfAcceptanceUploadedAt ? 'Yes' : 'No'} />
                        <DetailItem label="Proof Upload Date" value={record.proofOfAcceptanceUploadedAt ? formatDateTime(record.proofOfAcceptanceUploadedAt) : '—'} />
                      </div>
                      <div className="space-y-3">
                        <DetailItem label="Evaluation Form" value={record.evaluationFormUploadedAt ? 'Yes' : 'No'} />
                        <DetailItem label="Evaluation Upload Date" value={record.evaluationFormUploadedAt ? formatDateTime(record.evaluationFormUploadedAt) : '—'} />
                      </div>
                    </div>
                  </SectionBlock>

                  {/* 6. Progress Report Summary & Submitted Reports */}
                  <SectionBlock
                    title="Progress Reports"
                    description="Summary counters and biweekly report details."
                    icon={ClipboardCheck}
                  >
                    {/* Counters */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl border border-border bg-muted/30">
                      <div>
                        <div className="text-xs font-medium text-muted-foreground uppercase">Total Reports</div>
                        <div className="text-2xl font-bold text-foreground mt-1">{totalReports}</div>
                      </div>
                      <div>
                        <div className="text-xs font-medium text-emerald-600 dark:text-emerald-400 uppercase">Accepted</div>
                        <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{acceptedCount}</div>
                      </div>
                      <div>
                        <div className="text-xs font-medium text-red-600 dark:text-red-400 uppercase">Rejected</div>
                        <div className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{rejectedCount}</div>
                      </div>
                      <div>
                        <div className="text-xs font-medium text-amber-600 dark:text-amber-400 uppercase">Waiting</div>
                        <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{waitingCount}</div>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center gap-3">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setReportsExpandedByInternship(current => ({ ...current, [record.id]: !current[record.id] }));
                          if (!reportsByInternship[record.id]) {
                            loadInternshipReports(record.id);
                          }
                        }}
                        isLoading={loadingReportsByInternship[record.id]}
                      >
                        {reportsExpandedByInternship[record.id] ? 'Hide Progress Reports' : 'Show Progress Reports'}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => toggleSubmitReportForm(record.id)}
                      >
                        {isSubmitReportExpandedByInternship[record.id] ? 'Cancel Report Submission' : 'Submit Progress Report'}
                      </Button>
                    </div>

                    {reportErrorsByInternship[record.id] ? (
                      <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200">
                        {reportErrorsByInternship[record.id]}
                      </div>
                    ) : null}

                    {/* Submit Report Form */}
                    {isSubmitReportExpandedByInternship[record.id] && (
                      <Card className="mt-4 border border-border bg-muted/30">
                        <div className="p-4 space-y-4">
                          <h4 className="text-sm font-semibold text-foreground">Submit Progress Report for {selectedStudent?.name || selectedStudentId}</h4>
                          {submitReportErrorByInternship[record.id] && (
                            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200">
                              {submitReportErrorByInternship[record.id]}
                            </div>
                          )}
                          <div className="space-y-4">
                            <div>
                              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Report Number *</label>
                              <select
                                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                value={submitReportDraftNumber[record.id] || ''}
                                onChange={(e) => setSubmitReportDraftNumber(prev => ({ ...prev, [record.id]: e.target.value }))}
                              >
                                <option value="" disabled>Select report number</option>
                                {[...Array(10)].map((_, i) => {
                                  const num = i + 1;
                                  const isSubmitted = reports.some(r => r.report_number === num);
                                  return (
                                    <option key={num} value={num} disabled={isSubmitted}>
                                      Report {num} {isSubmitted ? '(Already submitted)' : ''}
                                    </option>
                                  );
                                })}
                              </select>
                            </div>
                            <div>
                              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Report Content *</label>
                              <textarea
                                className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                placeholder="Enter the progress report content here..."
                                value={submitReportDraftContent[record.id] || ''}
                                onChange={(e) => setSubmitReportDraftContent(prev => ({ ...prev, [record.id]: e.target.value }))}
                              />
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => toggleSubmitReportForm(record.id)}
                                disabled={isSubmittingReportByInternship[record.id]}
                              >
                                Cancel
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                onClick={() => handleSubmitReport(record.id)}
                                isLoading={isSubmittingReportByInternship[record.id]}
                              >
                                Submit Report
                              </Button>
                            </div>
                          </div>
                        </div>
                      </Card>
                    )}

                    {/* Submitted Progress Reports List */}
                    {reportsExpandedByInternship[record.id] && (
                      reports.length === 0 ? (
                        <EmptyState
                          icon={ClipboardCheck}
                          title="No progress reports"
                          description="No biweekly progress reports have been submitted for this internship yet."
                          className="my-4"
                        />
                      ) : (
                        <div className="mt-4 space-y-3">
                          {reports.map(report => {
                            const isAccepted = report.status === 'approved' || report.status === 'accepted';
                            const isRejected = report.status === 'rejected';
                            const statusLabel = isAccepted ? 'Accepted' : isRejected ? 'Rejected' : 'Waiting';
                            const statusVariant = isAccepted ? 'success' : isRejected ? 'danger' : 'warning';

                            return (
                              <Card key={report.id || report.report_number} className="border border-border">
                                <div className="p-4 space-y-3">
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="flex items-center gap-2">
                                      <span className="font-semibold text-foreground">Report {report.report_number}</span>
                                      <Badge variant={statusVariant}>{statusLabel}</Badge>
                                    </div>
                                    {(report.created_at || report.submitted_at) && (
                                      <span className="text-xs text-muted-foreground">
                                        Submission Date: {formatISODate(report.created_at || report.submitted_at)}
                                      </span>
                                    )}
                                  </div>

                                  <div className="text-sm text-foreground whitespace-pre-wrap leading-relaxed bg-muted/20 p-3 rounded-md">
                                    {report.summary || 'No report content provided.'}
                                  </div>

                                  {(report.review_notes || report.feedback) && String(report.review_notes || report.feedback).trim().length > 0 && (
                                    <div className="border-t border-border pt-2.5 mt-2">
                                      <DetailItem label="Supervisor Feedback" value={report.review_notes || report.feedback} />
                                    </div>
                                  )}
                                </div>
                              </Card>
                            );
                          })}
                        </div>
                      )
                    )}
                  </SectionBlock>

                  {/* 7. Final Status */}
                  <SectionBlock
                    title="Final Status"
                    description="Academic and Career Center final fulfillment status."
                    icon={CheckCircle2}
                  >
                    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                      <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
                        <div className="text-xs font-medium text-muted-foreground uppercase">Academic Final Status</div>
                        <div className="flex items-center gap-2">
                          <Badge variant={record.academicFinalStatus === 'fulfilled' ? 'success' : 'warning'}>
                            {record.academicFinalStatus === 'fulfilled' ? 'Fulfilled' : record.academicFinalStatus === 'waiting' ? 'Waiting' : record.academicFinalStatus}
                          </Badge>
                        </div>
                      </div>
                      <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-2">
                        <div className="text-xs font-medium text-muted-foreground uppercase">Career Center Final Status</div>
                        <div className="flex items-center gap-2">
                          <Badge variant={record.careerCenterFinalStatus === 'fulfilled' ? 'success' : 'warning'}>
                            {record.careerCenterFinalStatus === 'fulfilled' ? 'Fulfilled' : record.careerCenterFinalStatus === 'waiting' ? 'Waiting' : record.careerCenterFinalStatus}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </SectionBlock>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
