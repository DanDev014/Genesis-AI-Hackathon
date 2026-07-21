export async function apiRequest<T = any>(
  path: string,
  options: Parameters<typeof $fetch>[1] = {},
): Promise<T> {
  const config = useRuntimeConfig();

  try {
    return await $fetch<T>(`${config.apiBaseUrl}${path}`, options);
  } catch (err: any) {
    const status = err?.response?.status || 500;
    const body = err?.response?._data;

    const message =
      (typeof body === "string" && body) ||
      body?.message ||
      body?.error ||
      body?.description ||
      err?.message ||
      "Upstream API request failed";

    throw createError({
      statusCode: status,
      statusMessage: message,
      data: body,
    });
  }
}
