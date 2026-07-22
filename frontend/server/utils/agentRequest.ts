export async function agentRequest<T>(
  endpoint: string,
  options: Parameters<typeof $fetch<T>>[1] = {},
) {
  const config = useRuntimeConfig();

  console.log(`${config.agentBaseUrl}`, "BaseUrl");

  return await $fetch<T>(endpoint, {
    baseURL: config.agentBaseUrl,
    ...options,
  });
}
