export type Role = "owner" | "manager" | "editor" | "reader";

export type User = {
  id: string;
  email: string;
  name: string | null;
  locale: string;
  timezone: string;
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
  equipment_id: string | null;
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

export type ReminderUpdateInput = {
  title?: string;
  due_date?: string | null;
  due_odometer?: number | null;
  repeat_days?: number | null;
  repeat_distance?: number | null;
  notes?: string | null;
};

export type PlanStage = "planned" | "in_progress" | "testing" | "completed";
export type PlanPriority = "low" | "normal" | "high" | "urgent";

export type Plan = {
  id: string;
  vehicle_id: string;
  stage: PlanStage;
  kind: WorkKind;
  priority: PlanPriority;
  description: string;
  estimated_cost: string | null;
  due_date: string | null;
  due_odometer: number | null;
  notes: string | null;
  completed_work_record_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PlanInput = {
  kind: WorkKind;
  description: string;
  priority?: PlanPriority;
  stage?: Exclude<PlanStage, "completed">;
  estimated_cost?: string | null;
  due_date?: string | null;
  due_odometer?: number | null;
  notes?: string | null;
};

export type PlanCompleteInput = {
  recorded_on: string;
  odometer_reading: number;
  total_cost?: string;
  supplier?: string;
  notes?: string;
  inventory_items?: Array<{ item_id: string; quantity: string }>;
};

export type CalendarFeedStatus = {
  active: boolean;
  created_at: string | null;
};

export type CalendarFeedCreated = CalendarFeedStatus & {
  token: string;
  feed_path: string;
};

export type GoogleCalendarStatus = {
  configured: boolean;
  connected: boolean;
  google_account_email: string | null;
  calendar_id: string | null;
  synced_vehicle_ids: string[];
  status: string | null;
  last_error: string | null;
};

export type GoogleCalendarAuthorizeUrl = { authorize_url: string };

export type GoogleCalendarOption = { id: string; summary: string };

export type GoogleCalendarConnectionInput = { calendar_id: string; vehicle_ids: string[] };

export type InventoryItem = {
  id: string;
  household_id: string;
  vehicle_id: string | null;
  name: string;
  reference: string | null;
  manufacturer: string | null;
  quantity: string;
  unit: string;
  unit_cost: string | null;
  minimum_quantity: string | null;
  location: string | null;
  supplier: string | null;
  notes: string | null;
  low_stock: boolean;
  created_at: string;
  updated_at: string;
};

export type InventoryItemInput = {
  name: string;
  vehicle_id?: string | null;
  reference?: string | null;
  manufacturer?: string | null;
  quantity?: string;
  unit?: string;
  unit_cost?: string | null;
  minimum_quantity?: string | null;
  location?: string | null;
  supplier?: string | null;
  notes?: string | null;
};

export type MovementKind = "entry" | "adjustment" | "requisition" | "return" | "removal";

export type StockMovement = {
  id: string;
  item_id: string;
  kind: MovementKind;
  quantity_delta: string;
  quantity_after: string;
  notes: string | null;
  created_at: string;
};

export type EquipmentKind = "tires" | "trailer" | "roof_rack" | "accessory" | "other";
export type EquipmentStatus = "mounted" | "unmounted" | "stored" | "sold" | "discarded";
export type Equipment = {
  id: string; vehicle_id: string; name: string; kind: EquipmentKind; status: EquipmentStatus;
  manufacturer: string | null; model: string | null; serial_number: string | null;
  tire_size: string | null; tire_dot: string | null; tread_depth_mm: string | null;
  season: "summer" | "winter" | "all_season" | null; positions: Record<string, string> | null;
  distance_accumulated: number; open_reminders_count: number; notes: string | null; created_at: string; updated_at: string;
};
export type EquipmentInput = {
  name: string; kind: EquipmentKind; manufacturer?: string; model?: string;
  serial_number?: string; tire_size?: string; tire_dot?: string; tread_depth_mm?: string;
  season?: "summer" | "winter" | "all_season"; notes?: string;
};
export type EquipmentEventInput = { on: string; odometer: number; positions?: Record<string, string> };

export type InspectionFieldType = "text" | "number" | "date" | "single" | "multiple" | "boolean" | "photo" | "note";
export type InspectionField = {
  id: string;
  label: string;
  type: InspectionFieldType;
  required: boolean;
  options: string[];
  failure_values: Array<string | boolean>;
  create_plan_on_failure: boolean;
};
export type InspectionTemplate = {
  id: string;
  household_id: string;
  vehicle_id: string | null;
  name: string;
  version: number;
  fields: InspectionField[];
  archived: boolean;
  created_at: string;
};
export type InspectionTemplateInput = Pick<InspectionTemplate, "name" | "vehicle_id" | "fields">;
export type Inspection = {
  id: string;
  vehicle_id: string;
  template_id: string;
  template_snapshot: { name: string; version: number; fields: InspectionField[] };
  responses: Record<string, unknown>;
  status: "draft" | "completed";
  result: "passed" | "passed_with_observations" | "failed" | null;
  recorded_on: string;
  odometer: number | null;
  notes: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};
export type InspectionInput = {
  template_id: string;
  recorded_on: string;
  odometer?: number | null;
  responses?: Record<string, unknown>;
  notes?: string | null;
};

export type CategoryTotal = { category: string; amount: string };
export type MonthlyTotal = { month: string; fuel: string; charging: string; work: string; expenses: string; total: string; distance: number };
export type VehicleReport = {
  vehicle_id: string;
  vehicle_name: string;
  distance_unit: string;
  total_cost: string;
  distance: number;
  cost_per_distance: string | null;
  consumption_average: string | null;
  consumption_minimum: string | null;
  consumption_maximum: string | null;
  categories: CategoryTotal[];
  monthly: MonthlyTotal[];
};
export type ReportSummary = {
  date_from: string | null;
  date_to: string | null;
  currency: string;
  total_cost: string;
  total_distance: number;
  inventory_value: string;
  overdue_reminders: number;
  vehicles: VehicleReport[];
};
export type SearchKind = "vehicle" | "fuel" | "work" | "expense" | "note" | "plan" | "inventory" | "equipment" | "inspection";
export type SearchResult = {
  id: string;
  kind: SearchKind;
  title: string;
  subtitle: string | null;
  vehicle_id: string | null;
  occurred_on: string | null;
  url: string;
  tags: Tag[];
};

/** The record kinds a tag can sit on (RF-DOC-009). */
export type TaggableKind =
  | "vehicle"
  | "odometer"
  | "fuel"
  | "work"
  | "expense"
  | "note"
  | "plan"
  | "inspection";

export type Tag = {
  id: string;
  name: string;
  color: string;
  created_at: string;
};

/** A tag plus how many records carry it, for the management screen. */
export type TagUsage = Tag & { record_count: number };

export type TagInput = {
  name: string;
  color?: string;
};

export type SearchSort = "occurred_on_desc" | "occurred_on_asc" | "title_asc" | "title_desc";

export type SearchQuery = {
  q?: string;
  kind?: SearchKind[];
  vehicle_id?: string[];
  tag_id?: string[];
  date_from?: string;
  date_to?: string;
  sort?: SearchSort;
};

export type SavedView = {
  id: string;
  household_id: string;
  created_by: string;
  name: string;
  query: Record<string, unknown>;
  created_at: string;
};

export type SavedViewInput = { name: string; query: Record<string, unknown> };

export type BulkOperation = "delete" | "duplicate" | "move" | "edit" | "export";
export type BulkItem = { kind: SearchKind; id: string };
export type BulkOperationInput = {
  operation: BulkOperation;
  items: BulkItem[];
  target_vehicle_id?: string;
  fields?: Record<string, unknown>;
};
export type BulkFailure = { kind: SearchKind; id: string; reason: string };
export type BulkOperationResult = { requested: number; succeeded: number; failures: BulkFailure[] };

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

export type AuthSession = {
  id: string;
  user_agent: string;
  created_at: string;
  expires_at: string;
  current: boolean;
};

export type ChargingInput = {
  recorded_on: string;
  odometer_reading?: number | null;
  energy_kwh: string;
  total_cost: string;
  soc_start?: number | null;
  soc_end?: number | null;
  location?: string | null;
  charger_type: string;
  notes?: string | null;
};
export type ChargingRecord = ChargingInput & { id: string; vehicle_id: string; unit_price: string; efficiency_kwh_per_100km: string | null; created_at: string };

export type ApiKey = { id: string; name: string; scope: "read" | "write"; vehicle_ids: string[]; expires_at: string; revoked_at: string | null; created_at: string };
export type ApiKeyInput = { name: string; scope: "read" | "write"; vehicle_ids: string[]; expires_in_days: number };

export type TrashEntity =
  | "vehicle"
  | "odometer_reading"
  | "fuel_record"
  | "charging_record"
  | "work_record"
  | "expense_record"
  | "note"
  | "attachment"
  | "plan"
  | "reminder";
export type TrashItem = { entity_type: TrashEntity; entity_id: string; vehicle_id: string | null; summary: string; deleted_at: string; deleted_by: string | null; deleted_by_label: string };
export type AuditEvent = { id: string; actor_user_id: string | null; actor_label: string; action: string; entity_type: string; entity_id: string | null; summary: string; context: Record<string, unknown> | null; created_at: string };
export type AuditPage = { items: AuditEvent[]; next_before: string | null };

export type NotificationItem = { id: string; kind: string; title: string; body: string; context: Record<string, string> | null; entity_type: string; entity_id: string | null; vehicle_id: string | null; created_at: string; read_at: string | null };
export type NotificationPage = { items: NotificationItem[]; unread: number };
export type NotificationUrgency = "overdue" | "very_urgent" | "urgent" | "upcoming" | "future";
export type NotificationPreference = { channel_inapp: boolean; channel_email: boolean; min_urgency: NotificationUrgency; vehicle_ids: string[]; quiet_hours_start: number | null; quiet_hours_end: number | null };
export type NotificationRun = { created: number; delivered: number; failed: number };

export type Webhook = { id: string; description: string; url: string; events: string[]; active: boolean; created_at: string; last_success_at: string | null; last_error: string };
export type WebhookInput = { description: string; url: string; events: string[] };
export type WebhookDelivery = { id: string; event: string; payload: Record<string, unknown>; status: string; attempts: number; next_attempt_at: string; response_status: number | null; last_error: string; created_at: string; delivered_at: string | null };
