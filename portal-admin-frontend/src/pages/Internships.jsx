import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getApprovedInternships,
  getPendingInternships,
  getPendingProgressReports,
  makeInternshipDecision,
  makeProgressReportDecision,
  submitInternshipProgressReport,
} from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { Select } from '../components/ui/Select';
import { EmptyState } from '../components/ui/EmptyState';
import {
  Briefcase,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  FileText,
  Send,
} from 'lucide-react';

const decisionButtonClasses = {
  approved: 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 border-emerald-200 dark:border-emerald-900/50',
  rejected: 'text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/50 border-red-200 dark:border-red-900/50',
};

function StudentIdentity({ item }) {
  return (
    <Link to={`/students/${item.student_id}`} className="block group">
      <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
        {item.student_name || `Student ${item.student_id}`}
      </div>
      <div className="text-xs text-muted-foreground">
        {item.student_string_id || item.student_email || ''}
      </div>
    </Link>
  );
}

export default function Internships() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [pendingInternships, setPendingInternships] = useState([]);
  const [approvedInternships, setApprovedInternships] = useState([]);
  const [pendingReports, setPendingReports] = useState([]);

  const [activeInternshipDecision, setActiveInternshipDecision] = useState(null);
  const [internshipDecisionNotes, setInternshipDecisionNotes] = useState('');
  const [submittingInternshipDecision, setSubmittingInternshipDecision] = useState(false);

  const [selectedInternshipId, setSelectedInternshipId] = useState('');
  const [reportSummary, setReportSummary] = useState('');
  const [submittingReport, setSubmittingReport] = useState(false);

  const [activeReportDecision, setActiveReportDecision] = useState(null);
  const [reportDecisionNotes, setReportDecisionNotes] = useState('');
  const [submittingReportDecision, setSubmittingReportDecision] = useState(false);

  const loadData = useCallback(async (background = false) => {
    try {
      if (!background) setLoading(true);
      const [internshipQueue, eligible, reportQueue] = await Promise.all([
        getPendingInternships(1, 50),
        getApprovedInternships(),
        getPendingProgressReports(),
      ]);

      const pendingItems = Array.isArray(internshipQueue)
        ? internshipQueue
        : internshipQueue?.items || [];

      const eligibleItems = Array.isArray(eligible) ? eligible : [];
      setPendingInternships(pendingItems);
      setApprovedInternships(eligibleItems);
      setPendingReports(Array.isArray(reportQueue) ? reportQueue : []);
      setSelectedInternshipId(current => {
        if (eligibleItems.some(item => String(item.id) === current)) return current;
        return eligibleItems.length ? String(eligibleItems[0].id) : '';
      });
    } catch (err) {
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
      setActiveInternshipDecision(null);
      setInternshipDecisionNotes('');
      await loadData(true);
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setSubmittingInternshipDecision(false);
    }
  };

  const handleReportSubmit = async (event) => {
    event.preventDefault();
    if (!selectedInternshipId) {
      addToast('Select an approved internship first.', 'error');
      return;
    }

    try {
      setSubmittingReport(true);
      const report = await submitInternshipProgressReport(Number(selectedInternshipId), {
        summary: reportSummary.trim() || null,
      });
      addToast(`Bi-weekly report #${report.report_number} sent for review`);
      setReportSummary('');
      await loadData(true);
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setSubmittingReport(false);
    }
  };

  const handleReportDecision = async (event) => {
    event.preventDefault();
    if (!activeReportDecision) return;

    try {
      setSubmittingReportDecision(true);
      await makeProgressReportDecision(activeReportDecision.id, {
        status: activeReportDecision.status,
        review_notes: reportDecisionNotes.trim() || null,
      });
      addToast(`Progress report ${activeReportDecision.status} successfully`);
      setActiveReportDecision(null);
      setReportDecisionNotes('');
      await loadData(true);
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setSubmittingReportDecision(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <Skeleton className="h-10 w-64" />
        {Array(3).fill(0).map((_, index) => (
          <Card key={index}>
            <div className="p-6 space-y-4">
              <Skeleton className="h-6 w-56" />
              <Skeleton className="h-24 w-full" />
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const selectedInternship = approvedInternships.find(
    item => String(item.id) === selectedInternshipId,
  );

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Internship Management</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Approve internships, submit bi-weekly progress reports, and review each report.
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

      <Card className="flex flex-col overflow-hidden">
        <CardHeader>
          <CardTitle>1. Pending Internship Applications</CardTitle>
          <CardDescription>Approving an application immediately makes it available in the report submission section.</CardDescription>
        </CardHeader>
        <div className="overflow-x-auto border-t">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Company</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Internship Title</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Dates</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {pendingInternships.length === 0 ? (
                <tr><td colSpan="5" className="p-0"><EmptyState icon={Briefcase} title="No Pending Applications" description="All internship applications have been processed." className="my-10" /></td></tr>
              ) : pendingInternships.map(internship => (
                <React.Fragment key={internship.id}>
                  <tr className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap"><StudentIdentity item={internship} /></td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{internship.company_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{internship.position}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{internship.start_date} to {internship.end_date}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      {activeInternshipDecision?.id === internship.id ? (
                        <Button variant="ghost" size="sm" onClick={() => { setActiveInternshipDecision(null); setInternshipDecisionNotes(''); }}>Cancel</Button>
                      ) : (
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" className={decisionButtonClasses.approved} onClick={() => setActiveInternshipDecision({ id: internship.id, status: 'approved' })}>Approve</Button>
                          <Button variant="outline" size="sm" className={decisionButtonClasses.rejected} onClick={() => setActiveInternshipDecision({ id: internship.id, status: 'rejected' })}>Reject</Button>
                        </div>
                      )}
                    </td>
                  </tr>
                  {activeInternshipDecision?.id === internship.id && (
                    <tr className="bg-muted/20">
                      <td colSpan="5" className="px-6 py-4">
                        <form onSubmit={handleInternshipDecision} className="ml-auto flex max-w-2xl flex-col gap-4 rounded-md border bg-card p-4 shadow-sm sm:flex-row sm:items-end">
                          <div className="flex-1">
                            <label className="mb-1.5 block text-xs font-medium">
                              {activeInternshipDecision.status === 'rejected' ? 'Rejection reason' : 'Approval note (optional)'}
                            </label>
                            <textarea value={internshipDecisionNotes} onChange={event => setInternshipDecisionNotes(event.target.value)} required={activeInternshipDecision.status === 'rejected'} className="flex min-h-[76px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" placeholder={activeInternshipDecision.status === 'rejected' ? 'Explain why the internship is rejected...' : 'Optional internal note...'} />
                          </div>
                          <Button type="submit" variant={activeInternshipDecision.status === 'approved' ? 'default' : 'destructive'} isLoading={submittingInternshipDecision}>Confirm {activeInternshipDecision.status === 'approved' ? 'Approval' : 'Rejection'}</Button>
                        </form>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Send Bi-Weekly Report</CardTitle>
          <CardDescription>Select a student with an approved internship. The report number is assigned automatically; no PDF upload is required.</CardDescription>
        </CardHeader>
        <CardContent>
          {approvedInternships.length === 0 ? (
            <EmptyState icon={FileText} title="No Approved Internships" description="Approve an internship application to make the student eligible for progress reports." className="my-8" />
          ) : (
            <form onSubmit={handleReportSubmit} className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
              <div>
                <label className="mb-2 block text-sm font-medium">Student and internship</label>
                <Select value={selectedInternshipId} onChange={event => setSelectedInternshipId(event.target.value)}>
                  {approvedInternships.map(internship => (
                    <option key={internship.id} value={internship.id}>
                      {internship.student_name} — {internship.position} at {internship.company_name}
                    </option>
                  ))}
                </Select>
                {selectedInternship && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    This will create progress report #{selectedInternship.next_progress_report_number} for {selectedInternship.student_email}.
                  </p>
                )}
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">Short progress summary (optional)</label>
                <textarea value={reportSummary} onChange={event => setReportSummary(event.target.value)} maxLength={2000} className="flex min-h-[90px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" placeholder="What was completed during this two-week period?" />
              </div>
              <Button type="submit" isLoading={submittingReport} className="gap-2"><Send className="h-4 w-4" />Send Report</Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Card className="flex flex-col overflow-hidden">
        <CardHeader>
          <CardTitle>3. Review Bi-Weekly Reports</CardTitle>
          <CardDescription>Approve or reject submitted reports. Each decision creates a webhook-ready progress report status event.</CardDescription>
        </CardHeader>
        <div className="overflow-x-auto border-t">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Report</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Internship</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Summary</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Submitted</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {pendingReports.length === 0 ? (
                <tr><td colSpan="6" className="p-0"><EmptyState icon={ClipboardCheck} title="No Reports Awaiting Review" description="Submitted bi-weekly reports will appear here." className="my-10" /></td></tr>
              ) : pendingReports.map(report => (
                <React.Fragment key={report.id}>
                  <tr className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap"><Badge variant="secondary">Report #{report.report_number}</Badge></td>
                    <td className="px-6 py-4 whitespace-nowrap"><StudentIdentity item={report} /></td>
                    <td className="px-6 py-4"><div className="text-sm font-medium">{report.internship_title}</div><div className="text-xs text-muted-foreground">{report.company_name}</div></td>
                    <td className="px-6 py-4 text-sm text-muted-foreground max-w-sm"><p className="line-clamp-2">{report.summary || 'No summary provided.'}</p></td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">{new Date(report.submitted_at).toLocaleString()}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      {activeReportDecision?.id === report.id ? (
                        <Button variant="ghost" size="sm" onClick={() => { setActiveReportDecision(null); setReportDecisionNotes(''); }}>Cancel</Button>
                      ) : (
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="sm" className={decisionButtonClasses.approved} onClick={() => setActiveReportDecision({ id: report.id, status: 'approved' })}>Approve</Button>
                          <Button variant="outline" size="sm" className={decisionButtonClasses.rejected} onClick={() => setActiveReportDecision({ id: report.id, status: 'rejected' })}>Reject</Button>
                        </div>
                      )}
                    </td>
                  </tr>
                  {activeReportDecision?.id === report.id && (
                    <tr className="bg-muted/20">
                      <td colSpan="6" className="px-6 py-4">
                        <form onSubmit={handleReportDecision} className="ml-auto flex max-w-2xl flex-col gap-4 rounded-md border bg-card p-4 shadow-sm sm:flex-row sm:items-end">
                          <div className="flex-1">
                            <label className="mb-1.5 block text-xs font-medium">
                              {activeReportDecision.status === 'rejected' ? 'Rejection reason' : 'Review note (optional)'}
                            </label>
                            <textarea value={reportDecisionNotes} onChange={event => setReportDecisionNotes(event.target.value)} required={activeReportDecision.status === 'rejected'} maxLength={1000} className="flex min-h-[76px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" placeholder={activeReportDecision.status === 'rejected' ? 'Explain what needs to be corrected...' : 'Optional review note...'} />
                          </div>
                          <Button type="submit" variant={activeReportDecision.status === 'approved' ? 'default' : 'destructive'} isLoading={submittingReportDecision}>Confirm {activeReportDecision.status === 'approved' ? 'Approval' : 'Rejection'}</Button>
                        </form>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
