import { PublicClientApplication } from '@azure/msal-browser';

// Allowed redirect URIs — must ALL be registered in Azure AD portal under:
// App registrations → your app → Authentication → Single-page application → Redirect URIs
const REDIRECT_URI = window.location.origin;   // e.g. http://localhost:5173

export const msalConfig = {
  auth: {
    clientId:    import.meta.env.VITE_MICROSOFT_CLIENT_ID,
    authority:   `https://login.microsoftonline.com/${import.meta.env.VITE_MICROSOFT_TENANT_ID || 'common'}`,
    redirectUri: REDIRECT_URI,
    postLogoutRedirectUri: REDIRECT_URI,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation:          'sessionStorage',
    storeAuthStateInCookie: true,   // needed for IE11 / cross-origin iframes
  },
  system: {
    allowNativeBroker: false,        // prevents pop-up issues on some browsers
  },
};

// Scopes: openid + profile + email are sufficient for the GridAI login flow
export const loginRequest = {
  scopes: ['openid', 'profile', 'email', 'User.Read'],
  prompt: 'select_account',
};

export const msalInstance = new PublicClientApplication(msalConfig);

/*
 * ─── Azure AD Setup Checklist ───────────────────────────────────────────────
 *
 * 1. Go to https://portal.azure.com → Azure Active Directory → App registrations
 * 2. Select your app (client ID = VITE_MICROSOFT_CLIENT_ID in .env)
 * 3. Click "Authentication" in the left sidebar
 * 4. Under "Platform configurations" → "Single-page application"
 *    Add ALL of the following redirect URIs:
 *      • http://localhost:5173        ← Vite dev server default
 *      • http://localhost:3000        ← CRA / alternate dev port
 *      • https://your-production-domain.com   ← when deployed
 * 5. Under "Implicit grant and hybrid flows": UNCHECK both boxes
 *    (SPA mode uses PKCE — no implicit flow needed)
 * 6. "Supported account types" → choose:
 *      "Accounts in any organizational directory and personal Microsoft accounts"
 *    (matches VITE_MICROSOFT_TENANT_ID=common in .env)
 * 7. Save → wait ~30s for changes to propagate, then retry login
 */
