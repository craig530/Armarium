import client from './client'

export const authApi = {
  forgotPassword: (usernameOrEmail) =>
    client.post('/auth/forgot-password', { username_or_email: usernameOrEmail }).then((r) => r.data),
  validateResetToken: (token) => client.get(`/auth/reset-password/${token}`).then((r) => r.data),
  resetPassword: (token, newPassword) =>
    client.post('/auth/reset-password', { token, new_password: newPassword }).then((r) => r.data),
}
