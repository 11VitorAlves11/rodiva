import type { ComponentType, SVGProps } from "react";
import {
  ArchiveBoxIcon,
  BellIcon,
  BoltIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  ClipboardDocumentCheckIcon,
  ClockIcon,
  Cog6ToothIcon,
  CurrencyEuroIcon,
  DocumentTextIcon,
  EllipsisHorizontalIcon,
  HomeModernIcon,
  MagnifyingGlassIcon,
  MapIcon,
  PaperClipIcon,
  PlusIcon,
  TruckIcon,
  ViewColumnsIcon,
  WrenchIcon,
  WrenchScrewdriverIcon,
} from "@heroicons/react/24/outline";

export type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

/**
 * Single source of truth for "what icon represents this section/record kind"
 * across the app: sidebar/mobile nav (AppShell), the More page, the dashboard
 * activity feed, and search result badges all key into this map instead of
 * keeping their own copy of the same association.
 */
export const NAV_ICONS: Record<string, IconComponent> = {
  garage: HomeModernIcon,
  vehicle: TruckIcon,
  history: ClockIcon,
  reminders: BellIcon,
  calendar: CalendarDaysIcon,
  settings: Cog6ToothIcon,
  planner: ViewColumnsIcon,
  plan: ViewColumnsIcon,
  inventory: ArchiveBoxIcon,
  equipment: WrenchIcon,
  inspections: ClipboardDocumentCheckIcon,
  inspection: ClipboardDocumentCheckIcon,
  reports: ChartBarIcon,
  search: MagnifyingGlassIcon,
  more: EllipsisHorizontalIcon,
  plus: PlusIcon,
  fuel: BoltIcon,
  charging: BoltIcon,
  odometer: MapIcon,
  work: WrenchScrewdriverIcon,
  expenses: CurrencyEuroIcon,
  expense: CurrencyEuroIcon,
  notes: DocumentTextIcon,
  note: DocumentTextIcon,
  documents: PaperClipIcon,
  document: PaperClipIcon,
};
