import React, { useState, useEffect, useMemo, useRef } from 'react';
import { getStudents, getCourses, getStudentSummary, publishAssessment } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { Search, ChevronDown } from 'lucide-react';

function getAlphabeticalGrade(score) {
  if (score == null) return '-';
  if (score < 50) return 'F';
  if (score < 55) return 'D';
  if (score < 60) return 'D+';
  if (score < 65) return 'C-';
  if (score < 70) return 'C';
  if (score < 74) return 'C+';
  if (score < 78) return 'B-';
  if (score < 82) return 'B';
  if (score < 86) return 'B+';
  if (score < 90) return 'A-';
  if (score < 94) return 'A';
  return 'A+';
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function GradesDeadlines() {
  const { addToast } = useToast();
  
  // App-wide data
  const [loadingData, setLoadingData] = useState(true);
  const [students, setStudents] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  
  // Student selection state
  const [searchTerm, setSearchTerm] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  
  // Selected student data
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [assessments, setAssessments] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState('');
  
  // Action state
  const [actionLoading, setActionLoading] = useState(false);
  const [inlineScores, setInlineScores] = useState({});
  const dropdownRef = useRef(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoadingData(true);
        const [studentsRes, coursesRes] = await Promise.all([
          getStudents(1, 200),
          getCourses(1, 200)
        ]);
        const sList = Array.isArray(studentsRes) ? studentsRes : (studentsRes?.items || []);
        const cList = Array.isArray(coursesRes) ? coursesRes : (coursesRes?.items || []);
        setStudents(sList);
        setAllCourses(cList);
      } catch (err) {
        addToast("Failed to fetch initial data", "error");
      } finally {
        setLoadingData(false);
      }
    }
    fetchData();

    // Close dropdown on click outside
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadStudentSummary = async (student) => {
    try {
      setLoadingSummary(true);
      const summary = await getStudentSummary(student.id);
      const studentAssessments = summary?.grades?.assessments || [];
      setAssessments(studentAssessments);
      
      const courseIds = Array.from(new Set(studentAssessments.map(a => a.course_id)));
      if (courseIds.length > 0 && !courseIds.includes(selectedCourseId)) {
        setSelectedCourseId(courseIds[0]);
      } else if (courseIds.length === 0) {
        setSelectedCourseId('');
      }
    } catch (err) {
      addToast("Failed to load student grades", "error");
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleSelectStudent = (student) => {
    setSelectedStudent(student);
    setSearchTerm(`${student.student_id} - ${student.full_name}`);
    setIsDropdownOpen(false);
    loadStudentSummary(student);
  };

  const filteredStudents = useMemo(() => {
    if (!searchTerm) return students;
    const lowerSearch = searchTerm.toLowerCase();
    return students.filter(s => 
      (s.full_name || '').toLowerCase().includes(lowerSearch) || 
      (s.student_id || '').toLowerCase().includes(lowerSearch)
    );
  }, [students, searchTerm]);

  // Unique course IDs the student has assessments for
  const studentCourseIds = useMemo(() => {
    return Array.from(new Set(assessments.map(a => a.course_id))).sort();
  }, [assessments]);

  const coursework = useMemo(() => {
    return assessments.filter(a => 
      a.course_id === Number(selectedCourseId) && 
      a.type?.toLowerCase() !== 'midterm' && 
      a.type?.toLowerCase() !== 'final'
    );
  }, [assessments, selectedCourseId]);

  const examSummary = useMemo(() => {
    return studentCourseIds.map(course_id => {
      const courseObj = allCourses.find(c => c.id === course_id);
      const courseStr = courseObj ? `${courseObj.code} - ${courseObj.name}` : `Course ID ${course_id}`;
      
      const midterm = assessments.find(a => a.course_id === course_id && a.type?.toLowerCase() === 'midterm');
      const final = assessments.find(a => a.course_id === course_id && a.type?.toLowerCase() === 'final');
      
      const calcPercent = (assessment) => {
        if (!assessment || !assessment.is_published || assessment.score == null) return null;
        return (assessment.score / assessment.max_score) * 100;
      };

      return {
        course_id,
        courseStr,
        midterm,
        final,
        midPercent: calcPercent(midterm),
        finPercent: calcPercent(final)
      };
    });
  }, [assessments, studentCourseIds, allCourses]);

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
      await loadStudentSummary(selectedStudent);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fade-in-up">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Student Grades Report</h1>
        <p className="text-sm text-muted-foreground">Search and view a student's full academic record</p>
      </div>

      {/* Student Selector */}
      <Card className="p-4 bg-card border overflow-visible">
        <div className="flex flex-col gap-2 relative" ref={dropdownRef}>
          <label className="text-sm font-medium text-foreground">Select Student:</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input 
              type="text"
              placeholder={loadingData ? "Loading students..." : "Search by name or ID..."}
              className="w-full pl-9 pr-4 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setIsDropdownOpen(true);
                if (selectedStudent && e.target.value !== `${selectedStudent.student_id} - ${selectedStudent.full_name}`) {
                  setSelectedStudent(null);
                  setAssessments([]);
                }
              }}
              onFocus={() => setIsDropdownOpen(true)}
              disabled={loadingData}
            />
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          </div>

          {isDropdownOpen && (
            <ul className="absolute top-full left-0 right-0 mt-1 z-20 bg-card border rounded-md shadow-lg max-h-60 overflow-y-auto">
              {filteredStudents.length > 0 ? (
                filteredStudents.map(student => (
                  <li 
                    key={student.id} 
                    onClick={() => handleSelectStudent(student)}
                    className="px-4 py-2 text-sm hover:bg-muted cursor-pointer flex justify-between items-center"
                  >
                    <span className="font-medium text-foreground">{student.full_name}</span>
                    <span className="text-muted-foreground text-xs">{student.student_id}</span>
                  </li>
                ))
              ) : (
                <li className="px-4 py-3 text-sm text-muted-foreground text-center">No students found</li>
              )}
            </ul>
          )}
        </div>
      </Card>

      {selectedStudent && (
        <div className="space-y-8 mt-8">
          
          {/* Header */}
          <div className="text-center bg-muted/30 py-4 rounded-md border border-border/50">
            <h2 className="text-lg font-bold text-foreground">
              {selectedStudent.student_id} {selectedStudent.full_name}
            </h2>
          </div>

          {loadingSummary ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <>
              {/* Course Selector & Coursework Table */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row gap-4 items-center">
                  <label className="text-sm font-medium text-foreground whitespace-nowrap">Course:</label>
                  <select 
                    className="w-full p-2 text-sm border rounded-md bg-card focus:outline-none focus:ring-1 focus:ring-primary"
                    value={selectedCourseId}
                    onChange={(e) => setSelectedCourseId(e.target.value)}
                  >
                    {studentCourseIds.map(cid => {
                      const cObj = allCourses.find(c => c.id === cid);
                      const name = cObj ? `${cObj.code} - ${cObj.name}` : `Course ID ${cid}`;
                      return <option key={cid} value={cid}>{name}</option>;
                    })}
                    {studentCourseIds.length === 0 && <option value="">No courses found</option>}
                  </select>
                </div>

                <div className="border rounded-md overflow-hidden bg-card">
                  <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Quiz/Assignment</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Element Name</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Grade</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Prof./Lecturer/TA</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {coursework.length === 0 ? (
                        <tr><td colSpan="5" className="p-4 text-center text-sm text-muted-foreground">No coursework found for this course.</td></tr>
                      ) : (
                        coursework.map((item, index) => (
                          <tr key={item.id} className="hover:bg-muted/30 transition-colors">
                            <td className="px-4 py-3 text-sm capitalize">{item.title}</td>
                            <td className="px-4 py-3 text-sm">{item.title}</td>
                            <td className="px-4 py-3 text-sm font-medium">
                              {item.is_published ? (
                                `${item.score} / ${item.max_score}`
                              ) : (
                                <div className="flex items-center gap-2">
                                  <input 
                                    type="number" 
                                    className="w-16 px-2 py-1 text-xs border rounded bg-background"
                                    placeholder="Score"
                                    value={inlineScores[item.id] || ''}
                                    onChange={e => setInlineScores(prev => ({...prev, [item.id]: e.target.value}))}
                                  />
                                  <span className="text-muted-foreground">/ {item.max_score}</span>
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-muted-foreground">Simulated Prof.</td>
                            <td className="px-4 py-3 text-right">
                              {!item.is_published && (
                                <Button variant="outline" size="sm" onClick={() => handlePublish(item)} disabled={actionLoading}>
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
              </div>

              {/* Midterm Results Table */}
              <div className="space-y-3 mt-10">
                <h3 className="text-sm font-medium text-foreground">Mid-Term Results</h3>
                <div className="border rounded-md overflow-hidden bg-card">
                  <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Course</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Percentage</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Published Date</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Actions (Unpublished)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {examSummary.filter(s => s.midterm).length === 0 ? (
                        <tr><td colSpan="4" className="p-4 text-center text-sm text-muted-foreground">No midterms found.</td></tr>
                      ) : (
                        examSummary.filter(s => s.midterm).map((summary) => (
                          <tr key={summary.course_id} className="hover:bg-muted/30 transition-colors">
                            <td className="px-4 py-3 text-sm font-medium">{summary.courseStr}</td>
                            
                            <td className="px-4 py-3 text-sm">
                              {summary.midterm.is_published ? (
                                <span className="font-semibold">{summary.midPercent?.toFixed(2)} %</span>
                              ) : (
                                <Badge variant="secondary">Pending ({summary.midterm.max_score} pts)</Badge>
                              )}
                            </td>
                            
                            <td className="px-4 py-3 text-sm text-muted-foreground">
                              {summary.midterm.is_published ? formatDate(summary.midterm.published_at) : '-'}
                            </td>

                            <td className="px-4 py-3 text-right">
                              {!summary.midterm.is_published && (
                                <div className="flex items-center justify-end gap-2">
                                  <input 
                                    type="number" 
                                    className="w-16 px-2 py-1 text-xs border rounded bg-background"
                                    placeholder="Score"
                                    value={inlineScores[summary.midterm.id] || ''}
                                    onChange={e => setInlineScores(prev => ({...prev, [summary.midterm.id]: e.target.value}))}
                                  />
                                  <Button variant="outline" size="sm" className="h-6 text-xs px-2" onClick={() => handlePublish(summary.midterm)} disabled={actionLoading}>Pub</Button>
                                </div>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Final Results Table */}
              <div className="space-y-3 mt-10">
                <h3 className="text-sm font-medium text-foreground">Final Results</h3>
                <div className="border rounded-md overflow-hidden bg-card">
                  <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Course</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Percentage</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Alphabetical Grade</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Published Date</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Actions (Unpublished)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {examSummary.filter(s => s.final).length === 0 ? (
                        <tr><td colSpan="5" className="p-4 text-center text-sm text-muted-foreground">No finals found.</td></tr>
                      ) : (
                        examSummary.filter(s => s.final).map((summary) => (
                          <tr key={summary.course_id} className="hover:bg-muted/30 transition-colors">
                            <td className="px-4 py-3 text-sm font-medium">{summary.courseStr}</td>
                            
                            <td className="px-4 py-3 text-sm">
                              {summary.final.is_published ? (
                                <span className="font-semibold">{summary.finPercent?.toFixed(2)} %</span>
                              ) : (
                                <Badge variant="secondary">Pending ({summary.final.max_score} pts)</Badge>
                              )}
                            </td>

                            <td className="px-4 py-3 text-sm font-bold">
                              {summary.final.is_published ? getAlphabeticalGrade(summary.finPercent) : '-'}
                            </td>
                            
                            <td className="px-4 py-3 text-sm text-muted-foreground">
                              {summary.final.is_published ? formatDate(summary.final.published_at) : '-'}
                            </td>

                            <td className="px-4 py-3 text-right">
                              {!summary.final.is_published && (
                                <div className="flex items-center justify-end gap-2">
                                  <input 
                                    type="number" 
                                    className="w-16 px-2 py-1 text-xs border rounded bg-background"
                                    placeholder="Score"
                                    value={inlineScores[summary.final.id] || ''}
                                    onChange={e => setInlineScores(prev => ({...prev, [summary.final.id]: e.target.value}))}
                                  />
                                  <Button variant="outline" size="sm" className="h-6 text-xs px-2" onClick={() => handlePublish(summary.final)} disabled={actionLoading}>Pub</Button>
                                </div>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
