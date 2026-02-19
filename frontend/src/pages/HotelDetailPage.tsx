import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import client from '../api/client';

interface Snapshot {
  id: number;
  collected_at: string;
  source: string;
  google_score: number | null;
  google_count: number | null;
  google_normalized: number | null;
  booking_score: number | null;
  booking_count: number | null;
  booking_normalized: number | null;
  expedia_score: number | null;
  expedia_count: number | null;
  expedia_normalized: number | null;
  tripadvisor_score: number | null;
  tripadvisor_count: number | null;
  tripadvisor_normalized: number | null;
  weighted_average: number | null;
}

interface Hotel {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  keys: number | null;
  kind: string | null;
  brand: string | null;
  parent: string | null;
  latest_snapshot: Snapshot | null;
}

function scoreColor(score: number | null): string {
  if (score == null) return 'text-gray-400';
  if (score >= 8) return 'text-green-600';
  if (score >= 6) return 'text-yellow-600';
  return 'text-red-600';
}

export default function HotelDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [hotel, setHotel] = useState<Hotel | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [collecting, setCollecting] = useState(false);
  const [collectMsg, setCollectMsg] = useState('');

  useEffect(() => {
    if (!id) return;
    client.get(`/hotels/${id}`).then(r => setHotel(r.data));
    client.get(`/hotels/${id}/history`).then(r => setHistory(r.data));
  }, [id]);

  const handleCollect = async () => {
    setCollecting(true);
    setCollectMsg('');
    try {
      const resp = await client.post(`/reviews/hotels/${id}/collect`);
      setCollectMsg(`New snapshot created (weighted avg: ${resp.data.weighted_average})`);
      client.get(`/hotels/${id}`).then(r => setHotel(r.data));
      client.get(`/hotels/${id}/history`).then(r => setHistory(r.data));
    } catch {
      setCollectMsg('Collection failed (API keys may not be configured)');
    }
    setCollecting(false);
  };

  if (!hotel) return <p className="text-gray-500">Loading...</p>;

  const s = hotel.latest_snapshot;

  const barData = [
    { channel: 'Google', score: s?.google_normalized ?? 0, count: s?.google_count ?? 0 },
    { channel: 'Booking', score: s?.booking_normalized ?? 0, count: s?.booking_count ?? 0 },
    { channel: 'Expedia', score: s?.expedia_normalized ?? 0, count: s?.expedia_count ?? 0 },
    { channel: 'TripAdvisor', score: s?.tripadvisor_normalized ?? 0, count: s?.tripadvisor_count ?? 0 },
  ].filter(d => d.score > 0);

  const radarData = [
    { channel: 'Google', score: s?.google_normalized ?? 0 },
    { channel: 'Booking', score: s?.booking_normalized ?? 0 },
    { channel: 'Expedia', score: s?.expedia_normalized ?? 0 },
    { channel: 'TripAdvisor', score: s?.tripadvisor_normalized ?? 0 },
  ];

  return (
    <div>
      <Link to="/hotels" className="text-blue-600 hover:underline text-sm">← Back to hotels</Link>

      <div className="mt-4 mb-6">
        <h2 className="text-2xl font-bold">{hotel.name}</h2>
        <p className="text-gray-600">
          {[hotel.city, hotel.state].filter(Boolean).join(', ')}
          {hotel.kind && ` · ${hotel.kind}`}
          {hotel.brand && ` · ${hotel.brand}`}
          {hotel.keys && ` · ${hotel.keys} keys`}
        </p>
      </div>

      <div className="flex gap-2 mb-6">
        <button onClick={handleCollect} disabled={collecting}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm">
          {collecting ? 'Collecting...' : 'Collect Live Reviews'}
        </button>
        {collectMsg && <span className="text-sm text-gray-600 self-center">{collectMsg}</span>}
      </div>

      {s ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <ScoreCard label="Google" raw={s.google_score} normalized={s.google_normalized} count={s.google_count} />
            <ScoreCard label="Booking" raw={s.booking_score} normalized={s.booking_normalized} count={s.booking_count} />
            <ScoreCard label="Expedia" raw={s.expedia_score} normalized={s.expedia_normalized} count={s.expedia_count} />
            <ScoreCard label="TripAdvisor" raw={s.tripadvisor_score} normalized={s.tripadvisor_normalized} count={s.tripadvisor_count} />
            <div className="bg-white p-4 rounded shadow border">
              <div className="text-sm text-gray-500">Weighted Avg</div>
              <div className={`text-2xl font-bold ${scoreColor(s.weighted_average)}`}>
                {s.weighted_average?.toFixed(2) ?? '—'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <div className="bg-white p-4 rounded shadow border">
              <h3 className="font-semibold mb-4">Normalized Scores by Channel</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="channel" />
                  <YAxis domain={[0, 10]} />
                  <Tooltip />
                  <Bar dataKey="score" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white p-4 rounded shadow border">
              <h3 className="font-semibold mb-4">Channel Comparison</h3>
              <ResponsiveContainer width="100%" height={250}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="channel" />
                  <PolarRadiusAxis domain={[0, 10]} />
                  <Radar dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      ) : (
        <p className="text-gray-500">No review data available.</p>
      )}

      {history.length > 0 && (
        <div className="bg-white p-4 rounded shadow border">
          <h3 className="font-semibold mb-4">Snapshot History</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100 text-left">
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Google</th>
                <th className="px-3 py-2">Booking</th>
                <th className="px-3 py-2">Expedia</th>
                <th className="px-3 py-2">TripAdv</th>
                <th className="px-3 py-2">Avg</th>
              </tr>
            </thead>
            <tbody>
              {history.map(snap => (
                <tr key={snap.id} className="border-b">
                  <td className="px-3 py-2">{new Date(snap.collected_at).toLocaleDateString()}</td>
                  <td className="px-3 py-2">{snap.source}</td>
                  <td className="px-3 py-2">{snap.google_normalized?.toFixed(1) ?? '—'}</td>
                  <td className="px-3 py-2">{snap.booking_normalized?.toFixed(1) ?? '—'}</td>
                  <td className="px-3 py-2">{snap.expedia_normalized?.toFixed(1) ?? '—'}</td>
                  <td className="px-3 py-2">{snap.tripadvisor_normalized?.toFixed(1) ?? '—'}</td>
                  <td className={`px-3 py-2 font-semibold ${scoreColor(snap.weighted_average)}`}>
                    {snap.weighted_average?.toFixed(2) ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ScoreCard({ label, raw, normalized, count }: {
  label: string;
  raw: number | null;
  normalized: number | null;
  count: number | null;
}) {
  return (
    <div className="bg-white p-4 rounded shadow border">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`text-xl font-bold ${scoreColor(normalized)}`}>
        {normalized?.toFixed(1) ?? '—'}
      </div>
      <div className="text-xs text-gray-400">
        Raw: {raw ?? '—'} · {count?.toLocaleString() ?? '—'} reviews
      </div>
    </div>
  );
}
