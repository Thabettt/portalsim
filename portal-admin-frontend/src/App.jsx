import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import { ToastProvider } from './hooks/useToast';
import { ThemeProvider } from './hooks/useTheme';
import { CommandPalette } from './components/CommandPalette';
import { Menu } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Attendance from './pages/Attendance';
import Payments from './pages/Payments';
import Internships from './pages/Internships';
import GradesDeadlines from './pages/GradesDeadlines';
import WebhookLog from './pages/WebhookLog';
import Settings from './pages/Settings';
import StudentDetail from './pages/StudentDetail';

export default function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <ThemeProvider>
      <BrowserRouter>
        <ToastProvider>
          <div className="flex h-screen bg-background overflow-hidden font-sans text-foreground selection:bg-primary/20 selection:text-primary relative">
            <CommandPalette />
            
            <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
            
            <main className="flex-1 md:ml-64 overflow-y-auto flex flex-col h-screen w-full">
              {/* Mobile Header */}
              <div className="md:hidden flex items-center p-4 border-b border-border bg-card sticky top-0 z-10">
                <button 
                  onClick={() => setIsSidebarOpen(true)}
                  className="p-2 -ml-2 text-muted-foreground hover:bg-muted rounded-md"
                >
                  <Menu className="w-6 h-6" />
                </button>
                <div className="ml-2 font-semibold flex items-center gap-2">
                  <div className="h-6 w-6 rounded-md bg-primary text-primary-foreground flex items-center justify-center">
                    <span className="font-bold text-sm leading-none">P</span>
                  </div>
                  <span>Portal Admin</span>
                </div>
              </div>

              <div className="p-4 md:p-8 max-w-7xl w-full mx-auto min-h-full">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/attendance" element={<Attendance />} />
                  <Route path="/payments" element={<Payments />} />
                  <Route path="/internships" element={<Internships />} />
                  <Route path="/grades" element={<GradesDeadlines />} />
                  <Route path="/webhooks" element={<WebhookLog />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/students/:studentId" element={<StudentDetail />} />
                </Routes>
              </div>
            </main>
          </div>
        </ToastProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
