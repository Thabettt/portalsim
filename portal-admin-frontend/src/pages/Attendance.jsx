import React, { useState, useEffect } from 'react';
import { getCourses, getCourseAttendance, getCourseAttendanceByDate, batchMarkAttendance } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { ClipboardList, GraduationCap, Users } from 'lucide-react';

export default function Attendance() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [courses, setCourses] = useState([]);
  
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  
  const [dailyRoster, setDailyRoster] = useState([]);
  const [loadingDailyRoster, setLoadingDailyRoster] = useState(false);
  const [attendanceMarks, setAttendanceMarks] = useState({}); // { student_id: boolean }

  const [courseAttendance, setCourseAttendance] = useState(null);
  const [loadingCourseStats, setLoadingCourseStats] = useState(false);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const crsData = await getCourses(1, 200);
      setCourses(Array.isArray(crsData) ? crsData : (crsData?.items || []));
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const loadDailyRosterAndStats = async (courseId, date) => {
    if (!courseId || !date) return;
    try {
      setLoadingDailyRoster(true);
      setLoadingCourseStats(true);
      
      const course = courses.find(c => c.id === parseInt(courseId));
      
      const [rosterData, statsData] = await Promise.all([
        getCourseAttendanceByDate(courseId, date),
        getCourseAttendance(course.code)
      ]);
      
      setDailyRoster(rosterData);
      
      // Initialize checkboxes
      const marks = {};
      rosterData.forEach(student => {
        // If status is present, check it. If absent or null, uncheck it.
        marks[student.student_id] = student.status === 'present';
      });
      setAttendanceMarks(marks);
      
      setCourseAttendance(statsData);
      
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoadingDailyRoster(false);
      setLoadingCourseStats(false);
    }
  };

  useEffect(() => {
    if (selectedCourseId && selectedDate && courses.length > 0) {
      loadDailyRosterAndStats(selectedCourseId, selectedDate);
    } else {
      setDailyRoster([]);
      setCourseAttendance(null);
    }
  }, [selectedCourseId, selectedDate, courses]);

  const handleBatchSave = async () => {
    if (!selectedCourseId || !selectedDate) return;
    if (dailyRoster.length === 0) {
      addToast("No students to mark", "warning");
      return;
    }
    
    try {
      setActionLoading(true);
      
      const records = Object.keys(attendanceMarks).map(studentId => ({
        student_id: parseInt(studentId),
        status: attendanceMarks[studentId] ? "present" : "absent"
      }));
      
      await batchMarkAttendance({
        course_id: parseInt(selectedCourseId),
        date: selectedDate,
        records: records
      });
      
      addToast("Attendance saved successfully");
      
      // Reload everything to reflect new stats and status
      await loadDailyRosterAndStats(selectedCourseId, selectedDate);
      
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCheckboxChange = (studentId) => {
    setAttendanceMarks(prev => ({
      ...prev,
      [studentId]: !prev[studentId]
    }));
  };

  const handleSelectAll = (checked) => {
    const marks = {};
    dailyRoster.forEach(student => {
      marks[student.student_id] = checked;
    });
    setAttendanceMarks(marks);
  };

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in-up">
        <Skeleton className="h-10 w-48 mb-2" />
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-[500px]" />
          <Skeleton className="h-[500px]" />
        </div>
      </div>
    );
  }

  const selectedCourseCode = selectedCourseId ? courses.find(c => c.id === parseInt(selectedCourseId))?.code : null;

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Attendance</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage and view student attendance</p>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle>Attendance Controls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Course</label>
              <Select
                value={selectedCourseId}
                onChange={e => setSelectedCourseId(e.target.value)}
              >
                <option value="">Select Course...</option>
                {courses.map(c => (
                  <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Date</label>
              <Input
                type="date"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* Left column: Daily Roster for Marking */}
        <Card className="flex flex-col h-[600px] overflow-hidden border-primary/20 shadow-md">
          <CardHeader className="border-b py-4 bg-muted/20 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm">Daily Roster</CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedCourseId ? `Mark attendance for ${selectedDate}` : 'Select a course to mark attendance'}
              </p>
            </div>
          </CardHeader>
          <div className="overflow-auto flex-1 bg-card">
            {loadingDailyRoster ? (
              <div className="p-6 space-y-4">
                {Array(8).fill(0).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : dailyRoster.length > 0 ? (
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50 sticky top-0 z-10 backdrop-blur-sm">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <div className="flex items-center justify-end gap-2">
                        <span>Present</span>
                        <input 
                          type="checkbox" 
                          className="w-4 h-4 rounded border-input accent-primary"
                          onChange={(e) => handleSelectAll(e.target.checked)}
                          checked={dailyRoster.length > 0 && Object.values(attendanceMarks).every(Boolean)}
                        />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {dailyRoster.map((student) => (
                    <tr 
                      key={student.student_id} 
                      className={`hover:bg-muted/50 transition-colors cursor-pointer ${attendanceMarks[student.student_id] ? 'bg-primary/5' : ''}`}
                      onClick={() => handleCheckboxChange(student.student_id)}
                    >
                      <td className="px-6 py-3 whitespace-nowrap">
                        <div className="text-sm font-medium text-foreground">{student.full_name}</div>
                        <div className="text-xs text-muted-foreground">{student.student_string_id}</div>
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-right">
                        <input 
                          type="checkbox"
                          className="w-5 h-5 rounded border-input accent-primary"
                          checked={attendanceMarks[student.student_id] || false}
                          onChange={() => handleCheckboxChange(student.student_id)}
                          onClick={e => e.stopPropagation()}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState
                icon={Users}
                title="No Students Found"
                description={selectedCourseId ? "There are no students enrolled in this course." : "Select a course to view the daily roster."}
                className="h-full"
              />
            )}
          </div>
          {dailyRoster.length > 0 && (
            <div className="p-4 border-t bg-muted/10">
              <Button 
                className="w-full" 
                onClick={handleBatchSave}
                isLoading={actionLoading}
              >
                Confirm & Save Attendance
              </Button>
            </div>
          )}
        </Card>

        {/* Right column: Overall Course Roster Summary */}
        <Card className="flex flex-col h-[600px] overflow-hidden">
          <CardHeader className="border-b py-4 bg-muted/20">
            <CardTitle className="text-sm">
              {courseAttendance ? `Roster Summary: ${courseAttendance.course.code}` : 'Course Summary'}
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              {courseAttendance ? courseAttendance.course.name : 'Select a course to view summary'}
            </p>
          </CardHeader>
          <div className="overflow-auto flex-1 bg-card">
            {loadingCourseStats ? (
              <div className="p-6 space-y-4">
                {Array(8).fill(0).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : courseAttendance && Object.keys(courseAttendance.students).length > 0 ? (
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50 sticky top-0 z-10 backdrop-blur-sm">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Student</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">Present</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">Absent</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Warning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {Object.entries(courseAttendance.students).map(([studentId, data]) => (
                    <tr key={studentId} className="hover:bg-muted/50 transition-colors">
                      <td className="px-6 py-3 whitespace-nowrap">
                        <div className="text-sm font-medium text-foreground">{data.student_name}</div>
                        <div className="text-xs text-muted-foreground">{studentId}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm font-medium">{data.present}</td>
                      <td className="px-4 py-3 whitespace-nowrap text-center text-sm font-medium">{data.absent}</td>
                      <td className="px-6 py-3 whitespace-nowrap text-sm">
                        {data.warning_level && data.warning_level !== 'none' ? (
                           <Badge variant={data.warning_level === 'high' || data.warning_level === 'severe' ? 'danger' : 'warning'} className="uppercase text-[10px]">
                             {data.warning_level.replace('_', ' ')}
                           </Badge>
                        ) : (
                          <span className="text-muted-foreground text-xs font-medium">None</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState
                icon={courseAttendance ? ClipboardList : GraduationCap}
                title={courseAttendance ? "No Records Found" : "Select a Course"}
                description={courseAttendance ? "There are no attendance records for this course yet." : "Choose a course from the sidebar to view its attendance roster."}
                className="h-full"
              />
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
