import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import i18n from "../../lib/i18n";
import { auth } from "../../lib/api";
import { SessionProvider, useSession } from "../../lib/session";
import { ConfirmProvider } from "../ui/ConfirmDialog";
import { AccountSettings } from "./AccountSettings";

const profile = {
  user: { id: "user", email: "ana@example.com", name: "Ana", locale: "pt-PT", timezone: "Europe/Lisbon" },
  membership: { household_id: "home", household_name: "Casa", role: "owner" as const },
};

afterEach(async () => { cleanup(); await i18n.changeLanguage("pt-PT"); });

it.each([
  ["en", "Preferences", "Preferences saved."],
  ["fr", "Préférences", "Préférences enregistrées."],
  ["es", "Preferencias", "Preferencias guardadas."],
])("saves %s from the language selector and restores it on a new session", async (locale, heading, saved) => {
  vi.spyOn(auth, "me").mockResolvedValue(profile);
  vi.spyOn(auth, "sessions").mockResolvedValue([]);
  vi.spyOn(auth, "households").mockResolvedValue([]);
  const update = vi.spyOn(auth, "profile").mockResolvedValue({ ...profile.user, locale });
  function LoadedSettings() {
    const { loading } = useSession();
    return loading ? null : <AccountSettings />;
  }
  function Settings() {
    return <SessionProvider><ConfirmProvider><LoadedSettings /></ConfirmProvider></SessionProvider>;
  }
  const view = render(<Settings />);
  await screen.findByDisplayValue("Ana");
  await userEvent.selectOptions(screen.getByLabelText("Idioma"), locale);
  await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
  await waitFor(() => expect(update).toHaveBeenCalledWith(expect.objectContaining({ locale })));
  expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  expect(await screen.findByText(saved)).toBeInTheDocument();
  view.unmount();

  await i18n.changeLanguage("pt-PT");
  vi.mocked(auth.me).mockResolvedValue({ ...profile, user: { ...profile.user, locale } });
  render(<Settings />);
  expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  expect(document.documentElement.lang).toBe(locale);
});
