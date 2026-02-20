import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';

interface Stats {
  totalHotels: number;
  avgScore: number | null;
  topHotel: { name: string; score: number } | null;
  bottomHotel: { name: string; score: number } | null;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const resp = await client.get('/hotels', { params: { page_size: 500 } });
      const hotels = resp.data.items;
      const withScores = hotels.filter((h: any) => h.latest_snapshot?.weighted_average != null);
      const scores = withScores.map((h: any) => ({
        name: h.name,
        score: h.latest_snapshot.weighted_average,
      }));
      scores.sort((a: any, b: any) => b.score - a.score);

      setStats({
        totalHotels: hotels.length,
        avgScore: scores.length > 0
          ? Math.round((scores.reduce((s: number, h: any) => s + h.score, 0) / scores.length) * 100) / 100
          : null,
        topHotel: scores.length > 0 ? scores[0] : null,
        bottomHotel: scores.length > 0 ? scores[scores.length - 1] : null,
      });
    } catch {
      setStats(null);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await client.post('/hotels/import-csv', formData);
      setUploadMsg(`Imported ${resp.data.imported} hotel records.`);
      loadStats();
    } catch (err: any) {
      setUploadMsg(err.response?.data?.detail || 'Upload failed.');
    }
    setUploading(false);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <label className="bg-blue-600 text-white px-4 py-2 rounded cursor-pointer hover:bg-blue-700">
          {uploading ? 'Uploading...' : 'Upload CSV'}
          <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
        </label>
      </div>

      {uploadMsg && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-6">{uploadMsg}</div>
      )}

      {stats ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Hotels" value={stats.totalHotels} />
          <StatCard label="Avg Score" value={stats.avgScore?.toFixed(2) ?? 'N/A'} />
          <StatCard label="Top Hotel" value={stats.topHotel ? `${stats.topHotel.name} (${stats.topHotel.score})` : 'N/A'} />
          <StatCard label="Needs Attention" value={stats.bottomHotel ? `${stats.bottomHotel.name} (${stats.bottomHotel.score})` : 'N/A'} />
        </div>
      ) : (
        <p className="text-gray-500">Loading...</p>
      )}

      <div className="flex gap-4">
        <Link to="/hotels" className="text-blue-600 hover:underline">View all hotels →</Link>
        <Link to="/groups" className="text-blue-600 hover:underline">Manage groups →</Link>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white p-4 rounded shadow border">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-lg font-semibold truncate">{value}</div>
    </div>
  );
}
