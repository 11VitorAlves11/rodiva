import { errorFrom, request } from "./client";
import type {
  Attachment,
  ApiKey,
  AuditPage,
  ApiKeyInput,
  ChargingInput,
  ChargingRecord,
  AuthSession,
  Membership,
  User,
  BulkItem,
  BulkOperationInput,
  BulkOperationResult,
  CalendarFeedCreated,
  CalendarFeedStatus,
  GoogleCalendarAuthorizeUrl,
  GoogleCalendarConnectionInput,
  GoogleCalendarOption,
  GoogleCalendarStatus,
  ExpenseRecord,
  ExpenseRecordInput,
  Equipment,
  EquipmentEventInput,
  EquipmentInput,
  FuelRecord,
  FuelRecordInput,
  Invite,
  InviteInput,
  InvitePreview,
  InventoryItem,
  InventoryItemInput,
  Inspection,
  InspectionInput,
  InspectionTemplate,
  InspectionTemplateInput,
  Me,
  Member,
  Note,
  NoteInput,
  NotificationPage,
  NotificationPreference,
  NotificationRun,
  OdometerReading,
  TrashEntity,
  TrashItem,
  Webhook,
  WebhookDelivery,
  WebhookInput,
  OdometerReadingInput,
  Plan,
  PlanCompleteInput,
  PlanInput,
  Reminder,
  ReminderInput,
  ReminderUpdateInput,
  ReportSummary,
  SavedView,
  SavedViewInput,
  CustomField,
  CustomFieldInput,
  CustomFieldValues,
  InstanceStatus,
  PushKey,
  PushSubscriptionRow,
  SearchQuery,
  Tag,
  TagInput,
  TaggableKind,
  TagUsage,
  SearchResult,
  Role,
  StockMovement,
  MovementKind,
  Vehicle,
  VehicleInput,
  WorkRecord,
  WorkRecordInput,
} from "./types";

export const auth = {
  options: () =>
    request<{ registration: boolean; password_recovery: boolean; oidc: boolean }>(
      "/auth/options",
    ),
  forgotPassword: (email: string) => request<void>("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (token: string, password: string) => request<void>("/auth/reset-password", { method: "POST", body: { token, password } }),
  me: () => request<Me>("/auth/me"),
  profile: (body: Partial<Pick<User, "name" | "locale" | "timezone">>) => request<User>("/auth/profile", { method: "PATCH", body }),
  sessions: () => request<AuthSession[]>("/auth/sessions"),
  revokeSession: (id: string) => request<void>(`/auth/sessions/${id}`, { method: "DELETE" }),
  logoutAll: () => request<void>("/auth/logout-all", { method: "POST" }),
  changePassword: (body: { current_password: string; new_password: string }) => request<void>("/auth/password", { method: "POST", body }),
  households: () => request<Membership[]>("/auth/households"),
  activateHousehold: (id: string) => request<Me>(`/auth/households/${id}/activate`, { method: "POST" }),
  register: (body: { email: string; password: string; name?: string; household_name?: string; invite_token?: string }) =>
    request<Me>("/auth/register", { method: "POST", body }),
  login: (body: { email: string; password: string }) =>
    request<Me>("/auth/login", { method: "POST", body }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  previewInvite: (token: string) => request<InvitePreview>(`/auth/invites/${token}`),
  acceptInvite: (token: string) => request<Me>(`/auth/invites/${token}/accept`, { method: "POST" }),
};

export const household = {
  members: () => request<Member[]>("/api/household/members"),
  updateMemberRole: (userId: string, role: Role) =>
    request<Member>(`/api/household/members/${userId}`, { method: "PATCH", body: { role } }),
  removeMember: (userId: string) => request<void>(`/api/household/members/${userId}`, { method: "DELETE" }),
  invites: () => request<Invite[]>("/api/household/invites"),
  createInvite: (body: InviteInput) => request<Invite>("/api/household/invites", { method: "POST", body }),
  revokeInvite: (id: string) => request<void>(`/api/household/invites/${id}`, { method: "DELETE" }),
};

export const vehicles = {
  list: () => request<Vehicle[]>("/api/vehicles"),
  create: (body: VehicleInput) => request<Vehicle>("/api/vehicles", { method: "POST", body }),
  get: (id: string) => request<Vehicle>(`/api/vehicles/${id}`),
  update: (id: string, body: Partial<VehicleInput> & { status?: Vehicle["status"] }) =>
    request<Vehicle>(`/api/vehicles/${id}`, { method: "PATCH", body }),
  remove: (id: string) => request<void>(`/api/vehicles/${id}`, { method: "DELETE" }),
  uploadPhoto: (id: string, body: { content_base64: string; content_type: string }) =>
    request<Vehicle>(`/api/vehicles/${id}/photo`, { method: "POST", body }),
  /** Positions come from the list order, so two vehicles cannot claim one slot. */
  reorder: (vehicleIds: string[]) =>
    request<void>("/api/vehicles/order", { method: "PUT", body: { vehicle_ids: vehicleIds } }),
};

export const odometer = {
  list: (vehicleId: string) => request<OdometerReading[]>(`/api/vehicles/${vehicleId}/odometer-readings`),
  create: (vehicleId: string, body: OdometerReadingInput) =>
    request<OdometerReading>(`/api/vehicles/${vehicleId}/odometer-readings`, { method: "POST", body }),
  remove: (vehicleId: string, id: string) =>
    request<void>(`/api/vehicles/${vehicleId}/odometer-readings/${id}`, { method: "DELETE" }),
};

export const fuel = {
  list: (vehicleId: string) => request<FuelRecord[]>(`/api/vehicles/${vehicleId}/fuel-records`),
  create: (vehicleId: string, body: FuelRecordInput) =>
    request<FuelRecord>(`/api/vehicles/${vehicleId}/fuel-records`, { method: "POST", body }),
  update: (vehicleId: string, id: string, body: Partial<FuelRecordInput>) =>
    request<FuelRecord>(`/api/vehicles/${vehicleId}/fuel-records/${id}`, { method: "PATCH", body }),
  remove: (vehicleId: string, id: string) =>
    request<void>(`/api/vehicles/${vehicleId}/fuel-records/${id}`, { method: "DELETE" }),
};

export const workRecords = {
  list: (vehicleId: string) => request<WorkRecord[]>(`/api/vehicles/${vehicleId}/work-records`),
  create: (vehicleId: string, body: WorkRecordInput) =>
    request<WorkRecord>(`/api/vehicles/${vehicleId}/work-records`, { method: "POST", body }),
  update: (vehicleId: string, id: string, body: Partial<WorkRecordInput>) =>
    request<WorkRecord>(`/api/vehicles/${vehicleId}/work-records/${id}`, { method: "PATCH", body }),
  remove: (vehicleId: string, id: string) =>
    request<void>(`/api/vehicles/${vehicleId}/work-records/${id}`, { method: "DELETE" }),
};

export const expenses = {
  list: (vehicleId: string) => request<ExpenseRecord[]>(`/api/vehicles/${vehicleId}/expenses`),
  create: (vehicleId: string, body: ExpenseRecordInput) =>
    request<ExpenseRecord>(`/api/vehicles/${vehicleId}/expenses`, { method: "POST", body }),
  update: (vehicleId: string, id: string, body: Partial<ExpenseRecordInput>) =>
    request<ExpenseRecord>(`/api/vehicles/${vehicleId}/expenses/${id}`, { method: "PATCH", body }),
  remove: (vehicleId: string, id: string) =>
    request<void>(`/api/vehicles/${vehicleId}/expenses/${id}`, { method: "DELETE" }),
  nextOccurrence: (vehicleId: string, id: string) =>
    request<ExpenseRecord>(`/api/vehicles/${vehicleId}/expenses/${id}/next-occurrence`, {
      method: "POST",
    }),
};

export const reminders = {
  list: (vehicleId: string) => request<Reminder[]>(`/api/vehicles/${vehicleId}/reminders`),
  create: (vehicleId: string, body: ReminderInput) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/reminders`, { method: "POST", body }),
  update: (vehicleId: string, reminderId: string, body: ReminderUpdateInput) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/reminders/${reminderId}`, { method: "PATCH", body }),
  complete: (vehicleId: string, reminderId: string) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/reminders/${reminderId}/complete`, {
      method: "POST",
    }),
  reopen: (vehicleId: string, reminderId: string) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/reminders/${reminderId}/reopen`, {
      method: "POST",
    }),
  remove: (vehicleId: string, reminderId: string) =>
    request<void>(`/api/vehicles/${vehicleId}/reminders/${reminderId}`, { method: "DELETE" }),
};

export const plans = {
  list: (vehicleId: string) => request<Plan[]>(`/api/vehicles/${vehicleId}/plans`),
  create: (vehicleId: string, body: PlanInput) =>
    request<Plan>(`/api/vehicles/${vehicleId}/plans`, { method: "POST", body }),
  update: (vehicleId: string, planId: string, body: Partial<PlanInput>) =>
    request<Plan>(`/api/vehicles/${vehicleId}/plans/${planId}`, { method: "PATCH", body }),
  complete: (vehicleId: string, planId: string, body: PlanCompleteInput) =>
    request<Plan>(`/api/vehicles/${vehicleId}/plans/${planId}/complete`, { method: "POST", body }),
  remove: (vehicleId: string, planId: string) =>
    request<void>(`/api/vehicles/${vehicleId}/plans/${planId}`, { method: "DELETE" }),
};

export const calendarFeed = {
  status: () => request<CalendarFeedStatus>("/api/calendar-feed"),
  create: () => request<CalendarFeedCreated>("/api/calendar-feed", { method: "POST" }),
  revoke: () => request<void>("/api/calendar-feed", { method: "DELETE" }),
};

export const googleCalendar = {
  status: () => request<GoogleCalendarStatus>("/api/calendar/google/status"),
  connect: () => request<GoogleCalendarAuthorizeUrl>("/api/calendar/google/connect"),
  calendars: () => request<GoogleCalendarOption[]>("/api/calendar/google/calendars"),
  saveConnection: (body: GoogleCalendarConnectionInput) =>
    request<GoogleCalendarStatus>("/api/calendar/google/connection", { method: "POST", body }),
  disconnect: () => request<void>("/api/calendar/google/connection", { method: "DELETE" }),
};

export const inventory = {
  list: () => request<InventoryItem[]>("/api/inventory"),
  create: (body: InventoryItemInput) => request<InventoryItem>("/api/inventory", { method: "POST", body }),
  update: (id: string, body: Partial<InventoryItemInput>) =>
    request<InventoryItem>(`/api/inventory/${id}`, { method: "PATCH", body }),
  remove: (id: string) => request<void>(`/api/inventory/${id}`, { method: "DELETE" }),
  movements: (id: string) => request<StockMovement[]>(`/api/inventory/${id}/movements`),
  move: (id: string, body: { kind: MovementKind; quantity: string; notes?: string }) =>
    request<StockMovement>(`/api/inventory/${id}/movements`, { method: "POST", body }),
};

export const equipment = {
  list: (vehicleId: string) => request<Equipment[]>(`/api/vehicles/${vehicleId}/equipment`),
  create: (vehicleId: string, body: EquipmentInput) => request<Equipment>(`/api/vehicles/${vehicleId}/equipment`, { method: "POST", body }),
  update: (vehicleId: string, id: string, body: Partial<EquipmentInput>) => request<Equipment>(`/api/vehicles/${vehicleId}/equipment/${id}`, { method: "PATCH", body }),
  remove: (vehicleId: string, id: string) => request<void>(`/api/vehicles/${vehicleId}/equipment/${id}`, { method: "DELETE" }),
  mount: (vehicleId: string, id: string, body: EquipmentEventInput) => request(`/api/vehicles/${vehicleId}/equipment/${id}/mount`, { method: "POST", body }),
  unmount: (vehicleId: string, id: string, body: EquipmentEventInput) => request(`/api/vehicles/${vehicleId}/equipment/${id}/unmount`, { method: "POST", body }),
  rotate: (vehicleId: string, id: string, body: EquipmentEventInput) => request(`/api/vehicles/${vehicleId}/equipment/${id}/rotate`, { method: "POST", body }),
  reminders: (vehicleId: string, id: string) => request<Reminder[]>(`/api/vehicles/${vehicleId}/equipment/${id}/reminders`),
  createReminder: (vehicleId: string, id: string, body: ReminderInput) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/equipment/${id}/reminders`, { method: "POST", body }),
};

export const inspections = {
  templates: () => request<InspectionTemplate[]>("/api/inspection-templates"),
  createTemplate: (body: InspectionTemplateInput) =>
    request<InspectionTemplate>("/api/inspection-templates", { method: "POST", body }),
  versionTemplate: (id: string, body: InspectionTemplateInput) =>
    request<InspectionTemplate>(`/api/inspection-templates/${id}`, { method: "PATCH", body }),
  duplicateTemplate: (id: string) =>
    request<InspectionTemplate>(`/api/inspection-templates/${id}/duplicate`, { method: "POST" }),
  list: (vehicleId: string) => request<Inspection[]>(`/api/vehicles/${vehicleId}/inspections`),
  create: (vehicleId: string, body: InspectionInput) =>
    request<Inspection>(`/api/vehicles/${vehicleId}/inspections`, { method: "POST", body }),
  update: (vehicleId: string, id: string, body: Partial<Omit<InspectionInput, "template_id">>) =>
    request<Inspection>(`/api/vehicles/${vehicleId}/inspections/${id}`, { method: "PATCH", body }),
  complete: (vehicleId: string, id: string) =>
    request<Inspection>(`/api/vehicles/${vehicleId}/inspections/${id}/complete`, { method: "POST" }),
};

export const reports = {
  summary: (query: string) => request<ReportSummary>(`/api/reports/summary${query}`),
  csvUrl: (query: string) => `/api/reports/export.csv${query}`,
};

function searchQueryString(query: SearchQuery): string {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  for (const value of query.kind ?? []) params.append("kind", value);
  for (const value of query.vehicle_id ?? []) params.append("vehicle_id", value);
  for (const value of query.tag_id ?? []) params.append("tag_id", value);
  if (query.date_from) params.set("date_from", query.date_from);
  if (query.date_to) params.set("date_to", query.date_to);
  if (query.sort) params.set("sort", query.sort);
  return params.toString();
}

export const search = {
  query: (query: SearchQuery) => request<SearchResult[]>(`/api/search?${searchQueryString(query)}`),
  savedViews: {
    list: () => request<SavedView[]>("/api/search/saved-views"),
    create: (body: SavedViewInput) =>
      request<SavedView>("/api/search/saved-views", { method: "POST", body }),
    remove: (id: string) => request<void>(`/api/search/saved-views/${id}`, { method: "DELETE" }),
  },
  bulk: (body: BulkOperationInput) =>
    request<BulkOperationResult>("/api/search/bulk", { method: "POST", body }),
  exportCsv: async (items: BulkItem[]): Promise<Blob> => {
    const response = await fetch("/api/search/bulk", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation: "export", items }),
    });
    if (!response.ok) throw await errorFrom(response);
    return response.blob();
  },
};

export const admin = {
  status: () => request<InstanceStatus>("/api/admin/status"),
};

export const customFields = {
  list: (recordKind?: string) =>
    request<CustomField[]>(
      recordKind ? `/api/custom-fields?record_kind=${recordKind}` : "/api/custom-fields",
    ),
  create: (body: CustomFieldInput) =>
    request<CustomField>("/api/custom-fields", { method: "POST", body }),
  update: (id: string, body: Partial<CustomFieldInput> & { archived?: boolean }) =>
    request<CustomField>(`/api/custom-fields/${id}`, { method: "PATCH", body }),
  valuesFor: (kind: string, recordId: string) =>
    request<CustomFieldValues>(`/api/custom-fields/records/${kind}/${recordId}`),
  setValues: (kind: string, recordId: string, values: CustomFieldValues) =>
    request<CustomFieldValues>(`/api/custom-fields/records/${kind}/${recordId}`, {
      method: "PUT",
      body: { values },
    }),
};

export const push = {
  key: () => request<PushKey>("/api/push/key"),
  list: () => request<PushSubscriptionRow[]>("/api/push"),
  subscribe: (body: { endpoint: string; p256dh: string; auth: string }) =>
    request<PushSubscriptionRow>("/api/push", { method: "POST", body }),
  unsubscribe: (endpoint: string) =>
    request<void>("/api/push", { method: "DELETE", body: { endpoint, p256dh: "x", auth: "x" } }),
};

export const tags = {
  list: () => request<TagUsage[]>("/api/tags"),
  create: (body: TagInput) => request<Tag>("/api/tags", { method: "POST", body }),
  update: (id: string, body: Partial<TagInput>) =>
    request<Tag>(`/api/tags/${id}`, { method: "PATCH", body }),
  remove: (id: string) => request<void>(`/api/tags/${id}`, { method: "DELETE" }),
  forRecord: (kind: TaggableKind, recordId: string) =>
    request<Tag[]>(`/api/tags/records/${kind}/${recordId}`),
  setForRecord: (kind: TaggableKind, recordId: string, tagIds: string[]) =>
    request<Tag[]>(`/api/tags/records/${kind}/${recordId}`, {
      method: "PUT",
      body: { tag_ids: tagIds },
    }),
};

export const notes = {
  list: (vehicleId: string) => request<Note[]>(`/api/vehicles/${vehicleId}/notes`),
  create: (vehicleId: string, body: NoteInput) =>
    request<Note>(`/api/vehicles/${vehicleId}/notes`, { method: "POST", body }),
  update: (vehicleId: string, id: string, body: Partial<NoteInput>) =>
    request<Note>(`/api/vehicles/${vehicleId}/notes/${id}`, { method: "PATCH", body }),
  remove: (vehicleId: string, id: string) =>
    request<void>(`/api/vehicles/${vehicleId}/notes/${id}`, { method: "DELETE" }),
};

export const attachments = {
  list: (vehicleId: string) => request<Attachment[]>(`/api/vehicles/${vehicleId}/attachments`),
  create: (vehicleId: string, body: { filename: string; content_type: string; content_base64: string }) =>
    request<Attachment>(`/api/vehicles/${vehicleId}/attachments`, { method: "POST", body }),
  downloadUrl: (vehicleId: string, attachmentId: string) =>
    `/api/vehicles/${vehicleId}/attachments/${attachmentId}/download`,
  remove: (vehicleId: string, id: string) =>
    request<void>(`/api/vehicles/${vehicleId}/attachments/${id}`, { method: "DELETE" }),
};

export type ImportKind = "fuel" | "work" | "expenses" | "odometer" | "notes";
export type ImportInput = { vehicle_id: string; kind: ImportKind; csv_text: string; mapping: Record<string, string>; locale: "pt-PT" | "en" };
export type ImportPreview = { columns: string[]; fields: string[]; rows: { line: number; data: Record<string, string | number | boolean | null>; errors: string[] }[]; errors: string[]; imported: number; already_imported?: boolean };
export const imports = {
  preview: (body: ImportInput) => request<ImportPreview>("/api/imports/preview", { method: "POST", body }),
  commit: (body: ImportInput) => request<ImportPreview>("/api/imports/commit", { method: "POST", body }),
};

export const charging = {
  list: (vehicle: string) => request<ChargingRecord[]>(`/api/vehicles/${vehicle}/charging-records`),
  create: (vehicle: string, body: ChargingInput) => request<ChargingRecord>(`/api/vehicles/${vehicle}/charging-records`, { method: "POST", body }),
  update: (vehicle: string, id: string, body: ChargingInput) => request<ChargingRecord>(`/api/vehicles/${vehicle}/charging-records/${id}`, { method: "PATCH", body }),
  remove: (vehicle: string, id: string) => request<void>(`/api/vehicles/${vehicle}/charging-records/${id}`, { method: "DELETE" }),
};

export const notifications = {
  list: (unreadOnly = false) => request<NotificationPage>(`/api/v1/notifications${unreadOnly ? "?unread_only=true" : ""}`),
  markRead: (id: string) => request<void>(`/api/v1/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => request<void>("/api/v1/notifications/read-all", { method: "POST" }),
  preferences: () => request<NotificationPreference>("/api/v1/notifications/preferences"),
  savePreferences: (body: NotificationPreference) => request<NotificationPreference>("/api/v1/notifications/preferences", { method: "PUT", body }),
  run: () => request<NotificationRun>("/api/v1/notifications/run", { method: "POST" }),
};

export const webhooks = {
  list: () => request<Webhook[]>("/api/v1/webhooks"),
  create: (body: WebhookInput) => request<Webhook & { secret: string }>("/api/v1/webhooks", { method: "POST", body }),
  update: (id: string, body: Partial<WebhookInput> & { active?: boolean }) => request<Webhook>(`/api/v1/webhooks/${id}`, { method: "PATCH", body }),
  remove: (id: string) => request<void>(`/api/v1/webhooks/${id}`, { method: "DELETE" }),
  test: (id: string) => request<WebhookDelivery>(`/api/v1/webhooks/${id}/test`, { method: "POST" }),
  deliveries: (id: string) => request<WebhookDelivery[]>(`/api/v1/webhooks/${id}/deliveries`),
  retry: (id: string, deliveryId: string) => request<WebhookDelivery>(`/api/v1/webhooks/${id}/deliveries/${deliveryId}/retry`, { method: "POST" }),
};

export const trash = {
  list: () => request<TrashItem[]>("/api/v1/trash"),
  restore: (entity: TrashEntity, id: string) => request<void>(`/api/v1/trash/${entity}/${id}/restore`, { method: "POST" }),
  purge: (entity: TrashEntity, id: string) => request<void>(`/api/v1/trash/${entity}/${id}`, { method: "DELETE" }),
};

export const audit = {
  list: (before?: string) => request<AuditPage>(`/api/v1/audit${before ? `?before=${encodeURIComponent(before)}` : ""}`),
};

export const apiKeys = {
  list: () => request<ApiKey[]>("/api/api-keys"),
  create: (body: ApiKeyInput) => request<ApiKey & { token: string }>("/api/api-keys", { method: "POST", body }),
  revoke: (id: string) => request<void>(`/api/api-keys/${id}`, { method: "DELETE" }),
};
