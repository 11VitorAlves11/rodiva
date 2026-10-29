import { afterEach, describe, expect, it, vi } from "vitest";
import { localIsoDate } from "./dates";

describe("localIsoDate", () => {
  const zone = process.env.TZ;
  afterEach(() => {
    vi.useRealTimers();
    process.env.TZ = zone;
  });

  it("gives the local date just after midnight in summer time", () => {
    process.env.TZ = "Europe/Lisbon";
    vi.useFakeTimers();
    // 00:30 on 15 July in Lisbon (UTC+1) is still 14 July in UTC.
    vi.setSystemTime(new Date(2026, 6, 15, 0, 30));
    expect(new Date().toISOString().slice(0, 10)).toBe("2026-07-14");
    expect(localIsoDate()).toBe("2026-07-15");
  });

  it("pads single-digit months and days", () => {
    expect(localIsoDate(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
