import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import type { Group } from '../api/groups';
import { createGroup, listGroups, deleteGroup } from '../api/groups';

interface HotelOption {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
}

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [hotels, setHotels] = useState<HotelOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [hotelSearch, setHotelSearch] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchGroups = () => {
    listGroups().then(r => { setGroups(r.data); setLoading(false); });
  };

  useEffect(() => { fetchGroups(); }, []);

  const openForm = () => {
    if (hotels.length === 0) {
      client.get('/hotels', { params: { page_size: 500 } }).then(r => setHotels(r.data.items));
    }
    setShowForm(true);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setSaving(true);
    await createGroup(newName.trim(), Array.from(selectedIds));
    setNewName('');
    setSelectedIds(new Set());
    setShowForm(false);
    setSaving(false);
    fetchGroups();
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete group "${name}"?`)) return;
    await deleteGroup(id);
    fetchGroups();
  };

  const toggleHotel = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const filteredHotels = hotels.filter(h => {
    if (!hotelSearch) return true;
    const q = hotelSearch.toLowerCase();
    return h.name.toLowerCase().includes(q) ||
      (h.city?.toLowerCase().includes(q)) ||
      (h.state?.toLowerCase().includes(q));
  });

  if (loading) return <p className="text-gray-500">Loading groups...</p>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Groups ({groups.length})</h2>
        <button onClick={openForm} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
          Create Group
        </button>
      </div>

      {showForm && (
        <div className="bg-white p-4 rounded shadow border mb-6">
          <h3 className="font-semibold mb-3">New Group</h3>
          <input
            type="text"
            placeholder="Group name"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            className="border rounded px-3 py-2 w-full mb-3"
          />
          <div className="mb-2">
            <label className="text-sm text-gray-600">Select hotels ({selectedIds.size} selected)</label>
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
            <button onClick={handleCreate} disabled={saving || !newName.trim()}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm">
              {saving ? 'Creating...' : 'Create'}
            </button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 rounded border text-sm hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {groups.length === 0 ? (
        <p className="text-gray-500">No groups yet. Create one to organize your hotels.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 text-left">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Hotels</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {groups.map(g => (
                <tr key={g.id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <Link to={`/groups/${g.id}`} className="text-blue-600 hover:underline">{g.name}</Link>
                  </td>
                  <td className="px-3 py-2">{g.hotel_count}</td>
                  <td className="px-3 py-2">
                    <button onClick={() => handleDelete(g.id, g.name)}
                      className="text-red-600 hover:underline text-sm">Delete</button>
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
