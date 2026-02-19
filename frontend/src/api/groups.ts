import client from './client';

export interface Group {
  id: number;
  name: string;
  hotel_count: number;
}

export interface GroupHotel {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  google_normalized: number | null;
  booking_normalized: number | null;
  expedia_normalized: number | null;
  tripadvisor_normalized: number | null;
  weighted_average: number | null;
}

export interface GroupDetail {
  id: number;
  name: string;
  hotels: GroupHotel[];
}

export function createGroup(name: string, hotelIds: number[]) {
  return client.post<Group>('/groups', { name, hotel_ids: hotelIds });
}

export function listGroups() {
  return client.get<Group[]>('/groups');
}

export function getGroup(id: number) {
  return client.get<GroupDetail>(`/groups/${id}`);
}

export function updateGroup(id: number, data: { name?: string; hotel_ids?: number[] }) {
  return client.put<Group>(`/groups/${id}`, data);
}

export function deleteGroup(id: number) {
  return client.delete(`/groups/${id}`);
}

export function exportGroup(id: number) {
  return client.get(`/export/groups/${id}`, { responseType: 'blob' });
}
