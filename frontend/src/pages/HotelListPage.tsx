import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';

interface Hotel {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  brand: string | null;
  latest_snapshot: {
    google_normalized: number | null;
    booking_normalized: number | null;
    expedia_normalized: number | null;
    tripadvisor_normalized: number | null;
    weighted_average: number | null;
  } | null;
}

function scoreColor(score: number | null): string {
  if (score == null) return 'text-gray-400';
  if (score >= 8) return 'text-green-600 font-semibold';
  if (score >= 6) return 'text-yellow-600 font-semibold';
  return 'text-red-600 font-semibold';
}

function scoreBg(score: number | null): string {
  if (score == null) return '';
  if (score >= 8) return 'bg-green-50';
  if (score >= 6) return 'bg-yellow-50';
  return 'bg-red-50';
}

function fmt(score: number | null): string {
  return score != null ? score.toFixed(1) : '—';
}

type SortKey = 'name' | 'city' | 'state' | 'weighted_average' | 'google' | 'booking' | 'expedia' | 'tripadvisor';

export default function HotelListPage() {
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/hotels').then(resp => {
      setHotels(resp.data);
      setLoading(false);
    });
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const getScore = (h: Hotel, key: SortKey): number | null => {
    const s = h.latest_snapshot;
    if (!s) return null;
    switch (key) {
      case 'google': return s.google_normalized;
      case 'booking': return s.booking_normalized;
      case 'expedia': return s.expedia_normalized;
      case 'tripadvisor': return s.tripadvisor_normalized;
      case 'weighted_average': return s.weighted_average;
      default: return null;
    }
  };

  const filtered = hotels.filter(h => {
    if (!search) return true;
    const q = search.toLowerCase();
    return h.name.toLowerCase().includes(q) ||
      (h.city?.toLowerCase().includes(q)) ||
      (h.state?.toLowerCase().includes(q)) ||
      (h.brand?.toLowerCase().includes(q));
  });

  const sorted = [...filtered].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1;
    if (['name', 'city', 'state'].includes(sortKey)) {
      const av = (a[sortKey as keyof Hotel] as string) ?? '';
      const bv = (b[sortKey as keyof Hotel] as string) ?? '';
      return av.localeCompare(bv) * dir;
    }
    const av = getScore(a, sortKey) ?? -Infinity;
    const bv = getScore(b, sortKey) ?? -Infinity;
    return (av - bv) * dir;
  });

  const arrow = (key: SortKey) => sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  const handleExport = async () => {
    const resp = await client.get('/export/hotels', { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hotels_export.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) return <p className="text-gray-500">Loading hotels...</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Hotels ({sorted.length})</h2>
        <button onClick={handleExport} className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 text-sm">
          Export CSV
        </button>
      </div>

      <input
        type="text"
        placeholder="Search by name, city, state, or brand..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="w-full border rounded px-3 py-2 mb-4"
      />

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-gray-100 text-left">
              <Th onClick={() => handleSort('name')}>Name{arrow('name')}</Th>
              <Th onClick={() => handleSort('city')}>City{arrow('city')}</Th>
              <Th onClick={() => handleSort('state')}>State{arrow('state')}</Th>
              <Th onClick={() => handleSort('google')}>Google{arrow('google')}</Th>
              <Th onClick={() => handleSort('booking')}>Booking{arrow('booking')}</Th>
              <Th onClick={() => handleSort('expedia')}>Expedia{arrow('expedia')}</Th>
              <Th onClick={() => handleSort('tripadvisor')}>TripAdv{arrow('tripadvisor')}</Th>
              <Th onClick={() => handleSort('weighted_average')}>Avg{arrow('weighted_average')}</Th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(h => {
              const s = h.latest_snapshot;
              const wa = s?.weighted_average ?? null;
              return (
                <tr key={h.id} className={`border-b hover:bg-gray-50 ${scoreBg(wa)}`}>
                  <td className="px-3 py-2">
                    <Link to={`/hotels/${h.id}`} className="text-blue-600 hover:underline">{h.name}</Link>
                  </td>
                  <td className="px-3 py-2">{h.city ?? '—'}</td>
                  <td className="px-3 py-2">{h.state ?? '—'}</td>
                  <td className={`px-3 py-2 ${scoreColor(s?.google_normalized ?? null)}`}>{fmt(s?.google_normalized ?? null)}</td>
                  <td className={`px-3 py-2 ${scoreColor(s?.booking_normalized ?? null)}`}>{fmt(s?.booking_normalized ?? null)}</td>
                  <td className={`px-3 py-2 ${scoreColor(s?.expedia_normalized ?? null)}`}>{fmt(s?.expedia_normalized ?? null)}</td>
                  <td className={`px-3 py-2 ${scoreColor(s?.tripadvisor_normalized ?? null)}`}>{fmt(s?.tripadvisor_normalized ?? null)}</td>
                  <td className={`px-3 py-2 ${scoreColor(wa)}`}>{fmt(wa)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <th className="px-3 py-2 cursor-pointer select-none hover:bg-gray-200 whitespace-nowrap" onClick={onClick}>
      {children}
    </th>
  );
}
