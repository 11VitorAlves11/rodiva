/** Typed fetch wrapper. The session lives in an httpOnly cookie, so every call
 * sends credentials and no token is ever readable from JavaScript. */

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized() {
    return this.status === 401;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

export async function errorFrom(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const payload = await response.json();
    if (typeof payload?.message === "string") detail = payload.message;
    else if (typeof payload?.detail === "string") detail = payload.detail;
    if (Array.isArray(payload?.fields) && payload.fields.length) {
      detail += ": " + payload.fields.map((field: { field: string; message: string }) => `${field.field}: ${field.message}`).join("; ");
    }
  } catch {
    // A body that is not JSON tells us nothing more than the status already does.
  }
  return new ApiError(response.status, detail);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(path, {
    method: options.method ?? "GET",
    credentials: "include",
    headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
