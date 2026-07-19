import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getPendingInternships, makeInternshipDecision } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import Pagination from '../components/Pagination';
import { Briefcase } from 'lucide-react';

export default function Internships() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [internships, setInternships] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [activeDecision, setActiveDecision] = useState(null);
  const [decisionNotes, setDecisionNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchInternships = async (pageNum = 1) => {
    try {
      setLoading(true);
      const res = await getPendingInternships(pageNum, 50);
      if (Array.isArray(res)) {
        setInternships(res);
        setTotalPages(1);
      } else {
        setInternships(res?.items || []);
        setTotalPages(res?.total_pages || 1);
        setPage(res?.page || 1);
      }
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInternships(page);
  }, [page]);

  const handleDecisionSubmit = async (e) => {
    e.preventDefault();
    if (!activeDecision) return;

    try {
      setSubmitting(true);
      await makeInternshipDecision(activeDecision.id, {
        status: activeDecision.status,
        rejection_reason: activeDecision.status === 'rejected' ? decisionNotes : null
      });
      
      addToast(`Internship ${activeDecision.status} successfully`);
      
      setInternships(prev => prev.filter(i => i.id !== activeDecision.id));
      setActiveDecision(null);
      setDecisionNotes('');
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && internships.length === 0) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <Skeleton className="h-10 w-48 mb-2" />
        <Card>
          <div className="p-6 space-y-4">
            {Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Pending Internships</h1>
        <p className="text-sm text-muted-foreground mt-1">Review and approve student internship applications</p>
      </div>

      <Card className="flex flex-col overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student ID</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Company</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Position</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Dates</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {internships.length === 0 ? (
                <tr>
                  <td colSpan="5" className="p-0">
                    <EmptyState
                      icon={Briefcase}
                      title="No Pending Applications"
                      description="All internship applications have been processed."
                      className="my-12"
                    />
                  </td>
                </tr>
              ) : (
                internships.map((internship) => (
                  <React.Fragment key={internship.id}>
                    <tr className="hover:bg-muted/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link to={`/students/${internship.student_id}`} className="block group">
                          <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                            {internship.student?.name || internship.student_name || `Student ${internship.student_id}`}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {internship.student?.student_id || internship.student_string_id || ''}
                          </div>
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground font-medium">
                        {internship.company_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {internship.position}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {internship.start_date} to {internship.end_date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                        {activeDecision?.id === internship.id ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => { setActiveDecision(null); setDecisionNotes(''); }}
                          >
                            Cancel
                          </Button>
                        ) : (
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 border-emerald-200 dark:border-emerald-900/50"
                              onClick={() => setActiveDecision({ id: internship.id, status: 'approved' })}
                            >
                              Approve
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/50 border-red-200 dark:border-red-900/50"
                              onClick={() => setActiveDecision({ id: internship.id, status: 'rejected' })}
                            >
                              Reject
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                    
                    {/* Inline Decision Form */}
                    {activeDecision?.id === internship.id && (
                      <tr className="bg-muted/20 border-b border-border">
                        <td colSpan="5" className="px-6 py-4">
                          <form onSubmit={handleDecisionSubmit} className="flex flex-col sm:flex-row gap-4 items-start bg-card p-4 rounded-md border shadow-sm w-full max-w-2xl ml-auto">
                            <div className="flex-1 w-full">
                              <label className="block text-xs font-medium text-foreground mb-1.5">
                                {activeDecision.status === 'approved' ? 'Approval Notes (Optional)' : 'Rejection Reason (Required)'}
                              </label>
                              <textarea
                                value={decisionNotes}
                                onChange={e => setDecisionNotes(e.target.value)}
                                required={activeDecision.status === 'rejected'}
                                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder={activeDecision.status === 'rejected' ? 'Explain why this application is rejected...' : 'Add optional notes...'}
                              />
                            </div>
                            <div className="mt-6 flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                              <Button
                                type="submit"
                                variant={activeDecision.status === 'approved' ? 'default' : 'destructive'}
                                disabled={submitting}
                                isLoading={submitting}
                              >
                                Confirm {activeDecision.status === 'approved' ? 'Approval' : 'Rejection'}
                              </Button>
                            </div>
                          </form>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
        {internships.length > 0 && (
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>
    </div>
  );
}
