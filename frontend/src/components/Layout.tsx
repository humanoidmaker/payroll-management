import { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { IndianRupee, LayoutDashboard, ChevronLeft, Settings, BarChart3, Users, ChevronRight, LogOut, FileText, CalendarCheck, Play } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/employees", label: "Employees", icon: Users },
  { to: "/salary", label: "Salary Structure", icon: IndianRupee },
  { to: "/run-payroll", label: "Run Payroll", icon: Play },
  { to: "/payslips", label: "Payslips", icon: FileText },
  { to: "/attendance", label: "Attendance", icon: CalendarCheck },
  { to: "/reports", label: "Reports", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);
  const [time, setTime] = useState('');
  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Kolkata' }));
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, []);
  const currentLabel = NAV.find(n => n.to === '/' ? location.pathname === '/' : location.pathname.startsWith(n.to))?.label || 'PayRoll Pro';
  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <aside className={cn('flex flex-col bg-primary text-white transition-all duration-200 shrink-0', collapsed ? 'w-16' : 'w-56')}>
        <div className={cn('flex items-center gap-2 border-b border-white/10 px-4 py-4', collapsed && 'justify-center px-2')}>
          <LayoutDashboard className="h-6 w-6 text-accent shrink-0" />
          {!collapsed && <span className="font-bold text-lg">PayRoll Pro</span>}
        </div>
        <nav className="flex-1 py-3 space-y-0.5 px-2">
          {NAV.map(n => {
            const active = n.to === '/' ? location.pathname === '/' : location.pathname.startsWith(n.to);
            return (<Link key={n.to} to={n.to} className={cn('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors', active ? 'bg-white/15 text-white font-medium' : 'text-white/70 hover:bg-white/10', collapsed && 'justify-center px-2')}><n.icon className="h-4 w-4 shrink-0" />{!collapsed && n.label}</Link>);
          })}
        </nav>
        <div className={cn('border-t border-white/10 px-4 py-3', collapsed && 'px-2')}>
          {!collapsed && <p className="text-[10px] text-white/40 mb-1">{user?.name}</p>}
          {!collapsed && <button onClick={logout} className="text-[10px] text-white/40 hover:text-white flex items-center gap-1"><LogOut className="h-3 w-3" /> Logout</button>}
          <button onClick={() => setCollapsed(!collapsed)} className="mt-2 text-white/40 hover:text-white">{collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}</button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 border-b bg-white flex items-center justify-between px-6 shrink-0">
          <h1 className="font-semibold text-lg text-primary">{currentLabel}</h1>
          <span className="text-sm font-mono text-accent font-medium">{time}</span>
        </header>
        <main className="flex-1 overflow-y-auto p-6"><Outlet /></main>
      </div>
    </div>
  );
}