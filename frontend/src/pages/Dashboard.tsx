import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '@/lib/api';
export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.get('/stats').then(r => setStats(r.data.stats || r.data)).catch(() => {}).finally(() => setLoading(false)); }, []);
  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" /></div>;
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats && Object.entries(stats).slice(0, 8).map(([key, val]) => (
          <div key={key} className="bg-white rounded-xl border p-5">
            <p className="text-2xl font-bold text-gray-900">{typeof val === 'number' && val > 100 ? `\u20B9${Number(val).toLocaleString()}` : String(val)}</p>
            <p className="text-sm text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
          </div>
        ))}
      </div>
    </div>
  );
}