import React, { useState, useEffect, useMemo, useRef } from 'react';
import { getStudents, getStudentSummary, publishAssessment } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { Search, ChevronDown } from 'lucide-react';

function getAlphabeticalGrade(percentage) {
  if (percentage == null) return '-';
  if (percentage >= 90) return 'A+';
  if (percentage >= 85) return 'A';
  if (percentage >= 80) return 'A-';
  if (percentage >= 75) return 'B+';
  if (percentage >= 70) return 'B';
  if (percentage >= 65) return 'B-';
  if (percentage >= 60) return 'C+';
  if (percentage >= 50) return 'C';
  if (percentage >= 45) return 'C-';
  if (percentage >= 40) return 'D';
  return 'F';
}

export default function GradesDeadlines() {
  const { addToast } = useToast();
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [students, setStudents] = useState([]);
  
  // Student selection state
  const [searchTerm, setSearchTerm] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  
  // Selected student data
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [assessments, setAssessments] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  
  // Action state
  const [actionLoading, setActionLoading] = useState(false);
  const [inlineScores, setInlineScores] = useState({});
  const dropdownRef = useRef(null);

  useEffect(() => {
    async function fetchAllStudents() {
      try {
        setLoadingStudents(true);
        const res = await getStudents(1, 200);
        const list = Array.isArray(res) ? res : (res?.items || []);
        setStudents(list);
      } catch (err) {
        addToast("Failed to fetch students", "error");
      } finally {
        setLoadingStudents(false);
      }
    }
    fetchAllStudents();

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
      
      const courses = Array.from(new Set(studentAssessments.map(a => a.course_code)));
      if (courses.length > 0 && !courses.includes(selectedCourse)) {
        setSelectedCourse(courses[0]);
      } else if (courses.length === 0) {
        setSelectedCourse('');
      }
    } catch (err) {
      addToast("Failed to load student grades", "error");
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleSelectStudent = (student) => {
    setSelectedStudent(student);
    setSearchTerm(`${student.student_id} - ${student.name}`);
    setIsDropdownOpen(false);
    loadStudentSummary(student);
  };

  const filteredStudents = useMemo(() => {
    if (!searchTerm) return students;
    const lowerSearch = searchTerm.toLowerCase();
    return students.filter(s => 
      (s.name || '').toLowerCase().includes(lowerSearch) || 
      (s.student_id || '').toLowerCase().includes(lowerSearch)
    );
  }, [students, searchTerm]);

  const courses = useMemo(() => {
    return Array.from(new Set(assessments.map(a => a.course_code))).sort();
  }, [assessments]);

  const coursework = useMemo(() => {
    return assessments.filter(a => 
      a.course_code === selectedCourse && 
      a.assessment_type !== 'midterm' && 
      a.assessment_type !== 'final'
    );
  }, [assessments, selectedCourse]);

  const examSummary = useMemo(() => {
    return courses.map(course_code => {
      const midterm = assessments.find(a => a.course_code === course_code && a.assessment_type === 'midterm');
      const final = assessments.find(a => a.course_code === course_code && a.assessment_type === 'final');
      
      const calcPercent = (assessment) => {
        if (!assessment || !assessment.is_published || assessment.score == null) return null;
        return (assessment.score / assessment.max_score) * 100;
      };

      return {
        course_code,
        midterm,
        final,
        midPercent: calcPercent(midterm),
        finPercent: calcPercent(final)
      };
    });
  }, [assessments, courses]);

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
      <Card className="p-4 bg-card border">
        <div className="flex flex-col gap-2 relative" ref={dropdownRef}>
          <label className="text-sm font-medium text-foreground">Select Student:</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input 
              type="text"
              placeholder={loadingStudents ? "Loading students..." : "Search by name or ID..."}
              className="w-full pl-9 pr-4 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setIsDropdownOpen(true);
                if (selectedStudent && e.target.value !== `${selectedStudent.student_id} - ${selectedStudent.name}`) {
                  setSelectedStudent(null);
                  setAssessments([]);
                }
              }}
              onFocus={() => setIsDropdownOpen(true)}
              disabled={loadingStudents}
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
                    <span className="font-medium text-foreground">{student.name}</span>
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
              {selectedStudent.student_id} {selectedStudent.name}
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
                    value={selectedCourse}
                    onChange={(e) => setSelectedCourse(e.target.value)}
                  >
                    {courses.map(c => <option key={c} value={c}>{c}</option>)}
                    {courses.length === 0 && <option value="">No courses found</option>}
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
                            <td className="px-4 py-3 text-sm capitalize">{item.assessment_type} {index + 1}</td>
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

              {/* Exam Results Table */}
              <div className="space-y-3 mt-10">
                <h3 className="text-sm font-medium text-foreground">Exam Results</h3>
                <div className="border rounded-md overflow-hidden bg-card">
                  <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Course</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Mid-Term Percentage</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Final Percentage</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Final Grade (Alpha)</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Actions (Unpublished)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {examSummary.length === 0 ? (
                        <tr><td colSpan="5" className="p-4 text-center text-sm text-muted-foreground">No exams found.</td></tr>
                      ) : (
                        examSummary.map((summary) => (
                          <tr key={summary.course_code} className="hover:bg-muted/30 transition-colors">
                            <td className="px-4 py-3 text-sm font-medium">{summary.course_code}</td>
                            
                            {/* Midterm Column */}
                            <td className="px-4 py-3 text-sm">
                              {summary.midterm ? (
                                summary.midterm.is_published ? (
                                  <span className="font-semibold">{summary.midPercent?.toFixed(4)} %</span>
                                ) : (
                                  <Badge variant="secondary">Pending ({summary.midterm.max_score} pts)</Badge>
                                )
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                            
                            {/* Final % Column */}
                            <td className="px-4 py-3 text-sm">
                              {summary.final ? (
                                summary.final.is_published ? (
                                  <span className="font-semibold">{summary.finPercent?.toFixed(4)} %</span>
                                ) : (
                                  <Badge variant="secondary">Pending ({summary.final.max_score} pts)</Badge>
                                )
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>

                            {/* Final Alpha Column */}
                            <td className="px-4 py-3 text-sm font-bold">
                              {summary.final && summary.final.is_published ? (
                                getAlphabeticalGrade(summary.finPercent)
                              ) : '-'}
                            </td>

                            {/* Actions Column (Inline Publish for exams) */}
                            <td className="px-4 py-3 text-right">
                              <div className="flex flex-col items-end gap-2">
                                {summary.midterm && !summary.midterm.is_published && (
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground">Mid:</span>
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
                                {summary.final && !summary.final.is_published && (
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs text-muted-foreground">Fin:</span>
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
                              </div>
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
