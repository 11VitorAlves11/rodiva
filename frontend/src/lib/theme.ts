import { useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";
const key = "rodiva-theme";
const eventName = "rodiva-theme-change";

function readTheme(): Theme {
  const stored = localStorage.getItem(key);
  return stored === "light" || stored === "dark" ? stored : "system";
}

export function useTheme() {
  const [theme, setPreference] = useState<Theme>(readTheme);
  const [systemDark, setSystemDark] = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);
  const resolved = theme === "system" ? (systemDark ? "dark" : "light") : theme;

  useEffect(() => {
    const sync = () => setPreference(readTheme());
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const update = () => setSystemDark(media?.matches ?? false);
    media?.addEventListener("change", update);
    window.addEventListener("storage", sync);
    window.addEventListener(eventName, sync);
    return () => {
      media?.removeEventListener("change", update);
      window.removeEventListener("storage", sync);
      window.removeEventListener(eventName, sync);
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
  }, [resolved]);

  function setTheme(next: Theme) {
    localStorage.setItem(key, next);
    setPreference(next);
    window.dispatchEvent(new Event(eventName));
  }
  return { theme, resolved, setTheme };
}
