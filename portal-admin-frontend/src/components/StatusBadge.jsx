import React from 'react';

export default function StatusBadge({ status, type = 'default' }) {
  // Try to determine color based on common status strings
  const s = status?.toLowerCase() || '';
  
  let colorClass = 'bg-gray-100 text-gray-800 border-gray-200';
  
  if (['approved', 'paid', 'sent', 'present', 'completed'].includes(s)) {
    colorClass = 'bg-green-100 text-green-800 border-green-200';
  } else if (['rejected', 'failed', 'overdue', 'absent'].includes(s)) {
    colorClass = 'bg-red-100 text-red-800 border-red-200';
  } else if (['pending', 'retrying', 'late', 'partial'].includes(s)) {
    colorClass = 'bg-yellow-100 text-yellow-800 border-yellow-200';
  } else if (['excused', 'waived', 'in_progress'].includes(s)) {
    colorClass = 'bg-blue-100 text-blue-800 border-blue-200';
  }

  // Format status for display: replace underscores and title case
  const displayStatus = s.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {displayStatus}
    </span>
  );
}
