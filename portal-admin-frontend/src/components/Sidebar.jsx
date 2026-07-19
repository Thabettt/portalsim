import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  CreditCard, 
  Briefcase, 
  BookOpen, 
  History, 
  Settings,
  Moon,
  Sun,
  X
} from 'lucide-react';
import { getHealth } from '../api';
import { useTheme } from '../hooks/useTheme';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Attendance', path: '/attendance', icon: Users },
  { label: 'Payments', path: '/payments', icon: CreditCard },
  { label: 'Internships', path: '/internships', icon: Briefcase },
  { label: 'Grades & Deadlines', path: '/grades', icon: BookOpen },
  { label: 'Webhook Log', path: '/webhooks', icon: History },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar({ isOpen, setIsOpen }) {
  const location = useLocation();
  const [isHealthy, setIsHealthy] = useState(true);
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await getHealth();
        setIsHealthy(true);
      } catch {
        setIsHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Close sidebar on route change for mobile
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname, setIsOpen]);

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside 
        className={`w-64 bg-card dark:bg-zinc-950 border-r border-border text-foreground flex flex-col h-screen fixed left-0 top-0 z-50 transition-transform duration-300 ease-in-out md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
              <span className="font-bold text-lg leading-none">P</span>
            </div>
            <span>Portal Admin</span>
          </h1>
          <button 
            className="md:hidden text-muted-foreground hover:bg-muted p-1 rounded"
            onClick={() => setIsOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

      <div className="px-4 pb-4">
        <button
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }));
          }}
          className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-muted-foreground bg-muted/50 hover:bg-muted border border-border/50 rounded-md transition-colors"
        >
          <div className="flex items-center gap-2">
            <SearchIcon className="w-4 h-4" />
            <span>Search...</span>
          </div>
          <kbd className="inline-flex h-5 items-center gap-1 rounded border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
            <span className="text-xs">⌘</span>K
          </kbd>
        </button>
      </div>

      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors ${
                isActive 
                  ? 'bg-secondary text-secondary-foreground font-medium' 
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border bg-muted/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="relative flex items-center justify-center">
              <div className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
              {isHealthy && <div className="absolute w-2 h-2 rounded-full bg-emerald-500 animate-ping opacity-75"></div>}
            </div>
            <div className="text-xs">
              <p className="font-medium">Backend API</p>
              <p className={`text-[10px] ${isHealthy ? 'text-muted-foreground' : 'text-red-500'}`}>
                {isHealthy ? 'Connected' : 'Disconnected'}
              </p>
            </div>
          </div>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md transition-colors"
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </aside>
    </>
  );
}

function SearchIcon(props) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}
