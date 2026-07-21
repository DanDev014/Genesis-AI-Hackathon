export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  const response = await apiRequest<{
    message: string;
    user: {
      user_id: number;
      email: string;
      user_type: string;
    };
  }>('/login', {
    method: 'POST',
    body,
  });

  setCookie(event, 'session_user', JSON.stringify(response.user), {
    httpOnly: false, // readable by useCookie() client-side, no /me endpoint needed
    sameSite: 'lax',
    maxAge: 60 * 60 * 8, // 8 hours
    path: '/',
  });

  return response;
});