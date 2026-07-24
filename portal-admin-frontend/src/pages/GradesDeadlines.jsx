import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { getStudents, getStudentSummary, publishAssessment, simulateDeadlineCheck } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import Pagination from '../components/Pagination';
import { BookOpen, Search, CheckCircle } from 'lucide-react';

export default function GradesDeadlines() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [assessments, setAssessments] = useState([]);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [courseFilter, setCourseFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);

  // Bulk / Inline Score State
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [inlineScores, setInlineScores] = useState({});

  // API Tester State
  const [testStudentId, setTestStudentId] = useState('');
  const [testCourse, setTestCourse] = useState('');
  const [testType, setTestType] = useState('midterm');
  const [testResult, setTestResult] = useState(null);
  
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
    const scoreStr = inlineScores[assessment.id];
    if (scoreStr === undefined || scoreStr === '') {
      addToast(`Explicit score is required to publish`, "error");
      return;
    }
    try {
      setActionLoading(true);
      const score = parseFloat(scoreStr);
      await publishAssessment(assessment.id, { score });
      addToast(`Assessment published successfully`);
      await fetchAllAssessments(); // Re-fetch to confirm update
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkPublish = async () => {
    const itemsToPublish = Array.from(selectedRows).map(id => assessments.find(a => a.id === id));
    
    // Validation
    for (const item of itemsToPublish) {
      const scoreStr = inlineScores[item.id];
      if (scoreStr === undefined || scoreStr === '') {
        addToast(`Error: Explicit score required for ${item.student?.name}'s ${item.title}. Bulk publish aborted.`, "error");
        return;
      }
    }

    try {
      setActionLoading(true);
      await Promise.all(itemsToPublish.map(item => {
        const score = parseFloat(inlineScores[item.id]);
        return publishAssessment(item.id, { score });
      }));
      addToast(`Successfully published ${itemsToPublish.length} assessments`);
      setSelectedRows(new Set());
      // Explicitly re-query to confirm they are now published
      await fetchAllAssessments(); 
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  const toggleSelection = (id) => {
    const newSet = new Set(selectedRows);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedRows(newSet);
  };

  const toggleAll = (currentPageItems) => {
    const unselected = currentPageItems.filter(item => !item.is_published && !selectedRows.has(item.id));
    const newSet = new Set(selectedRows);
    if (unselected.length > 0) {
      unselected.forEach(item => newSet.add(item.id));
    } else {
      currentPageItems.forEach(item => newSet.delete(item.id));
    }
    setSelectedRows(newSet);
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

  const handleApiTest = async () => {
    setTestResult('Testing...');
    try {
      const res = await fetch(`http://localhost:8000/api/grades/lookup?student_id=${testStudentId}&course_id=${testCourse}&assessment_type=${testType}`, {
        headers: { 'X-API-Key': 'test-grades-key' }
      });
      if (res.status === 200) {
        const data = await res.json();
        setTestResult(`✅ 200 OK (Score: ${data.score}/${data.max_score})`);
      } else if (res.status === 404) {
        setTestResult(`❌ 404 Not Found`);
      } else {
        setTestResult(`⚠️ ${res.status} Error`);
      }
    } catch (err) {
      setTestResult(`Error: ${err.message}`);
    }
  };

  // Filter & Sort Data
  const filteredAssessments = useMemo(() => {
    const filtered = assessments.filter(a => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const sname = (a.student?.name || '').toLowerCase();
        const sid = (a.student?.student_id || '').toLowerCase();
        if (!sname.includes(q) && !sid.includes(q)) return false;
      }
      if (courseFilter !== 'All' && a.course_code !== courseFilter) return false;
      if (typeFilter === 'remarkable') {
        if (a.assessment_type !== 'midterm' && a.assessment_type !== 'final') return false;
      } else if (typeFilter !== 'All' && a.assessment_type !== typeFilter) return false;
      
      if (statusFilter === 'Published' && !a.is_published) return false;
      if (statusFilter === 'Pending' && a.is_published) return false;
      
      return true;
    });

    // Sort: Student Name -> Course -> Assessment Type
    return filtered.sort((a, b) => {
      const nameA = a.student?.name || '';
      const nameB = b.student?.name || '';
      if (nameA !== nameB) return nameA.localeCompare(nameB);
      
      const courseA = a.course_code || '';
      const courseB = b.course_code || '';
      if (courseA !== courseB) return courseA.localeCompare(courseB);
      
      const typeA = a.assessment_type || '';
      const typeB = b.assessment_type || '';
      return typeA.localeCompare(typeB);
    });
  }, [assessments, searchQuery, courseFilter, typeFilter, statusFilter]);

  const uniqueCourses = useMemo(() => {
    return Array.from(new Set(assessments.map(a => a.course_code))).sort();
  }, [assessments]);

  if (loading && assessments.length === 0) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <Skeleton className="h-10 w-48 mb-2" />
        <Card><div className="p-6 space-y-4">{Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div></Card>
      </div>
    );
  }

  const totalPages = Math.ceil(filteredAssessments.length / pageSize) || 1;
  const currentAssessments = filteredAssessments.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Grades & Deadlines</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage assessment grades and trigger deadline webhooks</p>
        </div>
        <div>
          <Button onClick={handleRunDeadlineCheck} disabled={actionLoading || loading} isLoading={actionLoading}>
            Deadline Check Now
          </Button>
        </div>
      </div>

      {/* API Tester Utility */}
      <Card className="p-4 bg-muted/20 border-blue-500/30 border">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <span className="font-semibold text-sm w-32">API Lookup Tester:</span>
          <input 
            type="text" 
            placeholder="Student ID (STU-...)" 
            className="text-sm px-3 py-1.5 border rounded-md" 
            value={testStudentId} onChange={e => setTestStudentId(e.target.value)} 
          />
          <input 
            type="text" 
            placeholder="Course Code" 
            className="text-sm px-3 py-1.5 border rounded-md" 
            value={testCourse} onChange={e => setTestCourse(e.target.value)} 
          />
          <select className="text-sm px-3 py-1.5 border rounded-md bg-background" value={testType} onChange={e => setTestType(e.target.value)}>
            <option value="midterm">Midterm</option>
            <option value="final">Final</option>
          </select>
          <Button variant="outline" size="sm" onClick={handleApiTest}>Test</Button>
          {testResult && <span className="text-sm font-medium">{testResult}</span>}
        </div>
      </Card>

      <div className="flex flex-wrap gap-4 items-center bg-card p-4 rounded-lg border">
        <div className="flex items-center bg-background border rounded-md px-3 py-1.5 min-w-[200px]">
          <Search className="w-4 h-4 text-muted-foreground mr-2" />
          <input 
            type="text" 
            placeholder="Search student..." 
            className="bg-transparent border-none outline-none text-sm w-full"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        
        <select className="text-sm px-3 py-1.5 border rounded-md bg-background" value={courseFilter} onChange={e => setCourseFilter(e.target.value)}>
          <option value="All">All Courses</option>
          {uniqueCourses.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        
        <select className="text-sm px-3 py-1.5 border rounded-md bg-background" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="All">All Statuses</option>
          <option value="Pending">Pending</option>
          <option value="Published">Published</option>
        </select>

        <select className="text-sm px-3 py-1.5 border rounded-md bg-background" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
          <option value="All">All Types</option>
          <option value="quiz">Quiz</option>
          <option value="assignment">Assignment</option>
          <option value="project">Project</option>
          <option value="midterm">Midterm</option>
          <option value="final">Final</option>
        </select>

        <Button 
          variant={typeFilter === 'remarkable' ? "default" : "outline"}
          size="sm"
          className="ml-auto"
          onClick={() => setTypeFilter(prev => prev === 'remarkable' ? 'All' : 'remarkable')}
        >
          {typeFilter === 'remarkable' && <CheckCircle className="w-4 h-4 mr-2" />}
          Remarkable Only
        </Button>
      </div>

      <Card className="flex flex-col overflow-hidden">
        {selectedRows.size > 0 && (
          <div className="bg-primary/5 border-b px-6 py-3 flex items-center justify-between">
            <span className="text-sm font-medium">{selectedRows.size} pending assessment(s) selected</span>
            <Button size="sm" onClick={handleBulkPublish} disabled={actionLoading}>
              Bulk Publish
            </Button>
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input type="checkbox" onChange={() => toggleAll(currentAssessments)} checked={currentAssessments.length > 0 && currentAssessments.filter(a => !a.is_published).every(a => selectedRows.has(a.id))} />
                </th>
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
                  <td colSpan="7" className="p-0">
                    <EmptyState icon={BookOpen} title="No Assessments Found" description="Try adjusting your filters." className="my-12" />
                  </td>
                </tr>
              ) : (
                currentAssessments.map((assessment) => {
                  const isRemarkable = assessment.assessment_type === 'midterm' || assessment.assessment_type === 'final';
                  return (
                  <tr key={assessment.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4">
                      {!assessment.is_published && (
                        <input type="checkbox" checked={selectedRows.has(assessment.id)} onChange={() => toggleSelection(assessment.id)} />
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link to={`/students/${assessment.student?.id || assessment.student_id}`} className="block group">
                        <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                          {assessment.student?.name || assessment.student_name || `Student ${assessment.student?.id}`}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {assessment.student?.student_id || ''}
                        </div>
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                      {assessment.course_code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                      {assessment.title}
                      <span className="block mt-1">
                        <Badge variant={isRemarkable ? "primary" : "outline"} className="capitalize">
                          {assessment.assessment_type}
                        </Badge>
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground flex items-center gap-1">
                      {assessment.is_published ? (
                        <span>{assessment.score} / {assessment.max_score}</span>
                      ) : (
                        <>
                          <input 
                            type="number" 
                            className="w-16 px-2 py-1 text-sm border rounded"
                            placeholder="-"
                            value={inlineScores[assessment.id] || ''}
                            onChange={e => setInlineScores(prev => ({...prev, [assessment.id]: e.target.value}))}
                          />
                          <span className="text-muted-foreground">/ {assessment.max_score}</span>
                        </>
                      )}
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
                        <Button variant="outline" size="sm" onClick={() => handlePublish(assessment)} disabled={actionLoading}>
                          Publish
                        </Button>
                      )}
                    </td>
                  </tr>
                )})
              )}
            </tbody>
          </table>
        </div>
        {filteredAssessments.length > 0 && (
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>
    </div>
  );
}
