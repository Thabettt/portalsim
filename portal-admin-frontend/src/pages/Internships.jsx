import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getAllInternships,
  getApprovedInternships,
  getPendingInternships,
  getPendingProgressReports,
  getInternshipProgressReports,
  updateInternshipFinalStatus,
  makeInternshipDecision,
  makeProgressReportDecision,
  updateInternshipRevisionReview,
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
  Clock3,
  FileCheck2,
  Send,
  ShieldCheck,
  UserRound,
} from 'lucide-react';

const decisionButtonClasses = {
  approved: 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 border-emerald-200 dark:border-emerald-900/50',
  rejected: 'text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/50 border-red-200 dark:border-red-900/50',
};

import { formatISODate, formatDateTime, getStatusMeta, normalizeInternshipRecord, studentRecordMatchesReport, normalizeReport } from '../lib/internshipUtils';
import { SectionBlock, DetailItem, StudentIdentity } from '../components/InternshipShared';
export default function Internships() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [allInternships, setAllInternships] = useState([]);
  const [pendingInternships, setPendingInternships] = useState([]);
  const [approvedInternships, setApprovedInternships] = useState([]);
  const [pendingReports, setPendingReports] = useState([]);
  const [expandedRecordId, setExpandedRecordId] = useState('');
  const [pageError, setPageError] = useState('');

  const [activeInternshipDecision, setActiveInternshipDecision] = useState(null);
  const [internshipDecisionNotes, setInternshipDecisionNotes] = useState('');
  const [submittingInternshipDecision, setSubmittingInternshipDecision] = useState(false);

  const [reportDrafts, setReportDrafts] = useState({});
  const [submittingReportId, setSubmittingReportId] = useState(null);
  const [reportsByInternship, setReportsByInternship] = useState({});
  const [loadingReportsByInternship, setLoadingReportsByInternship] = useState({});
  const [reportErrorsByInternship, setReportErrorsByInternship] = useState({});
  const [reportsExpandedByInternship, setReportsExpandedByInternship] = useState({});
  const [reportReviewDrafts, setReportReviewDrafts] = useState({});
  const [reportReviewAction, setReportReviewAction] = useState(null);
  const [reportReviewError, setReportReviewError] = useState('');

  const [revisionReasonDrafts, setRevisionReasonDrafts] = useState({});
  const [revisionActionState, setRevisionActionState] = useState(null);
  const [revisionError, setRevisionError] = useState('');

  const [finalStatusAction, setFinalStatusAction] = useState(null);
  const [finalStatusError, setFinalStatusError] = useState('');

  const loadData = useCallback(async (background = false) => {
    try {
      setPageError('');
      if (!background) setLoading(true);
      const [allRes, internshipQueue, eligible, reportQueue] = await Promise.all([
        getAllInternships(),
        getPendingInternships(1, 50),
        getApprovedInternships(),
        getPendingProgressReports(),
      ]);

      const allItems = Array.isArray(allRes) ? allRes : (allRes?.internships || []);
      const pendingItems = Array.isArray(internshipQueue)
        ? internshipQueue
        : internshipQueue?.items || [];

      const eligibleItems = Array.isArray(eligible) ? eligible : [];
      setAllInternships(allItems);
      setPendingInternships(pendingItems);
      setApprovedInternships(eligibleItems);
      setPendingReports(Array.isArray(reportQueue) ? reportQueue : []);
      setExpandedRecordId(current => {
        const fallbackId = allItems[0]?.id ?? eligibleItems[0]?.id ?? pendingItems[0]?.id;
        if (!fallbackId) return '';
        const combined = [...allItems, ...pendingItems, ...eligibleItems];
        if (current && combined.some(item => String(item.id) === String(current))) {
          return current;
        }
        return String(fallbackId);
      });
    } catch (err) {
      setPageError(err.message);
      addToast(err.message, 'error');
    } finally {
      if (!background) setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleInternshipDecision = async (event) => {
    event.preventDefault();
    if (!activeInternshipDecision) return;

    try {
      setSubmittingInternshipDecision(true);
      await makeInternshipDecision(activeInternshipDecision.id, {
        status: activeInternshipDecision.status,
        rejection_reason: activeInternshipDecision.status === 'rejected'
          ? internshipDecisionNotes
          : null,
      });
      addToast(`Internship ${activeInternshipDecision.status} successfully`);
      
      const targetId = activeInternshipDecision.id;
      const targetStatus = activeInternshipDecision.status;
      
      setPendingInternships(current => {
        const record = current.find(r => r.id === targetId);
        if (record && targetStatus === 'approved') {
          setApprovedInternships(prev => [{...record, status: 'approved'}, ...prev]);
        }
        return current.filter(r => r.id !== targetId);
      });
      
      setActiveInternshipDecision(null);
      setInternshipDecisionNotes('');
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setSubmittingInternshipDecision(false);
    }
  };


  const loadInternshipReports = async (internshipId) => {
    try {
      setLoadingReportsByInternship(current => ({ ...current, [internshipId]: true }));
      setReportErrorsByInternship(current => ({ ...current, [internshipId]: '' }));
      const reports = await getInternshipProgressReports(internshipId);
      setReportsByInternship(current => ({ ...current, [internshipId]: Array.isArray(reports) ? reports : [] }));
    } catch (err) {
      setReportErrorsByInternship(current => ({ ...current, [internshipId]: err.message }));
      addToast(err.message, 'error');
    } finally {
      setLoadingReportsByInternship(current => ({ ...current, [internshipId]: false }));
    }
  };

  const handleReportReview = async (internshipId, report, status) => {
    const feedbackKey = `${internshipId}-${report.id}`;
    const reviewNotes = reportReviewDrafts[feedbackKey] || '';
    setReportReviewAction({ internshipId, reportId: report.id, status });
    setReportReviewError('');
    try {
      const updatedReport = await makeProgressReportDecision(report.id, {
        status: status,
        review_notes: reviewNotes,
      });

      setReportsByInternship(prev => {
        const list = prev[internshipId] || [];
        return {
          ...prev,
          [internshipId]: list.map(r => r.id === updatedReport.id ? updatedReport : r)
        };
      });
      
      const updateFn = prevRecords => prevRecords.map(record => {
        if (record.id === internshipId) {
          const currentReports = record.reports || [];
          const oldStatus = report.status;
          
          let waiting_delta = 0;
          let accepted_delta = 0;
          let rejected_delta = 0;
          
          if (oldStatus === 'pending') waiting_delta--;
          else if (oldStatus === 'approved') accepted_delta--;
          else if (oldStatus === 'rejected') rejected_delta--;
          
          if (status === 'approved') accepted_delta++;
          else if (status === 'rejected') rejected_delta++;
          else if (status === 'pending') waiting_delta++;

          return {
            ...record,
            reports: currentReports.map(r => r.id === updatedReport.id ? updatedReport : r),
            reportSummary: {
              ...(record.reportSummary || { total_reports: 0, waiting_for_review: 0, accepted: 0, rejected: 0 }),
              waiting_for_review: (record.reportSummary?.waiting_for_review || 0) + waiting_delta,
              accepted: (record.reportSummary?.accepted || 0) + accepted_delta,
              rejected: (record.reportSummary?.rejected || 0) + rejected_delta,
            }
          };
        }
        return record;
      });
      setPendingInternships(updateFn);
      setApprovedInternships(updateFn);
      setAllInternships(updateFn);

      setReportReviewDrafts(current => {
        const next = { ...current };
        delete next[feedbackKey];
        return next;
      });
    } catch (err) {
      setReportReviewError(err.message || 'An error occurred while reviewing the report.');
    } finally {
      setReportReviewAction(null);
    }
  };

  const handleRevisionDecision = async (reviewType, record, newStatus) => {
    const draftKey = `${record.id}-${reviewType}`;

    try {
      setRevisionActionState({ reviewType, recordId: record.id, status: newStatus });
      setRevisionError('');
      const response = await updateInternshipRevisionReview(reviewType, {
        student_email: record.studentEmail,
        internship_title: record.position,
        new_status: newStatus,
        reason: revisionReasonDrafts[draftKey] || null,
      });
      const updatedStatus = response?.status || newStatus;
      const updateFn = current => current.map(item => {
        if (String(item.id) !== String(record.id)) return item;
        if (reviewType === 'career_center') {
          return {
            ...item,
            careerCenterReviewStatus: updatedStatus,
            careerCenterReviewReason: revisionReasonDrafts[draftKey] || item.careerCenterReviewReason,
          };
        } else if (reviewType === 'supervisor') {
          return {
            ...item,
            supervisorReviewStatus: updatedStatus,
            supervisorReviewReason: revisionReasonDrafts[draftKey] || item.supervisorReviewReason,
          };
        }
        return item;
      });
      
      setPendingInternships(updateFn);
      setApprovedInternships(updateFn);
      setAllInternships(updateFn);
      
      setRevisionReasonDrafts(current => ({ ...current, [draftKey]: '' }));
      addToast(`Revision review ${updatedStatus} successfully`);
    } catch (err) {
      setRevisionError(err.message);
      addToast(err.message, 'error');
    } finally {
      setRevisionActionState(null);
    }
  };

  const handleFinalStatus = async (record, reviewType) => {
    try {
      setFinalStatusAction({ internshipId: record.id, reviewType });
      setFinalStatusError('');
      const updatedInternship = await updateInternshipFinalStatus(record.id, { review_type: reviewType });
      const updateFn = current => current.map(item => (
        String(item.id) === String(record.id)
          ? {
              ...item,
              academicFinalStatus: updatedInternship?.academic_final_status || item.academicFinalStatus,
              careerCenterFinalStatus: updatedInternship?.career_center_final_status || item.careerCenterFinalStatus,
            }
          : item
      ));
      setPendingInternships(updateFn);
      setApprovedInternships(updateFn);
      setAllInternships(updateFn);
      addToast('Internship marked as fulfilled');
    } catch (err) {
      setFinalStatusError(err.message);
      addToast(err.message, 'error');
    } finally {
      setFinalStatusAction(null);
    }
  };

  const internshipCards = useMemo(() => {
    const merged = new Map();

    const addRecord = (item, source) => {
      const normalized = normalizeInternshipRecord(item, source);
      const existing = merged.get(String(normalized.id));
      merged.set(String(normalized.id), {
        ...(existing || {}),
        ...normalized,
      });
    };

    allInternships.forEach(item => addRecord(item, item.status));
    pendingInternships.forEach(item => addRecord(item, 'pending'));
    approvedInternships.forEach(item => addRecord(item, 'approved'));

    const records = [...merged.values()];
    records.forEach(record => {
      const loadedReports = reportsByInternship[record.id] || [];
      const fallbackReports = pendingReports.filter(report => studentRecordMatchesReport(record, report));
      const realReports = loadedReports.length > 0 ? loadedReports : fallbackReports;
      record.reports = realReports.map((report, index) => normalizeReport(report, record, index));
    });

    return records.sort((left, right) => String(left.studentStringId || left.studentId || '').localeCompare(String(right.studentStringId || right.studentId || ''), undefined, { numeric: true, sensitivity: 'base' }));
  }, [allInternships, approvedInternships, pendingInternships, pendingReports, reportsByInternship]);

  useEffect(() => {
    internshipCards.forEach(record => {
      if (!reportsByInternship[record.id] && !loadingReportsByInternship[record.id]) {
        loadInternshipReports(record.id);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [internshipCards]);

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array(3).fill(0).map((_, index) => (
            <Card key={index}>
              <div className="p-5 space-y-3">
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-4 w-56" />
              </div>
            </Card>
          ))}
        </div>
        {Array(2).fill(0).map((_, index) => (
          <Card key={index}>
            <div className="p-5 space-y-4">
              <Skeleton className="h-7 w-72" />
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-5/6" />
            </div>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Internship Management</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Review internship records, verify documents, submit bi-weekly reports, and handle approvals.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-500/10 p-2 text-amber-600"><Clock3 className="h-5 w-5" /></div>
            <div><p className="text-2xl font-semibold">{pendingInternships.length}</p><p className="text-xs text-muted-foreground">Pending internships</p></div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-600"><CheckCircle2 className="h-5 w-5" /></div>
            <div><p className="text-2xl font-semibold">{approvedInternships.length}</p><p className="text-xs text-muted-foreground">Report-eligible internships</p></div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/10 p-2 text-blue-600"><ClipboardCheck className="h-5 w-5" /></div>
            <div><p className="text-2xl font-semibold">{pendingReports.length}</p><p className="text-xs text-muted-foreground">Reports awaiting review</p></div>
          </div>
        </Card>
      </div>

      {pageError ? (
        <Card className="border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900/50 dark:bg-red-950/30">
          <CardContent className="p-4">
            <p className="text-sm font-medium text-red-700 dark:text-red-200">Unable to load internship data.</p>
            <p className="mt-1 text-sm text-red-600 dark:text-red-200/80">{pageError}</p>
          </CardContent>
        </Card>
      ) : null}

      <div className="space-y-4">
        {internshipCards.length === 0 ? (
          <Card className="p-6">
            <EmptyState
              icon={Briefcase}
              title="No Internship Records"
              description="Internship records will appear here once the simulator loads applications."
              className="my-8"
            />
          </Card>
        ) : internshipCards.map((record, index) => {
          const isExpanded = String(expandedRecordId) === String(record.id);
          const statusMeta = getStatusMeta(record.status);
          const displayName = record.studentDisplayName || record.studentName || `Student ${record.studentId}`;
          return (
            <Card key={record.id} className="overflow-hidden">
              <button
                type="button"
                onClick={() => setExpandedRecordId(current => String(current) === String(record.id) ? '' : String(record.id))}
                className="flex w-full items-center justify-between gap-4 border-b border-border dark:border-border dark:border-border/70 bg-muted dark:bg-muted dark:bg-muted/30 px-5 py-4 text-left transition-colors hover:bg-muted dark:hover:bg-muted dark:bg-muted/50"
                aria-expanded={isExpanded}
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold text-foreground">{displayName}</h2>
                    <Badge variant={statusMeta.variant}>{statusMeta.label}</Badge>
                    <Badge variant="secondary">Record #{index + 1}</Badge>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                    <span>{record.studentStringId}</span>
                    <span className="hidden sm:inline">-</span>
                    <span>{record.companyName}</span>
                    <span className="hidden sm:inline">-</span>
                    <span>{record.position}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="hidden text-right sm:block">
                    <div className="text-xs uppercase tracking-wide text-muted-foreground">Documents</div>
                    <div className="text-sm font-medium">{record.proofOfAcceptanceUploadedAt || record.evaluationFormUploadedAt ? 2 : 0}</div>
                  </div>
                  {isExpanded ? <ChevronDown className="h-5 w-5 text-muted-foreground" /> : <ChevronRight className="h-5 w-5 text-muted-foreground" />}
                </div>
              </button>

              {isExpanded && (
                <CardContent className="space-y-4 pt-5">
                  <SectionBlock
                    title="Student Information"
                    description="Identity and academic context for the internship record."
                    icon={UserRound}
                  >
                    <div className="space-y-3">
                      <DetailItem label="Student Name" value={record.studentDisplayName || record.studentName} />
                      <DetailItem label="Student E-mail" value={record.studentEmail ? record.studentEmail.replace(/\+[^@]+/, '') : ''} />
                      <DetailItem 
                        label="Supervised By" 
                        value={record.academicSupervisorId ? `(${record.academicSupervisorId}) ${record.academicSupervisorName || record.supervisorName}` : record.academicSupervisorName || record.supervisorName} 
                      />
                      <DetailItem label="Country" value={record.country} />
                      <DetailItem label="Faculty" value={record.faculty} />
                      <DetailItem label="First Major" value={record.firstMajor} />
                      <DetailItem label="Second Major" value={record.secondMajor || 'Not available'} />
                    </div>
                  </SectionBlock>

                  <SectionBlock
                    title="Internship Information"
                    description="Placement details, schedule, and host organization."
                    icon={Briefcase}
                  >
                    <div className="space-y-3">
                      <DetailItem label="Organization" value={record.companyName} />
                      <DetailItem label="Duration" value={record.startDate && record.endDate ? `From ${formatISODate(record.startDate)} To ${formatISODate(record.endDate)}` : 'Not available'} />
                      <DetailItem label="Entry Date" value={formatDateTime(record.entryDate)} />
                      <DetailItem label="Source of Internship" value={record.sourceOfInternship} />
                      <DetailItem label="Workplace" value={record.workplace} />
                      <DetailItem label="Training" value={record.position} />
                      <DetailItem label="Department(s)" value={record.departments || 'Not available'} />
                      <DetailItem label="Days per Week" value={record.daysPerWeek} />
                      <DetailItem label="Hours per Day" value={record.hoursPerDay} />
                      <DetailItem label="Job Description" value={record.jobDescription} />
                    </div>
                  </SectionBlock>

                  <SectionBlock
                    title="Organizational Supervisor Information"
                    description="Primary contact at the host organization."
                    icon={ShieldCheck}
                  >
                    <div className="space-y-3">
                      <DetailItem label="Name" value={record.supervisorName} />
                      <DetailItem label="Job Title" value={record.supervisorTitle} />
                      <DetailItem label="Mobile" value={record.supervisorPhone} />
                      <DetailItem label="E-mail" value={record.supervisorEmail ? record.supervisorEmail.replace(/\+[^@]+/, '') : ''} />
                    </div>
                  </SectionBlock>

                  <SectionBlock
                    title="Internship Revision Status"
                    description="Revision progress and the latest review feedback."
                    icon={FileCheck2}
                  >
                    <div className="space-y-4">
                      {[
                        { key: 'career_center', title: 'Career Center Review', status: record.careerCenterReviewStatus, reason: record.careerCenterReviewReason },
                        { key: 'supervisor', title: 'Academic Supervisor Review', status: record.supervisorReviewStatus, reason: record.supervisorReviewReason },
                      ].map(section => {
                        const draftKey = `${record.id}-${section.key}`;
                        const currentValue = revisionReasonDrafts[draftKey] ?? section.reason ?? '';
                        const isBusy = revisionActionState?.recordId === record.id && revisionActionState?.reviewType === section.key;
                        const isAccepted = section.status === 'accepted';
                        const isRejected = section.status === 'rejected';

                        return (
                          <div key={section.key} className="rounded-xl border border-border dark:border-border dark:border-border/60 bg-muted dark:bg-muted dark:bg-muted/20 p-4">
                            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                              <div className="space-y-2">
                                <h4 className="text-sm font-semibold text-foreground">{section.title}</h4>
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant={isAccepted ? 'success' : isRejected ? 'danger' : 'warning'}>
                                    {isAccepted ? 'Accepted' : isRejected ? 'Rejected' : 'Pending'}
                                  </Badge>
                                  <Badge variant="secondary">Revision required</Badge>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {isAccepted
                                    ? 'This review has been accepted.'
                                    : isRejected
                                      ? 'This review has been rejected.'
                                      : 'No decision has been submitted yet.'}
                                </p>
                              </div>

                              <div className="flex flex-wrap gap-2">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className={decisionButtonClasses.approved}
                                  disabled={isBusy}
                                  isLoading={isBusy && revisionActionState?.status === 'accepted'}
                                  onClick={() => handleRevisionDecision(section.key, record, 'accepted')}
                                >
                                  Accept
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className={decisionButtonClasses.rejected}
                                  disabled={isBusy}
                                  isLoading={isBusy && revisionActionState?.status === 'rejected'}
                                  onClick={() => handleRevisionDecision(section.key, record, 'rejected')}
                                >
                                  Reject
                                </Button>
                              </div>
                            </div>

                            <div className="mt-4 space-y-3">
                              <DetailItem label="Status" value={isAccepted ? 'Accepted' : isRejected ? 'Rejected' : 'Pending'} />
                              <DetailItem label="Last Reason" value={currentValue || 'No reason recorded'} />
                            </div>

                            <div className="mt-4">
                              <label className="mb-2 block text-xs font-medium text-muted-foreground">Reason</label>
                              <textarea
                                value={revisionReasonDrafts[draftKey] ?? ''}
                                onChange={event => setRevisionReasonDrafts(current => ({ ...current, [draftKey]: event.target.value }))}
                                className="flex min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                placeholder="Enter an optional review reason for this section..."
                              />
                            </div>
                          </div>
                        );
                      })}
                      {revisionError ? (
                        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200">
                          {revisionError}
                        </div>
                      ) : null}
                    </div>
                  </SectionBlock>

                  <SectionBlock
                    title="Internship Uploaded Documents"
                    description="Proof of acceptance and evaluation form uploads from the backend."
                    icon={FileCheck2}
                  >
                    {record.proofOfAcceptanceUploadedAt || record.evaluationFormUploadedAt ? (
                      <div className="space-y-3">
                        <DetailItem
                          label="Proof of Acceptance Upload Status"
                          value={record.proofOfAcceptanceUploadedAt ? 'Yes' : 'No'}
                        />
                        <DetailItem
                          label="Proof of Acceptance Upload Date"
                          value={record.proofOfAcceptanceUploadedAt ? formatDateTime(record.proofOfAcceptanceUploadedAt) : 'Not uploaded'}
                        />
                        <DetailItem
                          label="Evaluation Form Upload Status"
                          value={record.evaluationFormUploadedAt ? 'Yes' : 'No'}
                        />
                        <DetailItem
                          label="Evaluation Form Upload Date"
                          value={record.evaluationFormUploadedAt ? formatDateTime(record.evaluationFormUploadedAt) : 'Not uploaded'}
                        />
                      </div>
                    ) : (
                      <EmptyState
                        icon={FileCheck2}
                        title="No document information exists"
                        description="The backend has not provided proof of acceptance or evaluation form upload details for this record."
                        className="my-4"
                      />
                    )}
                  </SectionBlock>

                  <SectionBlock
                    title="Internship Reports"
                    description="Submitted reports, review actions, and automation triggers."
                    icon={ClipboardCheck}
                  >
                    <div className="space-y-2">
                      <DetailItem label="Total Reports" value={record.reports?.length ?? 0} />
                      <DetailItem label="Waiting for Review" value={record.reports?.filter(report => report.status === 'pending').length ?? 0} />
                      <DetailItem label="Accepted" value={record.reports?.filter(report => report.status === 'approved').length ?? 0} />
                      <DetailItem label="Rejected" value={record.reports?.filter(report => report.status === 'rejected').length ?? 0} />
                    </div>

                    <div className="mt-4 flex items-center gap-3">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          setReportsExpandedByInternship(current => ({ ...current, [record.id]: !current[record.id] }));
                          if (!reportsByInternship[record.id]) {
                            await loadInternshipReports(record.id);
                          }
                        }}
                        isLoading={loadingReportsByInternship[record.id]}
                      >
                        {reportsExpandedByInternship[record.id] ? 'Hide Biweekly Reports' : 'Show Biweekly Reports'}
                      </Button>
                    </div>

                    {!reportsExpandedByInternship[record.id] ? (
                      <div className="mt-4 rounded-lg border border-dashed border-border dark:border-border dark:border-border/60 bg-muted dark:bg-muted dark:bg-muted/20 p-4 text-sm text-muted-foreground">
                        Click â€œShow Biweekly Reportsâ€ to view the studentâ€™s reports.
                      </div>
                    ) : (reportsByInternship[record.id] || []).length === 0 ? (
                      <EmptyState
                        icon={ClipboardCheck}
                        title="No reports found"
                        description="This internship does not have any submitted biweekly reports yet."
                        className="my-4"
                      />
                    ) : (
                      <div className="mt-4 space-y-3">
                        {(reportsByInternship[record.id] || []).map(report => {
                          const feedbackKey = `${record.id}-${report.id}`;
                          const isBusy = reportReviewAction?.reportId === report.id && reportReviewAction?.internshipId === record.id;
                          const statusLabel = report.status === 'approved' ? 'Accepted' : report.status === 'rejected' ? 'Rejected' : 'Waiting';
                          const statusVariant = report.status === 'approved' ? 'success' : report.status === 'rejected' ? 'danger' : 'warning';
                          return (
                            <Card key={report.id} className="border border-border dark:border-border dark:border-border/60">
                              <div className="p-4 space-y-4">
                                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                                  <div className="space-y-2">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <Badge variant="secondary">Report #{report.report_number}</Badge>
                                      <Badge variant={statusVariant}>{statusLabel}</Badge>
                                    </div>
                                    <div className="text-sm text-foreground whitespace-pre-wrap">{report.summary || 'No report content provided.'}</div>
                                  </div>
                                </div>
                                <div className="space-y-3">
                                  <div>
                                    <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Optional Feedback</label>
                                    <textarea
                                      value={reportReviewDrafts[feedbackKey] ?? report.review_notes ?? ''}
                                      onChange={event => setReportReviewDrafts(current => ({ ...current, [feedbackKey]: event.target.value }))}
                                      className="flex min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                      placeholder="Leave optional feedback..."
                                    />
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    <Button
                                      type="button"
                                      size="sm"
                                      className={decisionButtonClasses.approved}
                                      disabled={isBusy}
                                      isLoading={isBusy && reportReviewAction?.status === 'approved'}
                                      onClick={() => handleReportReview(record.id, report, 'approved')}
                                    >
                                      Accept
                                    </Button>
                                    <Button
                                      type="button"
                                      size="sm"
                                      className={decisionButtonClasses.rejected}
                                      disabled={isBusy}
                                      isLoading={isBusy && reportReviewAction?.status === 'rejected'}
                                      onClick={() => handleReportReview(record.id, report, 'rejected')}
                                    >
                                      Reject
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </Card>
                          );
                        })}
                      </div>
                    )}

                    {reportReviewError ? (
                      <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200">
                        {reportReviewError}
                      </div>
                    ) : null}
                  </SectionBlock>

                  <SectionBlock
                    title="Internship Final Status"
                    description="Mark academic and career center fulfillment from the backend."
                    icon={CheckCircle2}
                  >
                    <div className="space-y-4">
                      {[
                        { key: 'academic', title: 'Academic Final Status', value: record.academicFinalStatus || 'waiting' },
                        { key: 'career_center', title: 'Career Center Final Status', value: record.careerCenterFinalStatus || 'waiting' },
                      ].map(section => {
                        const isBusy = finalStatusAction?.internshipId === record.id && finalStatusAction?.reviewType === section.key;
                        const isFulfilled = section.value === 'fulfilled';
                        return (
                          <div key={section.key} className="rounded-lg border border-border dark:border-border dark:border-border/60 bg-muted dark:bg-muted dark:bg-muted/20 p-4 space-y-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant={isFulfilled ? 'success' : 'warning'}>
                                {isFulfilled ? 'Fulfilled' : 'Waiting'}
                              </Badge>
                            </div>
                            <p className="text-sm font-medium text-foreground">{section.title}</p>
                            <Button
                              type="button"
                              disabled={isBusy || isFulfilled}
                              isLoading={isBusy}
                              onClick={() => handleFinalStatus(record, section.key)}
                            >
                              Mark as Fulfilled
                            </Button>
                          </div>
                        );
                      })}
                    </div>

                    {finalStatusError ? (
                      <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-200">
                        {finalStatusError}
                      </div>
                    ) : null}
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
