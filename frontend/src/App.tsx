import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { ConfirmProvider } from "./components/ui/ConfirmDialog";
import { ErrorState } from "./components/ui/ErrorState";
import { Equipment } from "./pages/Equipment";
import { Skeleton } from "./components/ui/Skeleton";
import { useSession } from "./lib/session";
import { Garage } from "./pages/Garage";
import { History } from "./pages/History";
import { Dashboard } from "./pages/Dashboard";
import { Activity } from "./pages/Activity";
import { Calendar } from "./pages/Calendar";
import { InviteAccept } from "./pages/InviteAccept";
import { Inventory } from "./pages/Inventory";
import { Inspections } from "./pages/Inspections";
import { PasswordRecovery } from "./pages/PasswordRecovery";
import { ImportRecords } from "./pages/ImportRecords";
import { Login } from "./pages/Login";
import { More } from "./pages/More";
import { Notifications } from "./pages/Notifications";
import { Planner } from "./pages/Planner";
import { Reminders } from "./pages/Reminders";
import { Reports } from "./pages/Reports";
import { Search } from "./pages/Search";
import { Trash } from "./pages/Trash";
import { Settings } from "./pages/Settings";
import { Vehicle } from "./pages/Vehicle";

function RequireSession({ children }: { children: ReactNode }) {
  const { me, loading, error, refresh } = useSession();
  const location = useLocation();

  if (loading) return <Skeleton className="p-8" lines={6} />;
  // A session we could not check is not a session that does not exist: bouncing
  // to the login screen on a network blip reads as being signed out.
  if (error && !me) {
    return (
      <div className="p-8">
        <ErrorState onRetry={() => void refresh()} />
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <AppShell>{children}</AppShell>;
}

export function App() {
  return (
    <ConfirmProvider>
      <Routes>
      <Route path="/forgot-password" element={<PasswordRecovery />} />
      <Route path="/reset-password" element={<PasswordRecovery reset />} />
      <Route path="/login" element={<Login />} />
      <Route path="/invite/:token" element={<InviteAccept />} />
      <Route
        path="/"
        element={
          <RequireSession>
            <Dashboard />
          </RequireSession>
        }
      />
      <Route path="/garage" element={<RequireSession><Garage /></RequireSession>} />
      <Route path="/history" element={<RequireSession><History /></RequireSession>} />
      <Route path="/reminders" element={<RequireSession><Reminders /></RequireSession>} />
      <Route path="/reports" element={<RequireSession><Reports /></RequireSession>} />
      <Route path="/search" element={<RequireSession><Search /></RequireSession>} />
      <Route path="/calendar" element={<RequireSession><Calendar /></RequireSession>} />
      <Route path="/inventory" element={<RequireSession><Inventory /></RequireSession>} />
      <Route path="/equipment" element={<RequireSession><Equipment /></RequireSession>} />
      <Route path="/inspections" element={<RequireSession><Inspections /></RequireSession>} />
      <Route path="/planner" element={<RequireSession><Planner /></RequireSession>} />
      <Route path="/import" element={<RequireSession><ImportRecords /></RequireSession>} />
      <Route path="/notifications" element={<RequireSession><Notifications /></RequireSession>} />
      <Route path="/activity" element={<RequireSession><Activity /></RequireSession>} />
      <Route path="/trash" element={<RequireSession><Trash /></RequireSession>} />
      <Route path="/more" element={<RequireSession><More /></RequireSession>} />
      <Route path="/settings" element={<RequireSession><Settings /></RequireSession>} />
      <Route
        path="/vehicles/:vehicleId"
        element={<RequireSession><Vehicle /></RequireSession>}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ConfirmProvider>
  );
}
