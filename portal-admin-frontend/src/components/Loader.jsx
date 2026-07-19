import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Loader({ text = "Loading...", className = "" }) {
  return (
    <div className={`flex items-center justify-center p-4 text-gray-500 ${className}`}>
      <Loader2 className="w-5 h-5 animate-spin mr-2" />
      <span className="text-sm font-medium">{text}</span>
    </div>
  );
}
