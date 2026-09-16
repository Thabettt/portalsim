import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CalendarPlus, Database, FlaskConical, RotateCcw, Search } from 'lucide-react';
import {
  getSimStatus,
  getSimStudent,
  resetSimulator,
  seedSimulator,
  simulateNextDay,
} from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';

const LEVEL_META = [
  { key: '0', label: 'Level 0 \u2014 Good', className: 'border-emerald-300 bg-emerald-100 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' },
  { key: '1', label: 'Level 1 \u2014 Warning 1', className: 'border-yellow-300 bg-yellow-100 text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950/60 dark:text-yellow-300' },
  { key: '2', label: 'Level 2 \u2014 Warning 2', className: 'border-orange-300 bg-orange-100 text-orange-800 dark:border-orange-800 dark:bg-orange-950/60 dark:text-orange-300' },
  { key: '3', label: 'Level 3 \u2014 Drop', className: 'border-red-300 bg-red-100 text-red-800 dark:border-red-800 dark:bg-red-950/60 dark:text-red-300' },
];

const BAR_COLORS = {
  0: 'bg-emerald-500',
  1: 'bg-yellow-500',
  2: 'bg-orange-500',
  3: 'bg-red-500',
};

function DistributionBar({ distribution }) {
  const total = Object.values(distribution || {}).reduce((sum, n) => sum + n, 0) || 1;
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full border bg-muted">
        {['0', '1', '2', '3'].map(key => {
          const value = distribution?.[key] || 0;
          const pct = (value / total) * 100;
          if (!pct) return null;
          return (
            <div
              key={key}
              className={BAR_COLORS[key]}
              style={{ width: `${pct}%` }}
              title={`${LEVEL_META[Number(key)].label}: ${value} (${pct.toFixed(1)}%)`}
            />
          );
        })}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {LEVEL_META.map(meta => {
          const value = distribution?.[meta.key] || 0;
          return (
            <div key={meta.key} className="rounded-md border bg-card p-2">
              <div className="text-xs text-muted-foreground">{meta.label}</div>
              <div className="mt-0.5 text-lg font-semibold tabular-nums">{value.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">{((value / total) * 100).toFixed(1)}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AttendanceSimulator() {
  const { addToast } = useToast();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [chunkSize, setChunkSize] = useState(200);
  const [lastRun, setLastRun] = useState(null);
  const [preview, setPreview] = useState(null);
  const [lookupId, setLookupId] = useState('');
  const [lookup, setLookup] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await getSimStatus());
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { refresh(); }, [refresh]);

  const runNextDay = async () => {
    setBusy('day');
    try {
      const result = await simulateNextDay({ chunkSize: Number(chunkSize) || 200, previewChunk: 1 });
      setLastRun(result.summary);
      setPreview(result.chunk_preview || null);
      addToast(
        `Day ${result.summary.day_number}: ${result.summary.changed_count} changed, ` +
        `${result.summary.new_drops} new drops, ${result.summary.chunk_count} chunks`,
        'success'
      );
      await refresh();
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setBusy('');
    }
  };

  const runSeed = async (force) => {
    setBusy('seed');
    try {
      const result = await seedSimulator({ students: 3000, force });
      addToast(result.message || 'Seeded.', 'success');
      setLastRun(null);
      setPreview(null);
      await refresh();
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setBusy('');
    }
  };

  const runReset = async () => {
    setBusy('reset');
    try {
      await resetSimulator();
      addToast('Warning levels reset to day 0. Enrollment preserved.', 'success');
      setLastRun(null);
      setPreview(null);
      await refresh();
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setBusy('');
    }
  };

  const runLookup = async e => {
    e.preventDefault();
    if (!lookupId.trim()) return;
    try {
      setLookup(await getSimStudent(lookupId.trim()));
    } catch (err) {
      setLookup(null);
      addToast(err.message, 'error');
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

  if (!status) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="Simulator unavailable"
        description="The dev simulator endpoints only respond when the backend runs with DEBUG enabled."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <FlaskConical className="h-6 w-6 text-primary" />
            Attendance Simulator
            <Badge className="border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
              Dev only
            </Badge>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Click through simulated days and watch warning levels evolve. Enrollment stays fixed; only levels change.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={runNextDay} isLoading={busy === 'day'} className="gap-2">
            <CalendarPlus className="h-4 w-4" />
            Simulate Next Day
          </Button>
          <Button variant="outline" onClick={runReset} isLoading={busy === 'reset'} className="gap-2">
            <RotateCcw className="h-4 w-4" />
            Reset to Day 0
          </Button>
          <Button variant="outline" onClick={() => runSeed(true)} isLoading={busy === 'seed'} className="gap-2">
            <Database className="h-4 w-4" />
            Regenerate Seed
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: 'Simulated day', value: status.day_number },
          { label: 'Students', value: status.students_count?.toLocaleString() },
          { label: 'Student-course pairs', value: status.course_records_count?.toLocaleString() },
          { label: 'Courses in catalog', value: status.course_catalog_size },
        ].map(stat => (
          <Card key={stat.label}>
            <CardContent className="p-4">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">{stat.label}</div>
              <div className="mt-1 text-2xl font-bold tabular-nums">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Current warning level distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <DistributionBar distribution={status.level_distribution} />
          <p className="mt-4 text-xs text-muted-foreground">
            All notifications route to <span className="font-mono">{status.test_inbox}</span> via +tag aliases.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Last simulated day</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <label htmlFor="chunk-size" className="text-sm text-muted-foreground">Chunk size</label>
              <Input
                id="chunk-size"
                type="number"
                min={1}
                value={chunkSize}
                onChange={e => setChunkSize(e.target.value)}
                className="w-28"
              />
            </div>
            {lastRun ? (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div><dt className="text-muted-foreground">Day</dt><dd className="font-semibold">{lastRun.day_number}</dd></div>
                <div><dt className="text-muted-foreground">Chunks</dt><dd className="font-semibold">{lastRun.chunk_count}</dd></div>
                <div><dt className="text-muted-foreground">Changed</dt><dd className="font-semibold">{lastRun.changed_count?.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">Unchanged</dt><dd className="font-semibold">{lastRun.unchanged_count?.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">New drops (L3)</dt><dd className="font-semibold text-red-600 dark:text-red-400">{lastRun.new_drops?.toLocaleString()}</dd></div>
                <div><dt className="text-muted-foreground">Same-day repeats</dt><dd className="font-semibold">{lastRun.repeat_records?.toLocaleString()}</dd></div>
                <div className="col-span-2">
                  <dt className="text-muted-foreground">finalize_id</dt>
                  <dd className="mt-0.5 break-all font-mono text-xs">{lastRun.finalize_id}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">
                Press <span className="font-medium">Simulate Next Day</span> to generate a day.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Chunk 1 preview</CardTitle>
          </CardHeader>
          <CardContent>
            {preview ? (
              <pre className="max-h-72 overflow-auto rounded-md border bg-muted/50 p-3 text-xs">
                {JSON.stringify(preview, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-muted-foreground">No chunk generated yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Inspect a student</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <form onSubmit={runLookup} className="flex flex-wrap gap-2">
            <Input
              value={lookupId}
              onChange={e => setLookupId(e.target.value)}
              placeholder="STU-2024-0001"
              className="max-w-xs font-mono"
            />
            <Button type="submit" variant="outline" className="gap-2">
              <Search className="h-4 w-4" />
              Look up
            </Button>
          </form>
          {lookup && (
            <div className="rounded-md border p-3">
              <div className="text-sm font-semibold">{lookup.student_name}</div>
              <div className="font-mono text-xs text-muted-foreground">{lookup.recipient}</div>
              <div className="mt-3 space-y-1.5">
                {lookup.courses.map(course => {
                  const meta = LEVEL_META[course.warning_level];
                  return (
                    <div key={course.course_id} className="flex items-center justify-between gap-3 text-sm">
                      <span>
                        <span className="font-mono text-xs">{course.course_id}</span>
                        <span className="ml-2 text-muted-foreground">{course.course_name}</span>
                      </span>
                      <Badge className={meta.className}>{meta.label}</Badge>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {status.history?.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle>Day history</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-2 pr-4">Day</th>
                  <th className="py-2 pr-4">Changed</th>
                  <th className="py-2 pr-4">New drops</th>
                  <th className="py-2 pr-4">Repeats</th>
                  <th className="py-2 pr-4">Chunks</th>
                  <th className="py-2">L0 / L1 / L2 / L3</th>
                </tr>
              </thead>
              <tbody>
                {[...status.history].reverse().map(entry => (
                  <tr key={entry.finalize_id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-semibold tabular-nums">{entry.day_number}</td>
                    <td className="py-2 pr-4 tabular-nums">{entry.changed_count?.toLocaleString()}</td>
                    <td className="py-2 pr-4 tabular-nums text-red-600 dark:text-red-400">{entry.new_drops?.toLocaleString()}</td>
                    <td className="py-2 pr-4 tabular-nums">{entry.repeat_records}</td>
                    <td className="py-2 pr-4 tabular-nums">{entry.chunk_count}</td>
                    <td className="py-2 font-mono text-xs tabular-nums">
                      {['0', '1', '2', '3'].map(k => entry.level_distribution?.[k] ?? 0).join(' / ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <p className="flex items-start gap-2 text-xs text-muted-foreground">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        This page writes only to the JSON seed files under <span className="font-mono">seeds/</span>. It never mutates the
        portal database and never calls the real finalize endpoint.
      </p>
    </div>
  );
}
