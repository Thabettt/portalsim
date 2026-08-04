import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getStudentSummary } from '../api';
import { useToast } from '../hooks/useToast';
import Loader from '../components/Loader';
import { ArrowLeft, User, GraduationCap, CreditCard, Clock, Receipt, AlertCircle, CheckCircle2, Hourglass } from 'lucide-react';

const statusConfig = {
  pending:  { label: 'Pending',  icon: Hourglass,      cls: 'bg-amber-500/10 text-amber-500 border border-amber-500/20' },
  paid:     { label: 'Paid',     icon: CheckCircle2,    cls: 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' },
  overdue:  { label: 'Overdue',  icon: AlertCircle,     cls: 'bg-red-500/10 text-red-500 border border-red-500/20' },
  partial:  { label: 'Partial',  icon: CreditCard,      cls: 'bg-blue-500/10 text-blue-500 border border-blue-500/20' },
  waived:   { label: 'Waived',   icon: CheckCircle2,    cls: 'bg-gray-500/10 text-gray-400 border border-gray-500/20' },
};

function StatusBadge({ status }) {
  const cfg = statusConfig[status] || { label: status, icon: CreditCard, cls: 'bg-muted text-foreground border border-border' };
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.cls}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function CurrencyAmount({ amount, currency = 'EGP' }) {
  const symbol = currency === 'EUR' ? '€' : 'EGP ';
  return (
    <span className="font-semibold tabular-nums">
      {symbol}{typeof amount === 'number' ? amount.toFixed(2) : amount}
    </span>
  );
}

export default function StudentDetail() {
  const { studentId } = useParams();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        const res = await getStudentSummary(studentId);
        setData(res);
      } catch (err) {
        addToast(err.message || "Failed to load student summary", "error");
      } finally {
        setLoading(false);
      }
    };
    if (studentId) {
      fetchSummary();
    }
  }, [studentId, addToast]);

  if (loading) return <Loader text="Loading student profile..." className="mt-20" />;
  if (!data) return <div className="p-8 text-center text-gray-500">Student not found</div>;

  const { student, attendance, payments, payments_detail = [], grades } = data;

  // Exam remark charges are payment_type='other' with an external_reference_id (Frappe doc name)
  // Regular seeded payments (tuition, lab_fee, etc.) have no external_reference_id
  const remarkCharges = payments_detail.filter(
    p => p.payment_type === 'other' && p.external_reference_id
  );
  const regularPayments = payments_detail.filter(
    p => !(p.payment_type === 'other' && p.external_reference_id)
  );

  return (
    <div className="space-y-6 animate-fade-in-up pb-12">
      <div className="flex items-center gap-4">
        <Link to={-1} className="p-2 hover:bg-muted rounded-full transition-colors">
          <ArrowLeft className="w-5 h-5 text-muted-foreground" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            {student.name}
          </h1>
          <p className="text-muted-foreground mt-1 flex items-center gap-2">
            <User className="w-4 h-4" /> {student.student_id} | {student.email}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Attendance Summary */}
        <div className="bg-card rounded-xl border p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold text-card-foreground">Attendance</h2>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Total Courses</span>
              <span className="font-semibold">{attendance?.total_courses || 0}</span>
            </div>
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Total Absences</span>
              <span className="font-semibold text-destructive">{attendance?.total_absences || 0}</span>
            </div>
            <div>
              <span className="text-muted-foreground block mb-2">Highest Warning Level</span>
              {attendance?.highest_warning_level && attendance.highest_warning_level !== 'none' ? (
                <span className="text-destructive font-medium text-sm border border-destructive/20 bg-destructive/10 px-2 py-1 rounded-full uppercase">
                  {attendance.highest_warning_level.replace('_', ' ')}
                </span>
              ) : (
                <span className="text-muted-foreground text-sm">None</span>
              )}
            </div>
          </div>
        </div>

        {/* Payment Summary */}
        <div className="bg-card rounded-xl border p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard className="w-5 h-5 text-emerald-500" />
            <h2 className="text-lg font-semibold text-card-foreground">Financials</h2>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Total Billed</span>
              <span className="font-semibold">{payments?.total_amount?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Total Paid</span>
              <span className="font-semibold text-emerald-500">{payments?.total_paid?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="flex justify-between items-end">
              <span className="text-muted-foreground">Outstanding</span>
              <span className={`font-semibold ${payments?.total_outstanding > 0 ? 'text-destructive' : 'text-foreground'}`}>
                {payments?.total_outstanding?.toFixed(2) || '0.00'}
              </span>
            </div>
            {remarkCharges.length > 0 && (
              <div className="pt-2 mt-2 border-t">
                <span className="text-xs text-amber-500 font-medium flex items-center gap-1">
                  <Receipt className="w-3 h-3" />
                  {remarkCharges.length} exam remark {remarkCharges.length === 1 ? 'charge' : 'charges'} pending
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Academic Summary */}
        <div className="bg-card rounded-xl border p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <GraduationCap className="w-5 h-5 text-purple-500" />
            <h2 className="text-lg font-semibold text-card-foreground">Academics</h2>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Overall Average</span>
              <span className="font-semibold">{grades?.overall_average?.toFixed(1) || '-'}%</span>
            </div>
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Assessments</span>
              <span className="font-semibold">{grades?.assessments?.length || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Exam Remark Charges */}
      {remarkCharges.length > 0 && (
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b flex items-center gap-2" style={{ background: 'linear-gradient(135deg, rgba(251,191,36,0.08), rgba(245,158,11,0.04))' }}>
            <Receipt className="w-4 h-4 text-amber-500" />
            <h2 className="text-base font-semibold text-card-foreground">Exam Remark Charges</h2>
            <span className="ml-auto text-xs text-muted-foreground">Posted from Frappe ERPNext</span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Reference</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Due Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {remarkCharges.map(p => (
                  <tr key={p.id} className="hover:bg-amber-500/5 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-xs font-mono text-amber-600 bg-amber-500/10 px-2 py-0.5 rounded">
                        {p.external_reference_id || `#${p.id}`}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-foreground max-w-xs">
                      {p.description || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <CurrencyAmount amount={p.amount} currency={p.currency} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                      {p.due_date || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={p.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Regular Payments */}
      {regularPayments.length > 0 && (
        <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b bg-muted/30">
            <h2 className="text-base font-semibold text-card-foreground">Payment Records</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Due Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {regularPayments.map(p => (
                  <tr key={p.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground capitalize">
                      {p.payment_type?.replace(/_/g, ' ')}
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground max-w-xs">
                      {p.description || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <CurrencyAmount amount={p.amount} currency={p.currency} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                      {p.due_date || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={p.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Assessments Details */}
      <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-muted/30">
          <h2 className="text-base font-semibold text-card-foreground">Assessments Details</h2>
        </div>
        <div className="p-0 overflow-x-auto">
          {grades?.assessments?.length > 0 ? (
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Course</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Assessment</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {grades.assessments.map(a => (
                  <tr key={a.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">{a.course_code}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground capitalize">{a.title} ({a.assessment_type})</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {a.score !== null ? a.score : '-'}/{a.max_score}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {a.is_published ? (
                        <span className="px-2 py-1 text-xs font-medium bg-emerald-500/10 text-emerald-500 rounded-full border border-emerald-500/20">Published</span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium bg-muted text-foreground rounded-full border border-border">Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center text-muted-foreground">No assessments recorded.</div>
          )}
        </div>
      </div>
      
    </div>
  );
}
