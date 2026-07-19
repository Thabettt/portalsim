import React, { useState } from 'react';

export default function ConfirmButton({ onConfirm, children, className = "", confirmText = "Are you sure?" }) {
  const [asking, setAsking] = useState(false);

  if (asking) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-red-600 font-medium">{confirmText}</span>
        <button
          onClick={() => {
            setAsking(false);
            onConfirm();
          }}
          className="px-2 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
        >
          Yes
        </button>
        <button
          onClick={() => setAsking(false)}
          className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
        >
          No
        </button>
      </div>
    );
  }

  return React.cloneElement(children, {
    onClick: (e) => {
      e.preventDefault();
      e.stopPropagation();
      setAsking(true);
    },
    className: `${children.props.className || ''} ${className}`.trim()
  });
}
