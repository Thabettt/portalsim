import React from 'react';

export default function StatusBadge({ status, type = 'default' }) {
  // Try to determine color based on common status strings
  const s = status?.toLowerCase() || '';
  
  let colorClass = 'bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700';
  
  if (['approved', 'paid', 'sent', 'present', 'completed'].includes(s)) {
    colorClass = 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800';
  } else if (['rejected', 'failed', 'overdue', 'absent'].includes(s)) {
    colorClass = 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
  } else if (['pending', 'retrying', 'late', 'partial'].includes(s)) {
    colorClass = 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800';
  } else if (['excused', 'waived', 'in_progress'].includes(s)) {
    colorClass = 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800';
  }

  // Format status for display: replace underscores and title case
  const displayStatus = s.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {displayStatus}
    </span>
  );
}
