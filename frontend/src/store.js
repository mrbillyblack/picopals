// Thin wrapper over localStorage for the bits that must persist on the device:
// the user id (so we keep the same pet across reloads) and UI preferences.

const KEYS = {
  userId: 'picopals.userId',
  recoveryCode: 'picopals.recoveryCode',
  settings: 'picopals.settings',
}

const DEFAULT_SETTINGS = { color: 'teal', dark: false }

export const store = {
  getUserId: () => localStorage.getItem(KEYS.userId),
  setUserId: (id) => localStorage.setItem(KEYS.userId, id),

  getRecoveryCode: () => localStorage.getItem(KEYS.recoveryCode) || '',
  setRecoveryCode: (code) => localStorage.setItem(KEYS.recoveryCode, code),

  getSettings() {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEYS.settings) || '{}') }
    } catch {
      return { ...DEFAULT_SETTINGS }
    }
  },
  setSettings(patch) {
    const next = { ...this.getSettings(), ...patch }
    localStorage.setItem(KEYS.settings, JSON.stringify(next))
    return next
  },

  // Switch which pet this device points at (used by recovery).
  adoptUser(userId, recoveryCode) {
    this.setUserId(userId)
    if (recoveryCode) this.setRecoveryCode(recoveryCode)
  },
}
