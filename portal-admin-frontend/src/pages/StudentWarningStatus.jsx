import React, { useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  EyeOff,
  Search,
  ShieldAlert,
  User,
  WifiOff,
} from "lucide-react";
import { getStudentWarningStatus } from "../api";
import { Button } from "../components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";

const WARNING_LEVELS = [
  { level: 0, label: "Good",      color: "bg-emerald-500" },
  { level: 1, label: "Warning 1", color: "bg-yellow-400"  },
  { level: 2, label: "Warning 2", color: "bg-orange-500"  },
  { level: 3, label: "Drop",      color: "bg-red-500"     },
];

function formatDateTime(iso) {
  if (!iso) return null;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

function WarningBar({ level }) {
  const clampedLevel = Math.max(0, Math.min(3, level ?? 0));
  const config = WARNING_LEVELS[clampedLevel];

  return (
    <div className="space-y-2">
      <div className="flex gap-1.5 h-2.5">
        {WARNING_LEVELS.map((seg) => (
          <div
            key={seg.level}
            className={`flex-1 rounded-full transition-all duration-500 ${
              seg.level <= clampedLevel ? seg.color : "bg-border"
            }`}
          />
        ))}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Warning Level{" "}
          <span className="font-semibold text-foreground">{clampedLevel}</span> of 3
        </span>
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            clampedLevel === 0
              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
              : clampedLevel === 1
              ? "bg-yellow-400/15 text-yellow-700 dark:text-yellow-400"
              : clampedLevel === 2
              ? "bg-orange-500/15 text-orange-700 dark:text-orange-400"
              : "bg-red-500/15 text-red-700 dark:text-red-400"
          }`}
        >
          {config.label}
        </span>
      </div>
    </div>
  );
}

function SeenBadge({ notification }) {
  if (!notification) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <EyeOff className="h-3.5 w-3.5" />
        No notification sent
      </span>
    );
  }
  if (notification.opened) {
    return (
      <div className="space-y-0.5">
        <Badge variant="success" className="gap-1">
          <Eye className="h-3 w-3" />
          Seen
        </Badge>
        {notification.opened_at && (
          <p className="text-[11px] text-muted-foreground pl-0.5">
            {formatDateTime(notification.opened_at)}
            {notification.open_count > 1 && (
              <span className="ml-1 text-muted-foreground/70">
                &middot; {notification.open_count}&times;
              </span>
            )}
          </p>
        )}
      </div>
    );
  }
  return (
    <div className="space-y-0.5">
      <Badge variant="secondary" className="gap-1 text-muted-foreground">
        <EyeOff className="h-3 w-3" />
        Not seen yet
      </Badge>
      {notification.sent_at && (
        <p className="text-[11px] text-muted-foreground pl-0.5">
          Sent {formatDateTime(notification.sent_at)}
        </p>
      )}
    </div>
  );
}

function CourseWarningCard({ course }) {
  const level = course.current_warning_level ?? 0;
  const notif = course.last_notification;

  return (
    <div className="rounded-lg border bg-card p-4 sm:p-5 space-y-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-mono text-muted-foreground">{course.course_id}</p>
          <h3 className="font-semibold text-sm mt-0.5 leading-snug">{course.course_name}</h3>
        </div>
        <div className="shrink-0">
          <SeenBadge notification={notif} />
        </div>
      </div>

      <WarningBar level={level} />

      {notif && (
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground border-t pt-3">
          <Clock className="h-3.5 w-3.5 shrink-0" />
          <span>
            Last notified at level <strong>{notif.notified_level}</strong>
            {notif.sent_at && <> &middot; {formatDateTime(notif.sent_at)}</>}
          </span>
        </div>
      )}
    </div>
  );
}

function ResultSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-20 w-full rounded-lg" />
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-40 w-full rounded-lg" />
      ))}
    </div>
  );
}

export default function StudentWarningStatus() {
  const [studentId, setStudentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const inputRef = useRef(null);

  const trimmedId = studentId.trim();

  const handleCheck = async () => {
    if (!trimmedId) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setNotFound(false);

    try {
      const data = await getStudentWarningStatus(trimmedId);
      if (!data.courses || data.courses.length === 0) {
        setNotFound(true);
        setResult(data);
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err.message || "Could not reach the warning status service. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleCheck();
  };

  const handleClear = () => {
    setStudentId("");
    setResult(null);
    setError(null);
    setNotFound(false);
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-orange-500" />
          Student Warning Status
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Look up a student&apos;s current attendance warning level across all enrolled courses.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Look Up Student</CardTitle>
          <p className="text-sm text-muted-foreground">Enter the student ID and press Check.</p>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 max-w-xl">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="student-warning-id-input"
                ref={inputRef}
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. 12345"
                className="pl-9"
                aria-label="Student ID"
              />
            </div>
            <Button
              id="student-warning-check-btn"
              onClick={handleCheck}
              disabled={!trimmedId || loading}
              isLoading={loading}
            >
              Check
            </Button>
            {(result || error || notFound) && (
              <Button variant="outline" onClick={handleClear}>
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {loading && <ResultSkeleton />}

      {error && !loading && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-5 flex items-start gap-3">
          <WifiOff className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-sm text-destructive">Could not fetch warning status</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
        </div>
      )}

      {notFound && !loading && (
        <div className="rounded-lg border bg-card p-10 flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
          <div>
            <p className="font-semibold">No records found for this student ID</p>
            <p className="text-sm text-muted-foreground mt-1">
              No warning data was returned for student ID{" "}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">{trimmedId}</code>.
              Check the ID and try again.
            </p>
          </div>
        </div>
      )}

      {result && !notFound && !loading && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 px-1">
            <div className="h-9 w-9 rounded-full bg-muted flex items-center justify-center shrink-0">
              <User className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="font-semibold text-sm leading-none">{result.student_name}</p>
              <p className="text-xs text-muted-foreground mt-1">ID: {result.student_id}</p>
            </div>
            <Badge variant="outline" className="ml-auto">
              {result.courses.length} course{result.courses.length !== 1 ? "s" : ""}
            </Badge>
          </div>

          {result.courses.every((c) => (c.current_warning_level ?? 0) === 0) && (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              All courses are at Level 0 &mdash; no active warnings.
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {result.courses.map((course) => (
              <CourseWarningCard key={course.course_id} course={course} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
