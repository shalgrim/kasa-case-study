import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import client from '../api/client';
import type { GroupDetail } from '../api/groups';
import { getGroup, updateGroup, exportGroup } from '../api/groups';

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

interface HotelOption {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
}

export default function GroupDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [allHotels, setAllHotels] = useState<HotelOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [hotelSearch, setHotelSearch] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchGroup = () => {
    if (!id) return;
    getGroup(Number(id)).then(r => setGroup(r.data));
  };

  useEffect(() => { fetchGroup(); }, [id]);

  const handleExport = async () => {
    if (!id) return;
    const resp = await exportGroup(Number(id));
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = `group_${id}_export.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const openEdit = () => {
    if (!group) return;
    setEditName(group.name);
    setSelectedIds(new Set(group.hotels.map(h => h.id)));
    if (allHotels.length === 0) {
      client.get('/hotels').then(r => setAllHotels(r.data));
    }
    setEditing(true);
  };

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    await updateGroup(Number(id), { name: editName.trim(), hotel_ids: Array.from(selectedIds) });
    setSaving(false);
    setEditing(false);
    fetchGroup();
  };

  const toggleHotel = (hid: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(hid)) next.delete(hid); else next.add(hid);
      return next;
    });
  };

  const filteredHotels = allHotels.filter(h => {
    if (!hotelSearch) return true;
    const q = hotelSearch.toLowerCase();
    return h.name.toLowerCase().includes(q) ||
      (h.city?.toLowerCase().includes(q)) ||
      (h.state?.toLowerCase().includes(q));
  });

  if (!group) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <Link to="/groups" className="text-blue-600 hover:underline text-sm">← Back to groups</Link>

      <div className="mt-4 mb-6 flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold">{group.name}</h2>
          <p className="text-gray-600">{group.hotels.length} hotel{group.hotels.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={openEdit} className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 text-sm">
            Edit Group
          </button>
          <button onClick={handleExport} className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 text-sm">
            Export CSV
          </button>
        </div>
      </div>

      {editing && (
        <div className="bg-white p-4 rounded shadow border mb-6">
          <h3 className="font-semibold mb-3">Edit Group</h3>
          <input
            type="text"
            value={editName}
            onChange={e => setEditName(e.target.value)}
            className="border rounded px-3 py-2 w-full mb-3"
          />
          <div className="mb-2">
            <label className="text-sm text-gray-600">Hotels ({selectedIds.size} selected)</label>
            <input
              type="text"
              placeholder="Search hotels..."
              value={hotelSearch}
              onChange={e => setHotelSearch(e.target.value)}
              className="border rounded px-3 py-1 w-full mt-1 text-sm"
            />
          </div>
          <div className="max-h-48 overflow-y-auto border rounded p-2 mb-3">
            {filteredHotels.map(h => (
              <label key={h.id} className="flex items-center gap-2 py-1 text-sm hover:bg-gray-50 px-1 rounded cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedIds.has(h.id)}
                  onChange={() => toggleHotel(h.id)}
                />
                <span>{h.name}</span>
                <span className="text-gray-400 text-xs">{[h.city, h.state].filter(Boolean).join(', ')}</span>
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={saving || !editName.trim()}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm">
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)} className="px-4 py-2 rounded border text-sm hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {group.hotels.length === 0 ? (
        <p className="text-gray-500">No hotels in this group. Click Edit Group to add some.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 text-left">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">City</th>
                <th className="px-3 py-2">State</th>
                <th className="px-3 py-2">Google</th>
                <th className="px-3 py-2">Booking</th>
                <th className="px-3 py-2">Expedia</th>
                <th className="px-3 py-2">TripAdv</th>
                <th className="px-3 py-2">Avg</th>
              </tr>
            </thead>
            <tbody>
              {group.hotels.map(h => (
                <tr key={h.id} className={`border-b hover:bg-gray-50 ${scoreBg(h.weighted_average)}`}>
                  <td className="px-3 py-2">
                    <Link to={`/hotels/${h.id}`} className="text-blue-600 hover:underline">{h.name}</Link>
                  </td>
                  <td className="px-3 py-2">{h.city ?? '—'}</td>
                  <td className="px-3 py-2">{h.state ?? '—'}</td>
                  <td className={`px-3 py-2 ${scoreColor(h.google_normalized)}`}>{fmt(h.google_normalized)}</td>
                  <td className={`px-3 py-2 ${scoreColor(h.booking_normalized)}`}>{fmt(h.booking_normalized)}</td>
                  <td className={`px-3 py-2 ${scoreColor(h.expedia_normalized)}`}>{fmt(h.expedia_normalized)}</td>
                  <td className={`px-3 py-2 ${scoreColor(h.tripadvisor_normalized)}`}>{fmt(h.tripadvisor_normalized)}</td>
                  <td className={`px-3 py-2 ${scoreColor(h.weighted_average)}`}>{fmt(h.weighted_average)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
