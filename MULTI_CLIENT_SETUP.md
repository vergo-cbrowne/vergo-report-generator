# Vergo Multi-Client Access System

## System Overview

This system enables the Streamlit admin panel to create and manage client accounts, which then power the Next.js client portal login and upload routing.

### Architecture

1. **Admin Panel** (Streamlit) - Create/manage clients
   - Hashes passwords using PBKDF2-SHA256
   - Saves client accounts to `data/client_accounts.json`
   - Prevents duplicate emails and slugs
   - Toggle client active status

2. **Client Portal** (Next.js) - Client-facing interface
   - Login with email + password (verified against hashed passwords)
   - Session stored in HTTP-only cookies
   - Upload routed to the client's configured Google Drive folder
   - All uploads tracked with client metadata

3. **Account Registry** - `data/client_accounts.json`
   - Persistent JSON file storing all client accounts
   - Client name, slug, email, password hash, intake folder ID, active status, creation date

## Files Changed

### Backend (Python Admin Panel)
- **src/admin_portal.py** - Updated to:
  - Use new `load_client_accounts()` / `save_client_accounts()` functions
  - Hash temporary passwords with PBKDF2-SHA256
  - Prevent duplicate emails and slugs
  - Migrate legacy `client_users.json` on first run
  - Display account list with formatted columns

### Frontend (Next.js Client Portal)
- **vergo-client-portal/app/page.tsx** - Updated to:
  - Add login section when not authenticated
  - Restore session from cookies on load
  - Dynamic profile display (client name + email)
  - Conditional upload form (only shown when logged in)
  - Updated header text based on auth state

### API Routes (Next.js)
- **vergo-client-portal/app/api/auth/login/route.ts** - New
  - POST `/api/auth/login` with `{ email, password }`
  - Verifies against account registry
  - Returns client metadata
  - Sets `vergo_client_email` cookie (7-day expiry)

- **vergo-client-portal/app/api/auth/session/route.ts** - New
  - GET `/api/auth/session`
  - Reads `vergo_client_email` cookie
  - Returns current client or null if not logged in

- **vergo-client-portal/app/api/auth/logout/route.ts** - New
  - POST `/api/auth/logout`
  - Clears the `vergo_client_email` cookie

- **vergo-client-portal/app/api/upload/route.ts** - Updated to:
  - Read client email from cookie or form data
  - Look up client account from registry
  - Verify account is active
  - Use the client's `intakeFolderId` for all uploads
  - Include rich metadata in uploaded `metadata.json`:
    - `clientName`, `clientSlug`, `clientEmail`
    - `taskName`, `uploadedAt`, `originalFilename`
    - Video details and drive folder reference

### Shared Library (Next.js)
- **vergo-client-portal/lib/auth.ts** - New
  - `loadClientAccounts()` - Read from registry file
  - `saveClientAccounts()` - Persist to registry file
  - `hashPassword()` - PBKDF2-SHA256 hashing
  - `verifyPassword()` - Verify passwords against hashes
  - `findClientByEmail()` - Lookup helper
  - `findClientBySlug()` - Lookup helper
  - Auto-migration from legacy format on first load

### Data File
- **data/client_accounts.json** - New registry file
  - Auto-created on first admin panel run
  - Auto-migrates from legacy `client_users.json` if present
  - JSON array of account objects:
    ```json
    {
      "clientName": "Eastcut",
      "slug": "eastcut",
      "email": "contact@eastcut.com",
      "passwordHash": "pbkdf2_sha256$250000$...",
      "intakeFolderId": "1W3aRbZ-52Xiz1Mo3h1Dg99HUlh0uRuSc",
      "active": true,
      "createdAt": "2026-06-01T12:34:56Z"
    }
    ```

## Running the System

### Start the Admin Panel

```bash
cd /workspaces/vergo-report-generator
streamlit run src/admin_portal.py
```

Navigate to the **Client Access** tab and create a test client.

### Start the Client Portal (Local Dev)

```bash
cd /workspaces/vergo-report-generator/vergo-client-portal
npm run dev -- -H 0.0.0.0 -p 3000
```

Visit `http://localhost:3000` in your browser.

## Testing Multi-Client Access

### Step 1: Create Two Test Clients in Admin Panel

In the **Client Access** tab, create:

**Client 1:**
- Client Name: `Eastcut`
- Client Slug: `eastcut`
- Client Login Email: `alice@eastcut.com`
- Temporary Password: `TestPass123!`
- Google Drive Intake Folder ID: (Folder A ID)
- Active: ✓

**Client 2:**
- Client Name: `SafeWorks`
- Client Slug: `safeworks`
- Client Login Email: `bob@safeworks.com`
- Temporary Password: `SecurePass456!`
- Google Drive Intake Folder ID: (Folder B ID)
- Active: ✓

After creating each, you should see them listed in the "Existing Client Accounts" section.

### Step 2: Test Client 1 Login

1. Open the client portal at `http://localhost:3000`
2. You should see the login form
3. Enter:
   - Email: `alice@eastcut.com`
   - Password: `TestPass123!`
4. Click **Sign in**
5. Verify that you see:
   - Profile sidebar updated to show "Eastcut" and "alice@eastcut.com"
   - Upload form becomes visible
   - Header changes to "Upload Task Video"

### Step 3: Upload a Test Video as Client 1

1. Fill in the upload form fields
2. Select or drag a test video file (MP4/MOV, under 100 MB)
3. Click **Upload**
4. Verify:
   - Circular spinner appears
   - "Uploading video to Vergo..." message shows
   - On success: "Upload complete" displays
   - Check Google Drive Folder A - should see a new `YYYY-MM-DD__TaskName/` folder with the video and `metadata.json`
   - In `metadata.json`, verify:
     ```json
     {
       "clientName": "Eastcut",
       "clientSlug": "eastcut",
       "clientEmail": "alice@eastcut.com",
       "taskName": "...",
       "uploadedAt": "2026-06-01T...",
       "originalFilename": "test.mp4"
     }
     ```

### Step 4: Test Client 1 Logout

1. Click the profile button in the sidebar (Eastcut / alice@eastcut.com)
2. Click **Log Out**
3. Verify login form reappears

### Step 5: Test Client 2 Login and Upload

1. Repeat Step 2 with Client 2 credentials:
   - Email: `bob@safeworks.com`
   - Password: `SecurePass456!`
2. Verify profile shows "SafeWorks" and "bob@safeworks.com"
3. Upload a test video
4. Verify upload goes to Google Drive Folder B (not Folder A)
5. Check `metadata.json` shows Client 2's details

### Step 6: Test Inactive Client Rejection

In the admin panel:
1. Find the "SafeWorks" account in the list
2. (Currently, you'd need to manually edit `data/client_accounts.json` to set `"active": false`)
3. Try logging in as SafeWorks again
4. Verify error message: "Invalid email or password, or the account is inactive."

### Step 7: Test Duplicate Prevention

In the admin panel, try creating:
1. A client with the same email as "Eastcut" → Should show "Client email already exists."
2. A client with the same slug as "SafeWorks" → Should show "Client slug already exists."

## Development Commands

### Build the Client Portal
```bash
cd vergo-client-portal
npm run build
```

### Run TypeScript Check
```bash
cd vergo-client-portal
npx tsc --noEmit
```

### Check Python Syntax (Admin Panel)
```bash
python -m py_compile src/admin_portal.py
```

### View Current Accounts Registry
```bash
cat data/client_accounts.json
```

## Migration from Legacy System

If the system detects the old `data/client_users.json` file on first run:
1. It automatically reads all old client records
2. Hashes the stored plain-text passwords using the new PBKDF2-SHA256 algorithm
3. Creates the new `data/client_accounts.json` with updated fields
4. The old file is left in place (can be deleted manually)

## Security Notes

- Passwords are hashed using PBKDF2-SHA256 with 250,000 iterations
- Session cookies are HTTP-only (not accessible from JavaScript)
- Session cookies are secure (only sent over HTTPS in production)
- Session cookies have a 7-day expiry
- Inactive clients cannot log in even with correct password
- Client email and slug must be unique
- Temporary passwords are never displayed after creation

## Troubleshooting

### Login fails with "Invalid email or password"
- Double-check email spelling and case (emails are stored lowercase)
- Verify the account exists in admin panel
- Verify the account is marked as "Active"

### Upload fails with "Client session is invalid"
- Session cookie may have expired (7 days)
- Log out and log in again

### Upload fails with "not configured with a Google Drive intake folder"
- The client account's `intakeFolderId` field is empty
- Update the account in admin panel with a valid folder ID

### Client's upload doesn't appear in their folder
- Check that the client's `intakeFolderId` is correct
- Verify the service account has permission to write to that folder
- Check the portal server logs for any Google Drive API errors
