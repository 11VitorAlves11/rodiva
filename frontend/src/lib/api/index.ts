import { request } from "./client";
import type {
  Attachment,
  ExpenseRecord,
  ExpenseRecordInput,
  FuelRecord,
  FuelRecordInput,
  Invite,
  InviteInput,
  InvitePreview,
  Me,
  Member,
  Note,
  NoteInput,
  OdometerReading,
  OdometerReadingInput,
  Reminder,
  ReminderInput,
  Role,
  Vehicle,
  VehicleInput,
  WorkRecord,
  WorkRecordInput,
} from "./types";

export const auth = {
  me: () => request<Me>("/auth/me"),
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
  uploadPhoto: (id: string, body: { content_base64: string; content_type: string }) =>
    request<Vehicle>(`/api/vehicles/${id}/photo`, { method: "POST", body }),
};

export const odometer = {
  list: (vehicleId: string) => request<OdometerReading[]>(`/api/vehicles/${vehicleId}/odometer-readings`),
  create: (vehicleId: string, body: OdometerReadingInput) =>
    request<OdometerReading>(`/api/vehicles/${vehicleId}/odometer-readings`, { method: "POST", body }),
};

export const fuel = {
  list: (vehicleId: string) => request<FuelRecord[]>(`/api/vehicles/${vehicleId}/fuel-records`),
  create: (vehicleId: string, body: FuelRecordInput) =>
    request<FuelRecord>(`/api/vehicles/${vehicleId}/fuel-records`, { method: "POST", body }),
};

export const workRecords = {
  list: (vehicleId: string) => request<WorkRecord[]>(`/api/vehicles/${vehicleId}/work-records`),
  create: (vehicleId: string, body: WorkRecordInput) =>
    request<WorkRecord>(`/api/vehicles/${vehicleId}/work-records`, { method: "POST", body }),
};

export const expenses = {
  list: (vehicleId: string) => request<ExpenseRecord[]>(`/api/vehicles/${vehicleId}/expenses`),
  create: (vehicleId: string, body: ExpenseRecordInput) =>
    request<ExpenseRecord>(`/api/vehicles/${vehicleId}/expenses`, { method: "POST", body }),
};

export const reminders = {
  list: (vehicleId: string) => request<Reminder[]>(`/api/vehicles/${vehicleId}/reminders`),
  create: (vehicleId: string, body: ReminderInput) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/reminders`, { method: "POST", body }),
  complete: (vehicleId: string, reminderId: string) =>
    request<Reminder>(`/api/vehicles/${vehicleId}/reminders/${reminderId}/complete`, {
      method: "POST",
    }),
};

export const notes = {
  list: (vehicleId: string) => request<Note[]>(`/api/vehicles/${vehicleId}/notes`),
  create: (vehicleId: string, body: NoteInput) =>
    request<Note>(`/api/vehicles/${vehicleId}/notes`, { method: "POST", body }),
};

export const attachments = {
  list: (vehicleId: string) => request<Attachment[]>(`/api/vehicles/${vehicleId}/attachments`),
  create: (vehicleId: string, body: { filename: string; content_type: string; content_base64: string }) =>
    request<Attachment>(`/api/vehicles/${vehicleId}/attachments`, { method: "POST", body }),
  downloadUrl: (vehicleId: string, attachmentId: string) =>
    `/api/vehicles/${vehicleId}/attachments/${attachmentId}/download`,
};
