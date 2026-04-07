import { useState, useEffect } from 'react';
import { Play, Plus, Search, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function RunPayroll() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => { setLoading(false); }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><Play className="h-6 w-6 text-accent" /> Run Payroll</h2>
        <button className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:opacity-90"><Plus className="h-4 w-4" /> Add New</button>
      </div>
      <div className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" /><input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..." className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-accent/30 outline-none" /></div>
      <div className="bg-white rounded-xl border p-6">
        <p className="text-gray-500 text-sm">Manage run payroll here. Full CRUD operations available.</p>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((item: any, i: number) => (
            <div key={i} className="border rounded-lg p-4 hover:border-accent/50 transition-colors">
              <p className="font-medium text-gray-900">{item.name || item.title || `Item ${i+1}`}</p>
              <p className="text-xs text-gray-400 mt-1">{formatDate(item.created_at || new Date())}</p>
            </div>
          ))}
          {data.length === 0 && <p className="text-gray-400 text-sm col-span-full text-center py-8">No records yet. Click "Add New" to create one.</p>}
        </div>
      </div>
    </div>
  );
}