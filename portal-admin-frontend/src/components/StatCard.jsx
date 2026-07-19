import React from 'react';

export default function StatCard({ title, value, icon: Icon, colorClass = "text-blue-600 bg-blue-50" }) {
  return (
    <div className="bg-white rounded-lg border p-5 flex items-center gap-4 shadow-sm">
      {Icon && (
        <div className={`p-3 rounded-full ${colorClass}`}>
          <Icon className="w-6 h-6" />
        </div>
      )}
      <div>
        <p className="text-sm text-gray-500 font-medium">{title}</p>
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
