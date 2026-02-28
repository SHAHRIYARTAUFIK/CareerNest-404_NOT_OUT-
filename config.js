/**
 * CareerNest — Frontend Configuration
 * ────────────────────────────────────
 * Copy the values from your .env file into this file.
 * This file is loaded by index.html and admin.html.
 *
 * ⚠️  NEVER commit this file to a public repository if it contains real credentials.
 *     Add config.js to your .gitignore.
 */
const CONFIG = {
    /**
    
     * Your Google OAuth 2.0 Client ID.
     * Get it from: https://console.cloud.google.com/
     *   → APIs & Services → Credentials → Create OAuth client ID (Web application)
     *   → Add http://localhost to Authorized JavaScript origins
     *   → Copy the Client ID and paste below.
     */
    API_BASE: "https://career-nest-404-not-out.vercel.app"
    GOOGLE_CLIENT_ID: "175096449908-avt2v9l07tag5sp36d6ugp8kquogpqvm.apps.googleusercontent.com",

    /**
     * Gmail addresses allowed to access the Admin panel.
     * Add or remove emails from this array to manage admin access.
     */
    ADMIN_EMAILS: ["kparitosh760@gmail.com", "shahriyartaufik@gmail.com"],


    /**
     * Backend API base URL.
     * Change this when deploying to production.
     */
    API_BASE: "http://localhost:8000",
};
