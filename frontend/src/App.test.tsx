import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "./lib/i18n";
import { App } from "./App";
import { SessionProvider } from "./lib/session";

describe("App", () => {
  beforeEach(() => {
    // Unauthenticated by default: /auth/me answers 401, same as a fresh visit.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Not authenticated" }), { status: 401 })),
    );
  });

  it("redirects to the login screen when signed out", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <SessionProvider>
          <App />
        </SessionProvider>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText(/entrar na rodiva/i)).toBeInTheDocument());
  });
});
