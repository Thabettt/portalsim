import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CalendarCheck2, CheckCircle2, ChevronDown, RotateCcw, Search, UserRound, XCircle } from 'lucide-react';
import { finalizeAttendanceDay, getStudents, getStudentAttendanceWarnings, updateStudentAttendanceWarnings } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

const LEVELS = [
  { value: 'none', label: 'Level 0 \u2014 Good' },
  { value: 'first_warning', label: 'Level 1 \u2014 Warning 1' },
  { value: 'second_warning', label: 'Level 2 \u2014 Warning 2' },
  { value: 'final_warning', label: 'Level 3 \u2014 Drop' },
];

const LEVEL_META = {
  first_warning: { label: 'Level 1 \u2014 Warning 1', className: 'border-yellow-300 bg-yellow-100 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950/60 dark:text-yellow-300' },
  second_warning: { label: 'Level 2 \u2014 Warning 2', className: 'border-orange-300 bg-orange-100 text-orange-800 dark:border-orange-800 dark:bg-orange-950/60 dark:text-orange-300' },
  final_warning: { label: 'Level 3 \u2014 Drop', className: 'border-red-300 bg-red-100 text-red-800 dark:border-red-800 dark:bg-red-950/60 dark:text-red-300' },
};

function formatUpdated(value) {
  if (!value) return 'Not recorded';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export default function AttendanceWarnings() {
  const { addToast } = useToast();
  const [students, setStudents] = useState([]);
  const [studentQuery, setStudentQuery] = useState('');
  const [studentMenuOpen, setStudentMenuOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeDialog, setFinalizeDialog] = useState(null);
  const [finalizeResult, setFinalizeResult] = useState(null);
  const [finalizeError, setFinalizeError] = useState('');

  useEffect(() => {
    getStudents(1, 200)
      .then(data => setStudents(Array.isArray(data) ? data : (data?.items || [])))
      .catch(err => addToast(err.message, 'error'))
      .finally(() => setLoadingStudents(false));
  }, [addToast]);

  const filteredStudents = useMemo(() => {
    const query = studentQuery.trim().toLowerCase();
    if (!query) return students;
    return students.filter(student =>
      student.full_name.toLowerCase().includes(query) ||
      student.student_id.toLowerCase().includes(query)
    );
  }, [students, studentQuery]);

  const loadReport = async student => {
    setSelectedStudent(student);
    setStudentQuery('');
    setStudentMenuOpen(false);
    setLoadingReport(true);
    setDrafts({});
    try {
      const data = await getStudentAttendanceWarnings(student.id);
      setWarnings(data.warnings || []);
    } catch (err) {
      addToast(err.message, 'error');
      setWarnings([]);
    } finally {
      setLoadingReport(false);
    }
  };

  const changeWarning = (courseId, warningLevel) => {
    setDrafts(current => ({ ...current, [courseId]: warningLevel }));
  };

  const pendingChanges = warnings
    .filter(row => drafts[row.course_id] && drafts[row.course_id] !== row.warning_level)
    .map(row => ({ course_id: row.course_id, warning_level: drafts[row.course_id] }));

  const persistPendingChanges = async () => {
    const result = await updateStudentAttendanceWarnings(selectedStudent.id, pendingChanges);
    setWarnings(result.warnings || []);
    setDrafts({});
    return result;
  };

  const saveChanges = async () => {
    if (!selectedStudent || pendingChanges.length === 0) return;
    setSaving(true);
    try {
      const result = await persistPendingChanges();
      addToast(result.message || 'Warning changes saved');
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const openFinalizeDialog = () => {
    setFinalizeResult(null);
    setFinalizeError('');
    setFinalizeDialog(pendingChanges.length > 0 ? 'unsaved' : 'confirm');
  };

  const runFinalization = async (saveFirst = false) => {
    setFinalizing(true);
    setFinalizeError('');
    try {
      if (saveFirst && pendingChanges.length > 0) {
        await persistPendingChanges();
      }
      const result = await finalizeAttendanceDay();
      setFinalizeResult(result);
      setFinalizeDialog('success');
    } catch (err) {
      console.error('Attendance finalization failed:', err);
      setFinalizeError(err.message || 'Attendance data was not sent to the notification workflow. Please try again.');
      setFinalizeDialog('error');
    } finally {
      setFinalizing(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">Attendance Warning Review</h2>
          <p className="mt-1 text-sm text-muted-foreground">Review and correct active attendance warnings by student.</p>
        </div>
        <Button onClick={openFinalizeDialog} className="gap-2 self-start">
          <CalendarCheck2 className="h-4 w-4" />
          Finalize End of Day
        </Button>
      </div>

      <Card className="overflow-visible">
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Select Student</CardTitle>
          <p className="text-sm text-muted-foreground">Search by student name or ID to view their absence report.</p>
        </CardHeader>
        <CardContent>
          <div className="relative max-w-xl">
            <Search className="pointer-events-none absolute left-3 top-2.5 z-10 h-4 w-4 text-muted-foreground" />
            <Input
              value={studentQuery}
              onChange={event => {
                setStudentQuery(event.target.value);
                setStudentMenuOpen(true);
              }}
              onFocus={() => setStudentMenuOpen(true)}
              placeholder={selectedStudent ? `${selectedStudent.full_name} \u00b7 ${selectedStudent.student_id}` : 'Search students...'}
              className="pl-9 pr-9"
              aria-label="Search and select a student"
              aria-expanded={studentMenuOpen}
            />
            <ChevronDown className="pointer-events-none absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
            {studentMenuOpen && (
              <div className="absolute z-30 mt-2 max-h-64 w-full overflow-auto rounded-md border bg-popover p-1 shadow-lg">
                {loadingStudents ? (
                  <div className="space-y-2 p-2"><Skeleton className="h-10" /><Skeleton className="h-10" /></div>
                ) : filteredStudents.length > 0 ? filteredStudents.map(student => (
                  <button
                    key={student.id}
                    type="button"
                    onClick={() => loadReport(student)}
                    className="flex w-full items-center gap-3 rounded-sm px-3 py-2 text-left hover:bg-accent focus:bg-accent focus:outline-none"
                  >
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted"><UserRound className="h-4 w-4" /></span>
                    <span>
                      <span className="block text-sm font-medium">{student.full_name}</span>
                      <span className="block text-xs text-muted-foreground">{student.student_id}</span>
                    </span>
                  </button>
                )) : (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">No matching students found.</p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {selectedStudent && (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4 border-b bg-muted/20">
            <div>
              <CardTitle>Absence Report &mdash; {selectedStudent.full_name}</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">{selectedStudent.student_id} &middot; Active attendance warnings only</p>
            </div>
            {warnings.length > 0 && <Badge variant="outline">{warnings.length} active</Badge>}
          </CardHeader>

          {loadingReport ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-14 w-full" />)}
            </div>
          ) : warnings.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No attendance warnings"
              description="This student currently has no courses with an active attendance warning."
              className="min-h-64"
            />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      {['Course Code', 'Course Name', 'Current Warning Level', 'Update Warning Level', 'Change Status', 'Last Updated'].map(column => (
                        <th key={column} className="whitespace-nowrap px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {warnings.map(row => {
                      const draft = drafts[row.course_id] ?? row.warning_level;
                      const changed = draft !== row.warning_level;
                      const cleared = changed && draft === 'none';
                      const meta = LEVEL_META[row.warning_level];
                      return (
                        <tr key={row.course_id} className={cleared ? 'bg-emerald-50/60 dark:bg-emerald-950/10' : 'hover:bg-muted/30'}>
                          <td className="whitespace-nowrap px-5 py-4 text-sm font-semibold">{row.course_code}</td>
                          <td className="min-w-48 px-5 py-4 text-sm">{row.course_name}</td>
                          <td className="whitespace-nowrap px-5 py-4"><Badge variant="outline" className={meta.className}>{meta.label}</Badge></td>
                          <td className="min-w-52 px-5 py-4">
                            <Select value={draft} onChange={event => changeWarning(row.course_id, event.target.value)} aria-label={`Update warning for ${row.course_code}`}>
                              {LEVELS.map(level => <option key={level.value} value={level.value}>{level.label}</option>)}
                            </Select>
                          </td>
                          <td className="whitespace-nowrap px-5 py-4">
                            {cleared ? (
                              <Badge variant="success">Warning Cleared</Badge>
                            ) : changed ? (
                              <Badge variant="warning">Pending Update</Badge>
                            ) : (
                              <span className="text-xs font-medium text-muted-foreground">No change</span>
                            )}
                          </td>
                          <td className="whitespace-nowrap px-5 py-4 text-sm text-muted-foreground">{formatUpdated(row.last_updated)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-col gap-3 border-t bg-muted/10 p-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="flex items-center gap-2 text-xs text-muted-foreground">
                  <AlertTriangle className="h-4 w-4" /> Cleared warnings remain visible here until changes are saved.
                </p>
                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <Button variant="outline" onClick={() => setDrafts({})} disabled={pendingChanges.length === 0} className="gap-2">
                    <RotateCcw className="h-4 w-4" /> Reset Changes
                  </Button>
                  <Button onClick={saveChanges} isLoading={saving} disabled={pendingChanges.length === 0}>
                    Save Changes{pendingChanges.length > 0 ? ` (${pendingChanges.length})` : ''}
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>
      )}

      {finalizeDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation">
          <div className="w-full max-w-lg rounded-lg border bg-card p-6 text-card-foreground shadow-xl" role="dialog" aria-modal="true" aria-labelledby="finalize-dialog-title">
            {finalizeDialog === 'success' ? (
              <div className="space-y-5">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-6 w-6 text-emerald-500" />
                  <div>
                    <h3 id="finalize-dialog-title" className="text-lg font-semibold">End-of-Day Processing Complete</h3>
                    <p className="mt-1 text-sm text-muted-foreground">The attendance snapshot was sent to the notification workflow.</p>
                  </div>
                </div>
                <dl className="grid grid-cols-1 gap-3 rounded-md bg-muted/50 p-4 text-sm sm:grid-cols-2">
                  <div><dt className="text-muted-foreground">Batch ID</dt><dd className="mt-1 break-all font-mono text-xs">{finalizeResult?.batch_id}</dd></div>
                  <div><dt className="text-muted-foreground">Finalized at</dt><dd className="mt-1">{formatUpdated(finalizeResult?.finalized_at)}</dd></div>
                  <div><dt className="text-muted-foreground">Students processed</dt><dd className="mt-1 font-semibold">{finalizeResult?.students_processed}</dd></div>
                  <div><dt className="text-muted-foreground">Course records sent</dt><dd className="mt-1 font-semibold">{finalizeResult?.course_records_sent}</dd></div>
                </dl>
                <div className="flex justify-end"><Button onClick={() => setFinalizeDialog(null)}>Done</Button></div>
              </div>
            ) : finalizeDialog === 'error' ? (
              <div className="space-y-5">
                <div className="flex items-start gap-3">
                  <XCircle className="mt-0.5 h-6 w-6 text-red-500" />
                  <div>
                    <h3 id="finalize-dialog-title" className="text-lg font-semibold">End-of-Day Processing Failed</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{finalizeError}</p>
                    <p className="mt-2 text-sm text-muted-foreground">Your saved attendance data has not been deleted or reset.</p>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setFinalizeDialog(null)}>Close</Button>
                  <Button onClick={() => runFinalization(pendingChanges.length > 0)} isLoading={finalizing}>Retry</Button>
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <h3 id="finalize-dialog-title" className="text-lg font-semibold">Finalize End of Day?</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {finalizeDialog === 'unsaved'
                      ? 'You have unsaved attendance changes. Save and finalize them?'
                      : 'This will send the complete saved attendance-warning snapshot to the notification workflow.'}
                  </p>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setFinalizeDialog(null)} disabled={finalizing}>Cancel</Button>
                  <Button onClick={() => runFinalization(finalizeDialog === 'unsaved')} isLoading={finalizing}>
                    {finalizeDialog === 'unsaved' ? 'Save and Finalize' : 'Finalize End of Day'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
