/** The calendar date `value` falls on where the user is, as `YYYY-MM-DD`.
 *
 * `toISOString()` gives the UTC date instead, which is yesterday for anyone
 * east of Greenwich in the hours after their midnight.
 */
export function localIsoDate(value: Date = new Date()): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
