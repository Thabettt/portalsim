import React, { useEffect, useState } from 'react';
import { useToast } from '../hooks/useToast';
import { 
  getSystemState, 
  getWebhookLogStats, 
  getSchedulerJobs, 
  seedData, 
  resetDatabase,
  simulateDayEnd,
  simulatePaymentReminders,
  simulateDeadlineCheck,
  runSchedulerJob
} from '../api';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import ConfirmButton from '../components/ConfirmButton';
import { 
  Users, BookOpen, CreditCard, CalendarX2, Briefcase, 
  CheckSquare, Activity, AlertTriangle, Clock, Play, CalendarClock
} from 'lucide-react';

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-4 rounded-full" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-1/3 mb-1" />
      </CardContent>
    </Card>
  );
}

function Stat({ title, value, icon: Icon, className }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className={`h-4 w-4 text-muted-foreground ${className}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState(null);
  const [webhookStats, setWebhookStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sysState, whStats, schedJobs] = await Promise.all([
        getSystemState(),
        getWebhookLogStats(),
        getSchedulerJobs()
      ]);
      setState(sysState);
      setWebhookStats(whStats);
      setJobs(schedJobs);
    } catch (err) {
      addToast(err.message || "Failed to load dashboard data", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAction = async (actionFn, successMsg) => {
    try {
      setActionLoading(true);
      const res = await actionFn();
      addToast(successMsg || (res?.message) || "Action completed successfully");
      await fetchData();
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">System Overview & Controls</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => handleAction(seedData, "Database seeded successfully")}
            disabled={actionLoading || loading}
            isLoading={actionLoading}
          >
            Seed Demo Data
          </Button>
          <ConfirmButton
            onConfirm={() => handleAction(resetDatabase, "Database reset successfully")}
            confirmText="Wipe all data?"
          >
            <Button variant="destructive" disabled={actionLoading || loading}>
              Reset Database
            </Button>
          </ConfirmButton>
        </div>
      </div>

      {/* System State Stats */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight mb-4 text-foreground">Entities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {loading ? (
            Array(6).fill(0).map((_, i) => <StatCardSkeleton key={i} />)
          ) : (
            <>
              <Stat title="Students" value={state?.users} icon={Users} className="text-blue-500" />
              <Stat title="Courses" value={state?.courses} icon={BookOpen} className="text-purple-500" />
              <Stat title="Payments" value={state?.payments} icon={CreditCard} className="text-emerald-500" />
              <Stat title="Attendances" value={state?.attendances} icon={CalendarX2} className="text-orange-500" />
              <Stat title="Internships" value={state?.internships} icon={Briefcase} className="text-indigo-500" />
              <Stat title="Assessments" value={state?.assessments} icon={CheckSquare} className="text-teal-500" />
            </>
          )}
        </div>
      </section>

      {/* Webhook Health Stats */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight mb-4 text-foreground">Webhook Delivery Health</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {loading ? (
            Array(3).fill(0).map((_, i) => <StatCardSkeleton key={i} />)
          ) : (
            <>
              <Stat title="Total Logs" value={state?.webhook_logs} icon={Activity} />
              <Stat title="Failed Deliveries" value={webhookStats?.failed || 0} icon={AlertTriangle} className="text-destructive" />
              <Stat title="Pending / Retrying" value={(webhookStats?.pending || 0) + (webhookStats?.retrying || 0)} icon={Clock} className="text-amber-500" />
            </>
          )}
        </div>
      </section>

      {/* Quick Actions & Scheduled Jobs */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <h2 className="text-lg font-semibold tracking-tight text-foreground">Quick Simulations</h2>
          <Card>
            <CardContent className="p-4 space-y-2">
              <Button
                variant="outline"
                className="w-full justify-between"
                onClick={() => handleAction(simulateDayEnd)}
                disabled={actionLoading || loading}
              >
                Day-End Attendance
                <Play className="w-4 h-4 text-muted-foreground" />
              </Button>
              <Button
                variant="outline"
                className="w-full justify-between"
                onClick={() => handleAction(simulatePaymentReminders)}
                disabled={actionLoading || loading}
              >
                Payment Reminders
                <Play className="w-4 h-4 text-muted-foreground" />
              </Button>
              <Button
                variant="outline"
                className="w-full justify-between"
                onClick={() => handleAction(simulateDeadlineCheck)}
                disabled={actionLoading || loading}
              >
                Deadline Check
                <Play className="w-4 h-4 text-muted-foreground" />
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold tracking-tight text-foreground">Scheduled Jobs</h2>
          <Card className="overflow-hidden">
            {loading ? (
              <div className="p-6 space-y-4">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : jobs && jobs.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Job Name</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Schedule</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Next Run</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Action</th>
                    </tr>
                  </thead>
                  <tbody className="bg-card divide-y divide-border">
                    {jobs.map((job) => (
                      <tr key={job.id} className="hover:bg-muted/50 transition-colors">
                        <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-foreground">{job.name || job.id}</td>
                        <td className="px-6 py-3 whitespace-nowrap text-sm text-muted-foreground">
                           {job.trigger_type === 'cron' ? job.expression : job.trigger_type}
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap text-sm text-muted-foreground">
                          {job.next_run_time ? new Date(job.next_run_time).toLocaleString() : 'N/A'}
                        </td>
                        <td className="px-6 py-3 whitespace-nowrap text-right text-sm">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleAction(() => runSchedulerJob(job.id), `Job ${job.id} ran successfully`)}
                            disabled={actionLoading}
                            className="h-8"
                          >
                            <Play className="w-3.5 h-3.5 mr-1.5" /> Run
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                icon={CalendarClock}
                title="No Scheduled Jobs"
                description="There are no scheduled jobs registered in the system."
              />
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}
