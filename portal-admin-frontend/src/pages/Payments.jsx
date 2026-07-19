import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getOverduePayments, simulatePaymentReminders } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';
import { Badge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import Pagination from '../components/Pagination';
import { CreditCard } from 'lucide-react';

export default function Payments() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [payments, setPayments] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchPayments = async (pageNum = 1) => {
    try {
      setLoading(true);
      const res = await getOverduePayments(pageNum, 50);
      if (Array.isArray(res)) {
        setPayments(res);
        setTotalPages(1);
      } else {
        setPayments(res?.items || []);
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
    fetchPayments(page);
  }, [page]);

  const handleRunReminders = async () => {
    try {
      setActionLoading(true);
      const res = await simulatePaymentReminders();
      addToast(res?.message || "Payment reminders processed successfully");
      fetchPayments(page);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && payments.length === 0) {
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Overdue Payments</h1>
          <p className="text-sm text-muted-foreground mt-1">Actionable queue of students at risk</p>
        </div>
        <div>
          <Button
            onClick={handleRunReminders}
            disabled={actionLoading || loading}
            isLoading={actionLoading}
          >
            Run Payment Reminders Now
          </Button>
        </div>
      </div>

      <Card className="flex flex-col overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Due Date</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {payments.length === 0 ? (
                <tr>
                  <td colSpan="5" className="p-0">
                    <EmptyState
                      icon={CreditCard}
                      title="No Overdue Payments"
                      description="All student payments are currently up to date."
                      className="my-12"
                    />
                  </td>
                </tr>
              ) : (
                payments.map((payment) => (
                  <tr key={payment.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link to={`/students/${payment.student_id}`} className="block group">
                        <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{payment.student_name || `Student ${payment.student_id}`}</div>
                        <div className="text-xs text-muted-foreground">{payment.student_string_id || ''}</div>
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground capitalize">
                      {payment.payment_type?.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      ${payment.amount?.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                      {payment.due_date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={payment.status === 'overdue' ? 'danger' : 'secondary'} className="capitalize">
                        {payment.status}
                      </Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {payments.length > 0 && (
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>
    </div>
  );
}
