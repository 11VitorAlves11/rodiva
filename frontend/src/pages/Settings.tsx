import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { googleCalendar, household, vehicles as vehiclesApi } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { GoogleCalendarOption, GoogleCalendarStatus, Invite, Member, Role, Vehicle } from "../lib/api/types";
import { useSession } from "../lib/session";
import { ApiKeySettings } from "../components/settings/ApiKeySettings";
import { AccountSettings } from "../components/settings/AccountSettings";

function initials(name: string | null | undefined, email: string) {
  const source = (name ?? email).trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function Settings() {
  const { t } = useTranslation();
  const { me, signOut } = useSession();
  const canManageMembers = me?.membership.role === "owner" || me?.membership.role === "manager";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-ink">{t("settings.title")}</h1>

      <section className="flex items-center gap-4 rounded-xl border border-line bg-raised p-5 shadow-sm">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-copper text-lg font-semibold text-white">
          {me ? initials(me.user.name, me.user.email) : ""}
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{me?.user.name ?? me?.user.email}</p>
          <p className="truncate text-sm text-ink-subtle">{me?.user.email}</p>
          <p className="mt-1 text-sm text-ink-subtle">{me?.membership.household_name}</p>
        </div>
      </section>

      <MembersSection canManage={canManageMembers} currentUserId={me?.user.id} />

      <GoogleCalendarSection />

      <AccountSettings />
      <ApiKeySettings />

      <button
        onClick={() => void signOut()}
        className="w-full rounded-lg border border-copper/30 px-4 py-3 text-sm font-semibold text-brand hover:bg-copper/5"
      >
        {t("common.signOut")}
      </button>
    </div>
  );
}

const roles: Role[] = ["owner", "manager", "editor", "reader"];

function MembersSection({ canManage, currentUserId }: { canManage: boolean; currentUserId: string | undefined }) {
  const { t } = useTranslation();
  const [members, setMembers] = useState<Member[] | null>(null);
  const [invites, setInvites] = useState<Invite[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [lastInviteLink, setLastInviteLink] = useState<string | null>(null);

  const load = () => {
    household.members().then(setMembers).catch((cause) => setError(cause instanceof ApiError ? cause.message : t("common.error")));
    if (canManage) {
      household.invites().then(setInvites).catch(() => setInvites([]));
    }
  };

  useEffect(load, [canManage, t]);

  async function changeRole(userId: string, role: Role) {
    setError(null);
    try {
      const updated = await household.updateMemberRole(userId, role);
      setMembers((current) => current?.map((member) => (member.user_id === userId ? updated : member)) ?? null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  async function remove(userId: string) {
    setError(null);
    try {
      await household.removeMember(userId);
      setMembers((current) => current?.filter((member) => member.user_id !== userId) ?? null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  async function revoke(inviteId: string) {
    try {
      await household.revokeInvite(inviteId);
      setInvites((current) => current?.filter((invite) => invite.id !== inviteId) ?? null);
    } catch {
      // The list will simply show it again on the next load if this failed.
    }
  }

  const pendingInvites = invites?.filter((invite) => !invite.accepted_at && !invite.revoked_at) ?? [];

  return (
    <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
      <div className="mb-4 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-semibold text-ink">{t("settings.members")}</h2>
        {canManage && (
          <button
            onClick={() => setShowInviteForm((value) => !value)}
            className="self-start rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
          >
            {t("settings.invite")}
          </button>
        )}
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      {showInviteForm && (
        <InviteForm
          onCreated={(invite) => {
            setInvites((current) => [invite, ...(current ?? [])]);
            setLastInviteLink(`${window.location.origin}/invite/${invite.token}`);
            setShowInviteForm(false);
          }}
        />
      )}

      {lastInviteLink && (
        <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg bg-copper/10 p-3 text-sm">
          <span className="font-medium text-brand">{t("settings.inviteReady")}</span>
          <code className="min-w-0 flex-1 truncate rounded bg-raised px-2 py-1 text-ink">
            {lastInviteLink}
          </code>
          <button
            onClick={() => void navigator.clipboard.writeText(lastInviteLink)}
            className="rounded-md border border-copper/30 px-2 py-1 text-xs font-medium text-copper"
          >
            {t("settings.copyLink")}
          </button>
        </div>
      )}

      {!members ? (
        <p className="text-sm text-ink-subtle">{t("common.loading")}</p>
      ) : (
        <ul className="divide-y divide-graphite/5 dark:divide-white/5">
          {members.map((member) => (
            <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{member.name ?? member.email}</p>
                <p className="truncate text-sm text-ink-subtle">{member.email}</p>
              </div>
              <div className="flex items-center gap-2">
                {canManage ? (
                  <select
                    value={member.role}
                    onChange={(event) => void changeRole(member.user_id, event.target.value as Role)}
                    className="rounded-md border border-line bg-raised px-2 py-1.5 text-sm"
                  >
                    {roles.map((role) => (
                      <option key={role} value={role}>{t(`settings.roles.${role}`)}</option>
                    ))}
                  </select>
                ) : (
                  <span className="rounded-full bg-graphite/5 px-3 py-1 text-xs font-medium text-ink-muted dark:bg-white/10">
                    {t(`settings.roles.${member.role}`)}
                  </span>
                )}
                {canManage && member.user_id !== currentUserId && (
                  <button onClick={() => void remove(member.user_id)} className="text-sm font-medium text-danger">
                    {t("settings.remove")}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {canManage && pendingInvites.length > 0 && (
        <div className="mt-5 border-t border-line pt-4">
          <h3 className="mb-2 text-sm font-semibold text-ink-muted">{t("settings.pendingInvites")}</h3>
          <ul className="space-y-2">
            {pendingInvites.map((invite) => (
              <li key={invite.id} className="flex flex-wrap items-center justify-between gap-3 text-sm">
                <span className="text-ink">
                  {invite.email ?? t(`settings.roles.${invite.role}`)}
                </span>
                <button onClick={() => void revoke(invite.id)} className="font-medium text-danger">
                  {t("settings.revoke")}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function InviteForm({ onCreated }: { onCreated: (invite: Invite) => void }) {
  const { t } = useTranslation();
  const [role, setRole] = useState<Role>("editor");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onCreated(await household.createInvite({ role, email: email || undefined }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="mb-4 grid gap-3 rounded-lg bg-graphite/5 p-4 dark:bg-white/5 sm:grid-cols-2">
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">{t("settings.role")}</span>
        <select
          value={role}
          onChange={(event) => setRole(event.target.value as Role)}
          className="w-full rounded-md border border-line bg-raised px-3 py-2"
        >
          {roles.filter((item) => item !== "owner").map((item) => (
            <option key={item} value={item}>{t(`settings.roles.${item}`)}</option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-ink-muted">{t("settings.inviteEmail")}</span>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-md border border-line px-3 py-2 bg-raised"
        />
      </label>
      {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
      <button
        type="submit"
        disabled={saving}
        className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60 sm:col-span-2"
      >
        {t("settings.createInvite")}
      </button>
    </form>
  );
}

function GoogleCalendarSection() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<GoogleCalendarStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [vehicleOptions, setVehicleOptions] = useState<Vehicle[] | null>(null);
  const [calendarOptions, setCalendarOptions] = useState<GoogleCalendarOption[] | null>(null);
  const [selectedCalendarId, setSelectedCalendarId] = useState("");
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  const loadStatus = () => {
    googleCalendar
      .status()
      .then(setStatus)
      .catch((cause) => setError(cause instanceof ApiError ? cause.message : t("common.error")));
  };

  useEffect(loadStatus, [t]);

  useEffect(() => {
    if (searchParams.get("google_calendar") !== "connected") return;
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("google_calendar");
      return next;
    });
    openPicker();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  async function openPicker() {
    setError(null);
    try {
      const [calendars, vehicleList] = await Promise.all([googleCalendar.calendars(), vehiclesApi.list()]);
      setCalendarOptions(calendars);
      setVehicleOptions(vehicleList);
      setSelectedCalendarId((current) => current || calendars[0]?.id || "");
      setShowPicker(true);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  function toggleVehicle(vehicleId: string) {
    setSelectedVehicleIds((current) => {
      const next = new Set(current);
      if (next.has(vehicleId)) next.delete(vehicleId);
      else next.add(vehicleId);
      return next;
    });
  }

  async function connect() {
    setError(null);
    try {
      const { authorize_url } = await googleCalendar.connect();
      window.location.href = authorize_url;
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  async function saveSelection() {
    if (!selectedCalendarId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await googleCalendar.saveConnection({
        calendar_id: selectedCalendarId,
        vehicle_ids: [...selectedVehicleIds],
      });
      setStatus(updated);
      setShowPicker(false);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    } finally {
      setSaving(false);
    }
  }

  async function changeSelection() {
    setSelectedVehicleIds(new Set(status?.synced_vehicle_ids ?? []));
    setSelectedCalendarId(status?.calendar_id ?? "");
    await openPicker();
  }

  async function disconnect() {
    setError(null);
    try {
      await googleCalendar.disconnect();
      setShowPicker(false);
      loadStatus();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("common.error"));
    }
  }

  if (!status) return null;

  return (
    <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
      <h2 className="mb-1 font-semibold text-ink">{t("calendar.google.title")}</h2>
      <p className="mb-4 text-sm text-ink-muted">{t("calendar.google.description")}</p>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      {!status.configured && (
        <p className="rounded-lg bg-graphite/5 p-3 text-sm text-ink-muted dark:bg-white/5">
          {t("calendar.google.notConfigured")}
        </p>
      )}

      {status.configured && !status.connected && !showPicker && (
        <button
          onClick={() => void connect()}
          className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark"
        >
          {t("calendar.google.connect")}
        </button>
      )}

      {status.configured && status.connected && !showPicker && (
        <div className="space-y-3">
          <div className="text-sm text-ink-muted">
            <p>
              <span className="font-medium text-ink">{t("calendar.google.account")}: </span>
              {status.google_account_email}
            </p>
            {status.calendar_id && (
              <p>
                <span className="font-medium text-ink">{t("calendar.google.calendarLabel")}: </span>
                {status.calendar_id}
              </p>
            )}
            <p>
              <span className="font-medium text-ink">{t("calendar.google.vehiclesLabel")}: </span>
              {status.synced_vehicle_ids.length}
            </p>
          </div>
          {status.last_error && <p className="text-sm text-danger">{status.last_error}</p>}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => void changeSelection()}
              className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink"
            >
              {t("calendar.google.changeSelection")}
            </button>
            <button
              onClick={() => void disconnect()}
              className="rounded-md border border-copper/30 px-3 py-2 text-sm font-medium text-brand"
            >
              {t("calendar.google.disconnect")}
            </button>
          </div>
        </div>
      )}

      {showPicker && calendarOptions && vehicleOptions && (
        <div className="space-y-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-ink-muted">
              {t("calendar.google.calendarLabel")}
            </span>
            <select
              value={selectedCalendarId}
              onChange={(event) => setSelectedCalendarId(event.target.value)}
              className="w-full rounded-md border border-line bg-raised px-3 py-2"
            >
              {calendarOptions.map((calendar) => (
                <option key={calendar.id} value={calendar.id}>
                  {calendar.summary}
                </option>
              ))}
            </select>
          </label>
          <div>
            <span className="mb-1 block text-sm font-medium text-ink-muted">
              {t("calendar.google.vehiclesLabel")}
            </span>
            <ul className="space-y-1">
              {vehicleOptions.map((vehicle) => (
                <li key={vehicle.id}>
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={selectedVehicleIds.has(vehicle.id)}
                      onChange={() => toggleVehicle(vehicle.id)}
                    />
                    {vehicle.name}
                  </label>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => void saveSelection()}
              disabled={saving || !selectedCalendarId}
              className="rounded-md bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-60"
            >
              {t("calendar.google.save")}
            </button>
            <button
              onClick={() => setShowPicker(false)}
              className="rounded-md border border-line px-3 py-2 text-sm font-medium text-ink"
            >
              {t("common.cancel")}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
