export type HealthResponse = {
  status: string;
  service: string;
};

type ApiRequestOptions = {
  token?: string | null;
};

export async function apiGet<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const response = await fetch(path, {
    headers: buildHeaders(options)
  });

  if (!response.ok) {
    throw new Error(`ForgeML API request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<TRequest, TResponse>(
  path: string,
  body: TRequest,
  options: ApiRequestOptions = {}
): Promise<TResponse> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      ...buildHeaders(options),
      "content-type": "application/json"
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(`ForgeML API request failed with ${response.status}`);
  }

  return response.json() as Promise<TResponse>;
}

function buildHeaders(options: ApiRequestOptions): HeadersInit {
  const headers: Record<string, string> = {
    accept: "application/json"
  };
  if (options.token) {
    headers.authorization = `Bearer ${options.token}`;
  }
  return headers;
}
