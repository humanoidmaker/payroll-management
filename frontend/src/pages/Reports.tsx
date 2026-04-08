import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line,
} from 'recharts';
import { BarChart3, Loader2, Users, IndianRupee, Download, TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';

const COLORS = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function Reports() {
  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState<any[]>([]);
  const [payslips, setPayslips] = useState<any[]>([]);
  const [salaryStructures, setSalaryStructures] = useState<any[]>([]);
  const [attendance, setAttendance] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      api.get('/employees').then(r => r.data.employees || []).catch(() => []),
      api.get('/payslips').then(r => r.data.payslips || []).catch(() => []),
      api.get('/salary-structures').then(r => r.data.structures || r.data.salary_structures || []).catch(() => []),
      api.get('/attendance').then(r => r.data.records || r.data.attendance || []).catch(() => []),
    ]).then(([e, p, s, a]) => {
      setEmployees(e);
      setPayslips(p);
      setSalaryStructures(s);
      setAttendance(a);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>;

  // Total payroll cost per month
  const monthlyPayroll: Record<string, { gross: number; net: number; deductions: number }> = {};
  payslips.forEach(p => {
    const month = (p.month || p.pay_period || (p.created_at || '').slice(0, 7));
    if (!monthlyPayroll[month]) monthlyPayroll[month] = { gross: 0, net: 0, deductions: 0 };
    monthlyPayroll[month].gross += p.gross_salary || p.gross || 0;
    monthlyPayroll[month].net += p.net_salary || p.net || 0;
    monthlyPayroll[month].deductions += p.total_deductions || p.deductions || 0;
  });
  const payrollTrend = Object.entries(monthlyPayroll)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([month, data]) => ({
      month: month.slice(2),
      Gross: data.gross,
      Net: data.net,
      Deductions: data.deductions,
    }));

  const totalGross = payslips.reduce((s, p) => s + (p.gross_salary || p.gross || 0), 0);
  const totalNet = payslips.reduce((s, p) => s + (p.net_salary || p.net || 0), 0);

  // Department-wise salary distribution
  const deptSalary: Record<string, number> = {};
  employees.forEach(e => {
    const dept = e.department || 'Unassigned';
    deptSalary[dept] = (deptSalary[dept] || 0) + (e.salary || e.basic_salary || e.ctc || 0);
  });
  const deptData = Object.entries(deptSalary)
    .map(([name, value]) => ({ name, value: Math.round(value) }))
    .sort((a, b) => b.value - a.value);

  // Employee count by department
  const deptCount: Record<string, number> = {};
  employees.forEach(e => {
    const dept = e.department || 'Unassigned';
    deptCount[dept] = (deptCount[dept] || 0) + 1;
  });
  const deptCountData = Object.entries(deptCount).map(([name, count]) => ({ name, count }));

  // Salary range distribution
  const ranges = [
    { label: '<20k', min: 0, max: 20000 },
    { label: '20-40k', min: 20000, max: 40000 },
    { label: '40-60k', min: 40000, max: 60000 },
    { label: '60-80k', min: 60000, max: 80000 },
    { label: '80k-1L', min: 80000, max: 100000 },
    { label: '>1L', min: 100000, max: Infinity },
  ];
  const salaryDistribution = ranges.map(r => ({
    range: r.label,
    count: employees.filter(e => {
      const sal = e.salary || e.basic_salary || e.ctc || 0;
      return sal >= r.min && sal < r.max;
    }).length,
  }));

  // Top earners
  const topEarners = [...employees]
    .sort((a, b) => (b.salary || b.ctc || 0) - (a.salary || a.ctc || 0))
    .slice(0, 8);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <BarChart3 className="h-6 w-6 text-accent" /> Reports
      </h2>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <div className="flex items-center gap-2 mb-1">
            <Users className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-500">Employees</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{employees.length}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="flex items-center gap-2 mb-1">
            <IndianRupee className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-500">Total Gross (All Time)</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalGross)}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <span className="text-sm text-gray-500">Total Net Paid</span>
          <p className="text-2xl font-bold text-emerald-600">{formatCurrency(totalNet)}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <span className="text-sm text-gray-500">Total Payslips</span>
          <p className="text-2xl font-bold text-gray-900">{payslips.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payroll Trend */}
        <div className="bg-white rounded-xl border p-5 lg:col-span-2">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-accent" /> Monthly Payroll Trend
          </h3>
          {payrollTrend.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No payroll data yet. Run payroll to see trends.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={payrollTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" fontSize={11} />
                <YAxis fontSize={11} tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(val: number) => formatCurrency(val)} />
                <Legend />
                <Bar dataKey="Gross" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Net" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Department Salary Distribution Pie */}
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Department Salary Distribution</h3>
          {deptData.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={deptData} cx="50%" cy="50%" outerRadius={90} dataKey="value"
                  label={({ name, percent }) => `${name.length > 10 ? name.slice(0, 10) + '..' : name} ${(percent * 100).toFixed(0)}%`}>
                  {deptData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(val: number) => formatCurrency(val)} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Salary Range Distribution */}
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Salary Range Distribution</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={salaryDistribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Employees" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top Earners */}
        <div className="bg-white rounded-xl border p-5 lg:col-span-2">
          <h3 className="font-semibold text-gray-900 mb-4">Top Earners</h3>
          {topEarners.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">No employee data.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-2 font-medium">#</th>
                    <th className="pb-2 font-medium">Employee</th>
                    <th className="pb-2 font-medium">Department</th>
                    <th className="pb-2 font-medium">Designation</th>
                    <th className="pb-2 font-medium text-right">Salary / CTC</th>
                  </tr>
                </thead>
                <tbody>
                  {topEarners.map((e, i) => (
                    <tr key={e.id || i} className="border-b last:border-0">
                      <td className="py-2 text-gray-400">{i + 1}</td>
                      <td className="py-2 font-medium">{e.name}</td>
                      <td className="py-2 text-gray-500">{e.department || '-'}</td>
                      <td className="py-2 text-gray-500">{e.designation || e.position || '-'}</td>
                      <td className="py-2 text-right font-medium">{formatCurrency(e.salary || e.ctc || 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
