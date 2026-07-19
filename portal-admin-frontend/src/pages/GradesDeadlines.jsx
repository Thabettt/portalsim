import React, { useState, useEffect } from 'react';
import { getStudents, getStudentSummary, publishAssessment, simulateDeadlineCheck } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import Pagination from '../components/Pagination';
import { BookOpen } from 'lucide-react';

export default function GradesDeadlines() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [assessments, setAssessments] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  
  const fetchAllAssessments = async () => {
    try {
      setLoading(true);
      const studentsRes = await getStudents(1, 200);
      const studentsList = Array.isArray(studentsRes) ? studentsRes : (studentsRes?.items || []);
      
      const summaries = await Promise.all(
        studentsList.map(s => getStudentSummary(s.id).catch(() => null))
      );
      
      let allAssessments = [];
      summaries.forEach((summary) => {
        if (summary && summary.grades && summary.grades.assessments) {
          summary.grades.assessments.forEach(assessment => {
            allAssessments.push({
              ...assessment,
              student: summary.student
            });
          });
        }
      });
      
      allAssessments.sort((a, b) => {
        if (a.is_published === b.is_published) {
          return new Date(a.due_date) - new Date(b.due_date);
        }
        return a.is_published ? 1 : -1;
      });
      
      setAssessments(allAssessments);
    } catch (err) {
      addToast(err.message || "Failed to fetch assessments", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllAssessments();
  }, []);

  const handlePublish = async (assessment) => {
    try {
      setActionLoading(true);
      const scoreToPublish = assessment.score !== null ? assessment.score : Math.round(assessment.max_score * 0.85);
      
      await publishAssessment(assessment.id, { score: scoreToPublish });
      addToast(`Assessment published successfully`);
      
      setAssessments(prev => prev.map(a => 
        a.id === assessment.id 
          ? { ...a, is_published: true, score: scoreToPublish } 
          : a
      ));
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunDeadlineCheck = async () => {
    try {
      setActionLoading(true);
      const res = await simulateDeadlineCheck();
      addToast(res?.message || "Deadline check processed successfully");
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && assessments.length === 0) {
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

  const totalPages = Math.ceil(assessments.length / pageSize) || 1;
  const currentAssessments = assessments.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Grades & Deadlines</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage assessment grades and trigger deadline webhooks</p>
        </div>
        <div>
          <Button
            onClick={handleRunDeadlineCheck}
            disabled={actionLoading || loading}
            isLoading={actionLoading}
          >
            Deadline Check Now
          </Button>
        </div>
      </div>

      <Card className="flex flex-col overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Course</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Assessment</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {currentAssessments.length === 0 ? (
                <tr>
                  <td colSpan="6" className="p-0">
                    <EmptyState
                      icon={BookOpen}
                      title="No Assessments"
                      description="No assessments were found for any students."
                      className="my-12"
                    />
                  </td>
                </tr>
              ) : (
                currentAssessments.map((assessment) => (
                  <tr key={assessment.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-foreground">{assessment.student?.name}</div>
                      <div className="text-xs text-muted-foreground">{assessment.student?.student_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {assessment.course_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                      {assessment.title}
                      <span className="block text-xs text-muted-foreground capitalize mt-0.5">{assessment.assessment_type}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {assessment.score !== null ? assessment.score : '-'}/{assessment.max_score}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {assessment.is_published ? (
                        <Badge variant="success">Published</Badge>
                      ) : (
                        <Badge variant="secondary">Pending</Badge>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      {!assessment.is_published && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePublish(assessment)}
                          disabled={actionLoading}
                        >
                          Publish
                        </Button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {assessments.length > 0 && (
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>
    </div>
  );
}
