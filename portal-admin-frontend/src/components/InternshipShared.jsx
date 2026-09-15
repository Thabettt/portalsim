import React from 'react';
import { Link } from 'react-router-dom';

export function SectionBlock({ title, description, icon: Icon, children }) {
  return (
    <section className="overflow-hidden rounded-xl border border-red-600 bg-card shadow-sm dark:border-red-700">
      <div className="flex items-start gap-3 border-b border-red-600 bg-red-600 px-4 py-3 dark:border-red-700 dark:bg-red-700">
        {Icon ? (
          <div className="mt-0.5 rounded-md bg-white/20 p-1.5 text-white">
            <Icon className="h-4 w-4" />
          </div>
        ) : null}
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {description ? <p className="text-xs text-red-100">{description}</p> : null}
        </div>
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

export function DetailItem({ label, value }) {
  return (
    <div className="rounded-lg border border-border dark:border-border dark:border-border/60 bg-muted dark:bg-muted dark:bg-muted/20 p-3">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm text-foreground">{value ?? 'Not available'}</div>
    </div>
  );
}

export function StudentIdentity({ item }) {
  return (
    <Link to={`/students/${item.studentId ?? item.student_id}`} className="block group">
      <div className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
        {item.studentName || item.student_name || `Student ${item.studentId ?? item.student_id}`}
      </div>
      <div className="text-xs text-muted-foreground">
        {item.studentStringId || item.student_string_id || (item.student_email ? item.student_email.replace(/\+[^@]+/, '') : '') || ''}
      </div>
    </Link>
  );
}
