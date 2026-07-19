import React, { useState, useEffect, useCallback } from 'react';
import { getWebhookLogs, retryWebhookLog } from '../api';
import { useToast } from '../hooks/useToast';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import { Select } from '../components/ui/Select';
import { EmptyState } from '../components/ui/EmptyState';
import Pagination from '../components/Pagination';
import { RefreshCw, ChevronDown, ChevronRight, Activity } from 'lucide-react';

const EVENT_TYPES = [
  "attendance_alert",
  "payment_reminder",
  "deadline_reminder",
  "grade_published",
  "internship_status_update",
  "attendance_marked",
  "payment_status_change"
];

export default function WebhookLog() {
  const { addToast } = useToast();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [expandedLogId, setExpandedLogId] = useState(null);
  const [isRetrying, setIsRetrying] = useState({});
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const fetchLogs = useCallback(async (pageNum = 1, eventType = eventTypeFilter, isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      const res = await getWebhookLogs(pageNum, 50, eventType || null);
      if (Array.isArray(res)) {
        setLogs(res);
        setTotalPages(1);
      } else {
        setLogs(res?.items || []);
        setTotalPages(res?.total_pages || 1);
        if (!isBackground) setPage(res?.page || 1);
      }
      setLastRefreshed(new Date());
    } catch (err) {
      if (!isBackground) addToast(err.message, "error");
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, [addToast, eventTypeFilter]);

  // Initial fetch and filter changes
  useEffect(() => {
    fetchLogs(page, eventTypeFilter);
  }, [page, eventTypeFilter, fetchLogs]);

  // Polling every 5 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      fetchLogs(page, eventTypeFilter, true);
    }, 5000);
    return () => clearInterval(intervalId);
  }, [page, eventTypeFilter, fetchLogs]);

  const handleRetry = async (e, logId) => {
    e.stopPropagation();
    try {
      setIsRetrying(prev => ({ ...prev, [logId]: true }));
      await retryWebhookLog(logId);
      addToast("Retry initiated");
      // Immediate fetch to see the change to pending/retrying
      await fetchLogs(page, eventTypeFilter, true);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setIsRetrying(prev => ({ ...prev, [logId]: false }));
    }
  };

  const toggleExpand = (logId) => {
    setExpandedLogId(prev => prev === logId ? null : logId);
  };

  const getStatusVariant = (status) => {
    switch(status?.toLowerCase()) {
      case 'success': return 'success';
      case 'failed': return 'danger';
      case 'retrying': return 'warning';
      default: return 'secondary';
    }
  };

  if (loading && logs.length === 0) {
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

  return (
    <div className="space-y-8 animate-fade-in-up">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground flex items-center gap-2">
            Webhook Logs
            <span className="text-[10px] font-medium text-muted-foreground flex items-center gap-1 bg-muted px-2 py-0.5 rounded-full uppercase tracking-wider">
              <RefreshCw className="w-3 h-3 animate-spin" /> Live
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time webhook delivery tracking</p>
        </div>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full md:w-auto">
          <div className="text-xs text-muted-foreground whitespace-nowrap">
            Updated: {lastRefreshed.toLocaleTimeString()}
          </div>
          <Select
            value={eventTypeFilter}
            onChange={(e) => {
              setPage(1);
              setEventTypeFilter(e.target.value);
            }}
            className="w-full sm:w-48"
          >
            <option value="">All Event Types</option>
            {EVENT_TYPES.map(type => (
              <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
            ))}
          </Select>
        </div>
      </div>

      <Card className="flex flex-col overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left w-8"></th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Event Type</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">Attempts</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="p-0">
                    <EmptyState
                      icon={Activity}
                      title="No Logs Found"
                      description="No webhook events have been recorded yet."
                      className="my-12"
                    />
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <React.Fragment key={log.id}>
                    <tr 
                      className="hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => toggleExpand(log.id)}
                    >
                      <td className="px-4 py-4 whitespace-nowrap text-muted-foreground">
                        {expandedLogId === log.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground font-mono">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-foreground capitalize">
                        {log.event_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge variant={getStatusVariant(log.status)} className="capitalize">
                          {log.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground text-center font-mono">
                        {log.attempt_number}/{log.max_retries}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        {['failed', 'retrying'].includes(log.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleRetry(e, log.id)}
                            disabled={isRetrying[log.id]}
                            isLoading={isRetrying[log.id]}
                            className="ml-auto"
                          >
                            <RefreshCw className="w-3 h-3 mr-1" />
                            Retry
                          </Button>
                        )}
                      </td>
                    </tr>
                    {expandedLogId === log.id && (
                      <tr className="bg-muted/20 border-b border-border">
                        <td colSpan="6" className="px-6 py-6">
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div>
                              <h4 className="font-semibold text-foreground mb-3 text-sm flex items-center">
                                Payload
                              </h4>
                              <pre className="bg-[#1e1e2e] text-[#a6accd] p-4 rounded-md text-[11px] overflow-x-auto shadow-inner border border-[#181825]">
                                {(() => {
                                  try {
                                    return JSON.stringify(JSON.parse(log.payload), null, 2);
                                  } catch (e) {
                                    return log.payload;
                                  }
                                })()}
                              </pre>
                            </div>
                            <div>
                              <h4 className="font-semibold text-foreground mb-3 text-sm">Delivery Details</h4>
                              <div className="bg-card border rounded-md p-4 space-y-4">
                                <div>
                                  <span className="text-muted-foreground block text-[10px] uppercase tracking-wider font-semibold mb-1">Target URL</span>
                                  <span className="font-medium font-mono text-sm break-all text-foreground">{log.target_url}</span>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider font-semibold mb-1">Response Code</span>
                                    <span className="font-medium font-mono text-sm">
                                      {log.status_code ? (
                                        <span className={log.status_code >= 200 && log.status_code < 300 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                                          {log.status_code}
                                        </span>
                                      ) : <span className="text-muted-foreground">-</span>}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider font-semibold mb-1">Next Retry</span>
                                    <span className="font-medium font-mono text-sm text-foreground">
                                      {log.next_retry_at ? new Date(log.next_retry_at).toLocaleString() : '-'}
                                    </span>
                                  </div>
                                </div>
                                {(log.error_message || log.response_body) && (
                                  <div>
                                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider font-semibold mb-2">
                                      {log.error_message ? 'Error' : 'Response Body'}
                                    </span>
                                    <div className="bg-destructive/10 text-destructive p-3 rounded border border-destructive/20 text-xs font-mono whitespace-pre-wrap">
                                      {log.error_message || log.response_body}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
        {logs.length > 0 && (
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        )}
      </Card>
    </div>
  );
}
