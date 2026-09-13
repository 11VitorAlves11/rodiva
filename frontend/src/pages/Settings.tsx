import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { household } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Invite, Member, Role } from "../lib/api/types";
import { useSession } from "../lib/session";

function initials(name: string | null | undefined, email: string) {
  const source = (name ?? email).trim();
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function Settings() {
  const { t, i18n } = useTranslation();
  const { me, signOut } = useSession();
  const canManageMembers = me?.membership.role === "owner" || me?.membership.role === "manager";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-graphite dark:text-cream">{t("settings.title")}</h1>

      <section className="flex items-center gap-4 rounded-xl border border-graphite/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
        <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-copper text-lg font-semibold text-white">
          {me ? initials(me.user.name, me.user.email) : ""}
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold text-graphite dark:text-cream">{me?.user.name ?? me?.user.email}</p>
          <p className="truncate text-sm text-graphite/50 dark:text-cream/50">{me?.user.email}</p>
          <p className="mt-1 text-sm text-graphite/50 dark:text-cream/50">{me?.membership.household_name}</p>
        </div>
      </section>

      <MembersSection canManage={canManageMembers} currentUserId={me?.user.id} />

      <section className="rounded-xl border border-graphite/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
        <h2 className="mb-4 font-semibold text-graphite dark:text-cream">{t("settings.preferences")}</h2>
        <div className="flex items-center justify-between gap-4 py-2">
          <span className="text-sm text-graphite/70 dark:text-cream/70">{t("settings.language")}</span>
          <select
            value={i18n.language}
            onChange={(event) => void i18n.changeLanguage(event.target.value)}
            className="rounded-md border border-graphite/15 bg-white px-3 py-2 text-sm dark:border-white/15 dark:bg-surface-dark"
          >
            <option value="pt-PT">Português</option>
            <option value="en">English</option>
          </select>
        </div>
      </section>

      <button
        onClick={() => void signOut()}
        className="w-full rounded-lg border border-copper/30 px-4 py-3 text-sm font-semibold text-copper hover:bg-copper/5 dark:text-copper-bright"
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
    <section className="rounded-xl border border-graphite/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-surface-dark-raised">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="font-semibold text-graphite dark:text-cream">{t("settings.members")}</h2>
        {canManage && (
          <button
            onClick={() => setShowInviteForm((value) => !value)}
            className="rounded-md bg-copper px-3 py-2 text-sm font-medium text-white hover:bg-copper-dark"
          >
            {t("settings.invite")}
          </button>
        )}
      </div>

      {error && <p className="mb-3 text-sm text-red-700">{error}</p>}

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
          <span className="font-medium text-copper-dark dark:text-copper-bright">{t("settings.inviteReady")}</span>
          <code className="min-w-0 flex-1 truncate rounded bg-white px-2 py-1 text-graphite dark:bg-surface-dark dark:text-cream">
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
        <p className="text-sm text-graphite/50 dark:text-cream/50">{t("common.loading")}</p>
      ) : (
        <ul className="divide-y divide-graphite/5 dark:divide-white/5">
          {members.map((member) => (
            <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-graphite dark:text-cream">{member.name ?? member.email}</p>
                <p className="truncate text-sm text-graphite/50 dark:text-cream/50">{member.email}</p>
              </div>
              <div className="flex items-center gap-2">
                {canManage ? (
                  <select
                    value={member.role}
                    onChange={(event) => void changeRole(member.user_id, event.target.value as Role)}
                    className="rounded-md border border-graphite/15 bg-white px-2 py-1.5 text-sm dark:border-white/15 dark:bg-surface-dark"
                  >
                    {roles.map((role) => (
                      <option key={role} value={role}>{t(`settings.roles.${role}`)}</option>
                    ))}
                  </select>
                ) : (
                  <span className="rounded-full bg-graphite/5 px-3 py-1 text-xs font-medium text-graphite/70 dark:bg-white/10 dark:text-cream/70">
                    {t(`settings.roles.${member.role}`)}
                  </span>
                )}
                {canManage && member.user_id !== currentUserId && (
                  <button onClick={() => void remove(member.user_id)} className="text-sm font-medium text-red-700">
                    {t("settings.remove")}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {canManage && pendingInvites.length > 0 && (
        <div className="mt-5 border-t border-graphite/10 pt-4 dark:border-white/10">
          <h3 className="mb-2 text-sm font-semibold text-graphite/70 dark:text-cream/70">{t("settings.pendingInvites")}</h3>
          <ul className="space-y-2">
            {pendingInvites.map((invite) => (
              <li key={invite.id} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-graphite dark:text-cream">
                  {invite.email ?? t(`settings.roles.${invite.role}`)}
                </span>
                <button onClick={() => void revoke(invite.id)} className="font-medium text-red-700">
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
        <span className="mb-1 block font-medium text-graphite/70 dark:text-cream/70">{t("settings.role")}</span>
        <select
          value={role}
          onChange={(event) => setRole(event.target.value as Role)}
          className="w-full rounded-md border border-graphite/15 bg-white px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
        >
          {roles.filter((item) => item !== "owner").map((item) => (
            <option key={item} value={item}>{t(`settings.roles.${item}`)}</option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-graphite/70 dark:text-cream/70">{t("settings.inviteEmail")}</span>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-md border border-graphite/15 px-3 py-2 dark:border-white/15 dark:bg-surface-dark"
        />
      </label>
      {error && <p className="text-sm text-red-700 sm:col-span-2">{error}</p>}
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
