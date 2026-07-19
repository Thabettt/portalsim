import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getStudentSummary } from '../api';
import { useToast } from '../hooks/useToast';
import Loader from '../components/Loader';
import { ArrowLeft, User, GraduationCap, CreditCard, Clock } from 'lucide-react';

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

  const { student, attendance, payments, grades } = data;

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
        <div className="bg-card rounded-lg border p-6 shadow-sm">
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
        <div className="bg-card rounded-lg border p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard className="w-5 h-5 text-emerald-500" />
            <h2 className="text-lg font-semibold text-card-foreground">Financials</h2>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Total Billed</span>
              <span className="font-semibold">${payments?.total_amount?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="flex justify-between items-end border-b pb-2">
              <span className="text-muted-foreground">Total Paid</span>
              <span className="font-semibold text-emerald-500">${payments?.total_paid?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="flex justify-between items-end">
              <span className="text-muted-foreground">Outstanding</span>
              <span className={`font-semibold ${payments?.total_outstanding > 0 ? 'text-destructive' : 'text-foreground'}`}>
                ${payments?.total_outstanding?.toFixed(2) || '0.00'}
              </span>
            </div>
          </div>
        </div>

        {/* Academic Summary */}
        <div className="bg-card rounded-lg border p-6 shadow-sm">
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

      {/* Detailed Lists */}
      <div className="bg-card rounded-lg border shadow-sm mt-8 overflow-hidden">
        <div className="px-6 py-4 border-b bg-muted/50">
          <h2 className="text-lg font-semibold text-card-foreground">Assessments Details</h2>
        </div>
        <div className="p-0 overflow-x-auto">
          {grades?.assessments?.length > 0 ? (
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Course</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Assessment</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {grades.assessments.map(a => (
                  <tr key={a.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">{a.course_code}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground capitalize">{a.title} ({a.assessment_type})</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {a.score !== null ? a.score : '-'}/{a.max_score}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {a.is_published ? (
                        <span className="px-2 py-1 text-xs font-medium bg-emerald-500/10 text-emerald-500 rounded-full">Published</span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium bg-muted text-foreground rounded-full">Pending</span>
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
