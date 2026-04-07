import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import toast from 'react-hot-toast';

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => { api.get('/settings').then(r => setSettings(r.data.settings || {})).catch(() => {}).finally(() => setLoading(false)); }, []);

  const save = async () => {
    setSaving(true);
    try { await api.put('/settings', settings); toast.success('Settings saved'); }
    catch { toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-accent" /></div>;

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><SettingsIcon className="h-6 w-6 text-accent" /> Settings</h2>
      <div className="bg-white rounded-xl border p-6 space-y-4">
        {Object.entries(settings).map(([key, value]) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">{key.replace(/_/g, ' ')}</label>
            <input type="text" value={value} onChange={e => setSettings(s => ({...s, [key]: e.target.value}))} className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-accent/30 outline-none" />
          </div>
        ))}
        <button onClick={save} disabled={saving} className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium disabled:opacity-50">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}