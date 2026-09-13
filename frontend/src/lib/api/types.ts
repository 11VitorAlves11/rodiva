export type Role = "owner" | "manager" | "editor" | "reader";

export type User = {
  id: string;
  email: string;
  name: string | null;
  locale: string;
};

export type Membership = {
  household_id: string;
  household_name: string;
  role: Role;
};

export type Me = {
  user: User;
  membership: Membership;
};

export type Member = {
  user_id: string;
  email: string;
  name: string | null;
  role: Role;
  joined_at: string;
};

export type Invite = {
  id: string;
  role: Role;
  email: string | null;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
};

export type InviteInput = { role: Role; email?: string; expires_in_hours?: number };

export type InvitePreview = { household_name: string; role: Role };

export type VehicleStatus = "active" | "parked" | "sold" | "archived";

export type Vehicle = {
  id: string;
  name: string;
  type: string | null;
  make: string | null;
  model: string | null;
  year: number | null;
  license_plate: string | null;
  vin: string | null;
  photo_url: string | null;
  distance_unit: "km" | "mi";
  status: VehicleStatus;
  created_at: string;
  updated_at: string;
};

export type VehicleInput = {
  name: string;
  type?: string | null;
  make?: string | null;
  model?: string | null;
  year?: number | null;
  license_plate?: string | null;
  vin?: string | null;
  distance_unit?: "km" | "mi";
};

export type OdometerReading = {
  id: string;
  vehicle_id: string;
  recorded_on: string;
  reading: number;
  start_reading: number | null;
  distance: number | null;
  is_adjustment: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type OdometerReadingInput = {
  recorded_on: string;
  reading: number;
  start_reading?: number;
  is_adjustment?: boolean;
  notes?: string;
};

export type FuelRecord = {
  id: string;
  vehicle_id: string;
  recorded_on: string;
  odometer_reading: number | null;
  volume_litres: string;
  total_price: string;
  unit_price: string;
  fuel_type: string | null;
  station: string | null;
  full_tank: boolean;
  excluded_from_consumption: boolean;
  consumption_l_per_100km: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type FuelRecordInput = {
  recorded_on: string;
  odometer_reading?: number;
  volume_litres?: string;
  total_price?: string;
  unit_price?: string;
  fuel_type?: string;
  station?: string;
  full_tank?: boolean;
  excluded_from_consumption?: boolean;
  notes?: string;
};

export type WorkKind = "maintenance" | "repair" | "modification";

export type WorkRecord = {
  id: string;
  vehicle_id: string;
  recorded_on: string;
  kind: WorkKind;
  description: string;
  odometer_reading: number | null;
  total_cost: string | null;
  supplier: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkRecordInput = {
  recorded_on: string;
  kind: WorkKind;
  description: string;
  odometer_reading?: number;
  total_cost?: string;
  supplier?: string;
  notes?: string;
};

export type ExpenseStatus = "planned" | "pending" | "paid" | "cancelled";

export type ExpenseRecord = {
  id: string;
  vehicle_id: string;
  issued_on: string;
  category: string;
  amount: string;
  supplier: string | null;
  status: ExpenseStatus;
  created_at: string;
};

export type ExpenseRecordInput = {
  issued_on: string;
  category: string;
  amount: string;
  supplier?: string;
  status: ExpenseStatus;
};

export type ReminderUrgency = "future" | "upcoming" | "urgent" | "very_urgent" | "overdue" | "completed";

export type Reminder = {
  id: string;
  vehicle_id: string;
  title: string;
  due_date: string | null;
  due_odometer: number | null;
  repeat_days: number | null;
  repeat_distance: number | null;
  notes: string | null;
  status: string;
  urgency: ReminderUrgency;
  completed_at: string | null;
  created_at: string;
};

export type ReminderInput = {
  title: string;
  due_date?: string;
  due_odometer?: number;
  repeat_days?: number;
  repeat_distance?: number;
  notes?: string;
};

export type Note = {
  id: string;
  vehicle_id: string;
  title: string;
  content: string;
  pinned: boolean;
  created_at: string;
  updated_at: string;
};

export type NoteInput = { title: string; content: string; pinned?: boolean };

export type Attachment = {
  id: string;
  vehicle_id: string;
  filename: string;
  content_type: string;
  size: number;
  checksum: string;
  created_at: string;
};
