import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Clock,
  RefreshCw,
  Send,
  XCircle,
} from 'lucide-react';
import {
  finalizeTerm,
  getSimPoint,
  getTerm,
  getTermDay,
  getTermFinalizeProgress,
  previewTermFinalize,
  regenerateTerm,
  resendTermFailedChunks,
} from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

// Poll cadence while a finalize run is still sending chunks.
const PROGRESS_POLL_MS = 1000;

const LEVEL_VARIANTS = { 0: 'success', 1: 'warning', 2: 'warning', 3: 'danger' };
const LEVEL_LABELS = { 0: 'Good', 1: 'Warning 1', 2: 'Warning 2', 3: 'Drop' };

function TermPointPicker({ label, weeks, days, week, weekday, onWeek, onWeekday, disabled }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-foreground">{label} &mdash; week</label>
        <div className="flex flex-wrap gap-1.5">
          {weeks.map(w => (
            <button
              key={w}
              type="button"
              disabled={disabled}
              onClick={() => onWeek(w)}
              className={[
                'h-8 w-10 rounded-md border text-xs font-semibold transition-colors',
                'disabled:cursor-not-allowed disabled:opacity-50',
                w === week
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-input bg-background hover:bg-accent hover:text-accent-foreground',
              ].join(' ')}
            >
              {w}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-foreground">{label} &mdash; day</label>
        <div className="flex flex-wrap gap-1.5">
          {days.map(d => (
            <button
              key={d.weekday}
              type="button"
              disabled={disabled}
              onClick={() => onWeekday(d.weekday)}
              className={[
                'h-8 rounded-md border px-3 text-xs font-semibold transition-colors',
                'disabled:cursor-not-allowed disabled:opacity-50',
                d.weekday === weekday
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-input bg-background hover:bg-accent hover:text-accent-foreground',
              ].join(' ')}
            >
              {d.weekday_name.slice(0, 3)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChunkProgress({ progress, onResend, resending }) {
  if (!progress) return null;

  const total = progress.chunk_count || 0;
  const sent = progress.chunks_sent || 0;
  const failed = progress.chunks_failed || 0;
  const pct = total ? Math.round((sent / total) * 100) : 0;
  const failedChunks = (progress.chunks || []).filter(c => c.status === 'failed');
  // A 400 is a validation failure: resending the identical body cannot help.
  const resendable = failedChunks.filter(c => c.retryable !== false);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold tabular-nums">
          {sent} / {total} chunks sent
          {failed > 0 && (
            <span className="ml-2 text-red-600 dark:text-red-400">({failed} failed)</span>
          )}
          {progress.duplicates > 0 && (
            <span className="ml-2 text-muted-foreground">({progress.duplicates} duplicate)</span>
          )}
        </div>
        <Badge
          variant={
            progress.status === 'completed'
              ? 'success'
              : progress.status === 'partial'
                ? 'danger'
                : 'secondary'
          }
        >
          {progress.status === 'running' && <Clock className="mr-1 h-3 w-3" />}
          {progress.status === 'completed' && <CheckCircle2 className="mr-1 h-3 w-3" />}
          {progress.status === 'partial' && <XCircle className="mr-1 h-3 w-3" />}
          {progress.status}
        </Badge>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={failed ? 'h-full bg-amber-500' : 'h-full bg-emerald-500'}
          style={{ width: `${pct}%` }}
        />
      </div>

      <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <div><dt className="text-muted-foreground">Students</dt><dd className="font-semibold tabular-nums">{progress.students_processed?.toLocaleString()}</dd></div>
        <div><dt className="text-muted-foreground">Course records</dt><dd className="font-semibold tabular-nums">{progress.course_records_sent?.toLocaleString()}</dd></div>
        <div><dt className="text-muted-foreground">Chunk size</dt><dd className="font-semibold tabular-nums">{progress.chunk_size}</dd></div>
        <div><dt className="text-muted-foreground">today_date</dt><dd className="font-mono font-semibold">{progress.today_date}</dd></div>
      </dl>

      {progress.finalize_id && (
        <div className="text-xs">
          <span className="text-muted-foreground">finalize_id </span>
          <span className="break-all font-mono">{progress.finalize_id}</span>
        </div>
      )}

      {progress.message && (
        <p className="text-xs text-muted-foreground">{progress.message}</p>
      )}

      {failedChunks.length > 0 && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950/40">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs font-semibold text-red-800 dark:text-red-300">
              Failed after retries: chunk {failedChunks.map(c => c.chunk_index).join(', ')}
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={onResend}
              isLoading={resending}
              disabled={resendable.length === 0}
            >
              Resend failed
            </Button>
          </div>
          <ul className="mt-2 space-y-1">
            {failedChunks.map(c => (
              <li key={c.chunk_index} className="font-mono text-[11px] text-red-700 dark:text-red-400">
                #{c.chunk_index} &mdash; {c.status_code || 'network'} &mdash; {c.error}
                {c.retryable === false && ' (validation error, not retryable)'}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function TermSimulator() {
  const { addToast } = useToast();
  const [term, setTerm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  // Selected day being inspected.
  const [week, setWeek] = useState(1);
  const [weekday, setWeekday] = useState(6); // Sunday
  const [day, setDay] = useState(null);

  // "Send up to" point, kept separate so you can browse one day and finalize
  // through another.
  const [sendWeek, setSendWeek] = useState(1);
  const [sendWeekday, setSendWeekday] = useState(6);

  const [chunkSize, setChunkSize] = useState(200);
  const [preview, setPreview] = useState(null);
  const [progress, setProgress] = useState(null);
  const [resending, setResending] = useState(false);
  const pollRef = useRef(null);

  const weeks = useMemo(() => term?.weeks || [], [term]);
  const days = useMemo(() => term?.teaching_weekdays || [], [term]);

  const load = useCallback(async () => {
    try {
      const [termData, point] = await Promise.all([getTerm(), getSimPoint()]);
      setTerm(termData);
      setWeek(point.week_number);
      setWeekday(point.weekday);
      setSendWeek(point.week_number);
      setSendWeekday(point.weekday);
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  // Load the day view whenever the inspected point changes.
  useEffect(() => {
    if (!term) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getTermDay(week, weekday);
        if (!cancelled) setDay(data);
      } catch (err) {
        if (!cancelled) addToast(err.message, 'error');
      }
    })();
    return () => { cancelled = true; };
  }, [term, week, weekday, addToast]);

  // Poll chunk progress while a run is in flight; stop as soon as it settles.
  useEffect(() => {
    if (!progress?.finalize_id || progress.status !== 'running') return undefined;
    pollRef.current = setInterval(async () => {
      try {
        setProgress(await getTermFinalizeProgress(progress.finalize_id));
      } catch {
        /* transient poll failure is not worth a toast on every tick */
      }
    }, PROGRESS_POLL_MS);
    return () => clearInterval(pollRef.current);
  }, [progress?.finalize_id, progress?.status]);

  const sendPointLabel = useMemo(() => {
    const name = days.find(d => d.weekday === sendWeekday)?.weekday_name || '';
    return `Week ${sendWeek}, ${name}`;
  }, [days, sendWeek, sendWeekday]);

  const runPreview = async () => {
    setBusy('preview');
    try {
      const result = await previewTermFinalize({
        weekNumber: sendWeek,
        weekday: sendWeekday,
        chunkSize: Number(chunkSize) || 200,
      });
      setPreview(result);
      addToast(
        `Preview: ${result.summary.chunk_count} chunks, ` +
        `${result.summary.sessions_count.toLocaleString()} sessions through ${result.summary.today_date}`,
        'success'
      );
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setBusy('');
    }
  };

  const runFinalize = async () => {
    setBusy('finalize');
    try {
      const result = await finalizeTerm({
        weekNumber: sendWeek,
        weekday: sendWeekday,
        chunkSize: Number(chunkSize) || undefined,
      });
      setProgress(result.progress);
      addToast(
        `Finalizing ${result.summary.chunk_count} chunks through ${result.summary.today_date}. ` +
        'Sending in the background.',
        'success'
      );
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setBusy('');
    }
  };

  const runResend = async () => {
    if (!progress?.finalize_id) return;
    setResending(true);
    try {
      setProgress(await resendTermFailedChunks(progress.finalize_id));
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setResending(false);
    }
  };

  const runRegenerate = async () => {
    setBusy('regen');
    try {
      const result = await regenerateTerm({});
      addToast(result.message || 'Term regenerated.', 'success');
      setPreview(null);
      setProgress(null);
      await load();
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setBusy('');
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!term) {
    return (
      <EmptyState
        icon={CalendarDays}
        title="Term simulator unavailable"
        description="The dev simulator endpoints only respond when the backend runs with DEBUG enabled."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <CalendarDays className="h-6 w-6 text-primary" />
            Term Simulator
            <Badge variant="warning">Dev only</Badge>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Fixed 12-week term, Sunday&ndash;Thursday. Slot days are randomised once when the term is
            generated, never on page load.
          </p>
        </div>
        <Button variant="outline" onClick={runRegenerate} isLoading={busy === 'regen'} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Regenerate term
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Pick a day</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <TermPointPicker
            label="Inspect"
            weeks={weeks}
            days={days}
            week={week}
            weekday={weekday}
            onWeek={setWeek}
            onWeekday={setWeekday}
          />
          {day && (
            <div className="rounded-md border bg-muted/30 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold">
                  {day.weekday_name}, Week {day.week_number}
                  <span className="ml-2 font-mono text-xs text-muted-foreground">{day.date}</span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {day.session_count} session{day.session_count === 1 ? '' : 's'}
                </span>
              </div>

              {day.courses.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  No courses have a slot on this day.
                </p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="py-2 pr-4">Course</th>
                        <th className="py-2 pr-4">Credits</th>
                        <th className="py-2">Slots today</th>
                      </tr>
                    </thead>
                    <tbody>
                      {day.courses.map(course => (
                        <tr key={course.course_id} className="border-b last:border-0">
                          <td className="py-2 pr-4">
                            <span className="font-mono text-xs">{course.course_id}</span>
                            <span className="ml-2 text-muted-foreground">{course.course_name}</span>
                          </td>
                          <td className="py-2 pr-4 tabular-nums">{course.credit_hours}</td>
                          <td className="py-2">
                            <div className="flex flex-wrap gap-1.5">
                              {course.sessions.map(s => (
                                <Badge key={`${s.slot}-${s.session_type}`} variant="secondary">
                                  Slot {s.slot} &middot; {s.session_type} &middot; {s.duration}m
                                </Badge>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Finalize &mdash; send up to</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <TermPointPicker
            label="Send through"
            weeks={weeks}
            days={days}
            week={sendWeek}
            weekday={sendWeekday}
            onWeek={setSendWeek}
            onWeekday={setSendWeekday}
            disabled={busy === 'finalize'}
          />

          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <label htmlFor="chunk-size" className="text-xs font-medium text-foreground">
                Chunk size
              </label>
              <Input
                id="chunk-size"
                type="number"
                min={1}
                value={chunkSize}
                onChange={e => setChunkSize(e.target.value)}
                className="w-28"
              />
            </div>
            <Button variant="outline" onClick={runPreview} isLoading={busy === 'preview'}>
              Preview payload
            </Button>
            <Button onClick={runFinalize} isLoading={busy === 'finalize'} className="gap-2">
              <Send className="h-4 w-4" />
              Finalize {sendPointLabel}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            Only sessions dated on or before <span className="font-medium">{sendPointLabel}</span> are
            included. Chunks are sent in the background, at most 5 in flight, each retried 3 times
            with 2s / 4s / 8s backoff.
          </p>
        </CardContent>
      </Card>

      {progress && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Submission progress</CardTitle>
          </CardHeader>
          <CardContent>
            <ChunkProgress progress={progress} onResend={runResend} resending={resending} />
          </CardContent>
        </Card>
      )}

      {preview && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Payload summary</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div><dt className="text-muted-foreground">today_date</dt><dd className="font-mono font-semibold">{preview.summary.today_date}</dd></div>
                <div><dt className="text-muted-foreground">Chunks</dt><dd className="font-semibold tabular-nums">{preview.summary.chunk_count}</dd></div>
                <div><dt className="text-muted-foreground">Students</dt><dd className="font-semibold tabular-nums">{preview.summary.students_count?.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">Course records</dt><dd className="font-semibold tabular-nums">{preview.summary.course_records_count?.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">Sessions</dt><dd className="font-semibold tabular-nums">{preview.summary.sessions_count?.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">Absences</dt><dd className="font-semibold tabular-nums">{preview.summary.absences_count?.toLocaleString()}</dd></div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                {['0', '1', '2', '3'].map(key => (
                  <Badge key={key} variant={LEVEL_VARIANTS[key]}>
                    {LEVEL_LABELS[key]}: {preview.summary.level_distribution?.[key]?.toLocaleString() ?? 0}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Chunk preview</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-96 overflow-auto rounded-md border bg-muted/50 p-3 text-xs">
                {JSON.stringify(preview.chunk_preview, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </div>
      )}

      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        &ldquo;Today&rdquo; here is the simulated point you have stepped to, not the real calendar
        date. Every chunk carries it as <span className="font-mono">today_date</span>, and n8n rejects
        a chunk holding any session dated after it.
      </p>
    </div>
  );
}
