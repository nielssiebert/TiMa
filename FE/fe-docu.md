## Main setting
### Basic user journey
- there should be a main menu on the left site of the onepage app.
    - listing the entities that are maintainable
        - ExecutionEvent
        - ExecutionEventGroup
        - Sequence
        - Trigger
        - Factor
        - User
    - menu should always be open, if there are more than 820px in with and not on a smartphone
    - if opened on a small screen the menu can be opened and close via a burger menu icon at the top left of screen
- the title of the app is TiMa
- if one entity of the menu options is clicked, an overview is presented with a list of all available items. At the top of the list, there is a plus icon to add a new instance of the entity.
- if one of the existing items in the overview is clicked you enter a maintenance page for the respective entity.
- maintenance pages have a cancel and a save button.
- ExecutionEvent overview provides a PrimeVue ToggleButton per row labeled `ON`/`OFF` to manually start/stop the ExecutionEvent via API.
- ExecutionEventGroup overview provides a PrimeVue ToggleButton per row labeled `ON`/`OFF` to manually start/stop the ExecutionEventGroup via API.
- Sequence overview provides a PrimeVue ToggleButton per row labeled `ON`/`OFF` to manually start/stop the Sequence via API.

### Frameworks
- Vue 3
- Fontawsome for icons
- PrimeVue

### Other key settings
- central config
    - local dev profile via env vars
    - production profile via env vars (for deploying to nginx)
    - app config env vars:
        - `VITE_APP_TITLE` (default `TiMa`)
        - `VITE_APP_PROFILE` (`local` or `production`, default `local`)
        - `VITE_API_BASE_URL` (default `/api`)
        - `VITE_OVERVIEW_REFRESH_DEFAULT_MS` (default `5000`)
        - `VITE_OVERVIEW_REFRESH_EXECUTION_EVENTS_MS` (default `1000`)
        - `VITE_OVERVIEW_REFRESH_SEQUENCES_MS` (default `2000`)
    - overview auto-refresh intervals:
        - default: `5000 ms`
        - `ExecutionEvent` overview: `1000 ms`
        - `Sequence` overview: `2000 ms`
- supported devices:
    - should work on a smartphone browser
    - should work on a small tablet
    - should work on a normal pc/laptop monitor
- all static texts that the user will see should be mapped via global translation file
- toast notifications are responsive on small screens (`<= 640px`) and use viewport-based width with side margins so messages stay fully visible on smartphones

### Deployment notes
- The root `install.sh` now enforces Docker daemon auto-start on boot (`systemctl enable --now docker`) so compose services configured with restart policies come back automatically after reboot.
- Before starting containers, `install.sh` lists frontend (`VITE_*`) and backend runtime environment variables and optionally lets the user override each value interactively.

## Auth
- If the browser has no logged-in session, the app opens a login component first.
- Login component:
    - fields: username and password
    - action: log in
    - action: register (switches to registration mode)
- Registration mode keeps username/password fields and shows:
    - action: create account
    - action: return to login
- After successful login:
    - if user is confirmed, user is redirected to ExecutionEvent overview
    - if user is not confirmed, user is redirected to a pending-confirmation component
- Pending-confirmation component informs the user that another confirmed user must confirm the registration first.
- Session handling:
    - Basic Auth session is stored in browser local storage
    - Any API response with status 401 (except login request) automatically clears the stored session and redirects to login
    - protected routes require authenticated session
    - app routes require confirmed user

## Entity maintenances
### Global field help
- Every maintenance form field label includes an info icon at the end of the label.
- The info icon shows the field-specific explanation via tooltip/title text.
- Explanations describe impact and purpose of the field and are maintained in global i18n messages.
- Relation picker typeahead suggestions close automatically when the search input loses focus.

### API service pattern
- Maintenance views should call dedicated feature services instead of directly calling `httpClient`.
- Implemented services:
    - `ExecutionEventService` for ExecutionEvent maintenance.
    - `ExecutionEventGroupService` for ExecutionEventGroup maintenance.
    - `SequenceService` for Sequence maintenance.
    - `FactorService` for Factor maintenance.
    - `TriggerService` for Trigger maintenance.
- Services encapsulate endpoint paths and request methods (`getById`, `create`, `update`, `remove`, and action endpoints).

### ExecutionEvent
- Implemented maintenance form fields:
    - id (editable only on create)
    - status (manual ON/OFF start-stop toggle)
    - name
    - duration (ms)
    - factors (multi relation picker)
    - activated
    - Custom Event Attributes
        - Start event: dynamic key/value rows
        - Stop event: dynamic key/value rows
- Actions:
    - Save (create/update)
    - Delete
    - Cancel

### ExecutionEventGroup
- Implemented maintenance form fields:
    - id (editable only on create)
    - status (manual ON/OFF start-stop toggle)
    - name
    - execution events (multi relation picker)
- Validation:
    - id and name are required
- Actions:
    - Save (create/update)
    - Delete
    - Cancel
    - Runtime toggle uses dedicated backend endpoints (`/start` and `/stop`)
- Backend behavior:
    - group status is derived from related ExecutionEvents (`ON` only when all related ExecutionEvents are `ON`, otherwise `OFF`)
    - `ON` action starts all related ExecutionEvents
    - `OFF` action stops all related ExecutionEvents

### Sequence
- Implemented maintenance form fields:
    - id (editable only on create)
    - status (manual ON/OFF start-stop toggle)
    - name
    - triggers (multi relation picker)
    - execution events (multi relation picker)
    - execution event groups (multi relation picker)
- Validation:
    - id and name are required
- Notes:
    - sequence items are generated from selected execution events first, then selected execution event groups
    - SequenceItem ordering is bucket-based (`order` starts at 1 and is normalized to contiguous values on every reorder)
    - dropping on an item card applies `match order` (the dragged item joins the same `order` bucket as the target)
    - dropping on a gap applies `insert position` (creates a standalone bucket at that position and shifts following buckets)
    - newly selected items are appended to the end in creation order while existing item order is preserved
    - runtime toggle uses dedicated backend endpoints (`/start` and `/stop`)
- Actions:
    - Save (create/update)
    - Delete
    - Cancel

### Factor
- Implemented maintenance form fields:
    - id (editable only on create)
    - name
    - factor value (read-only by default)
    - min value (optional)
    - max value (optional)
    - activated
- Validation:
    - id and name are required
    - min/max must be valid numbers when provided
    - `min <= max` when both are provided
- Actions:
    - Save (create/update)
    - Delete
    - Cancel
    - Activated toggle uses dedicated backend endpoints (`/activate` and `/deactivate`)
    - Factor value supports inline edit flow:
        - click edit icon (pen) to enable editing
        - click accept icon (green check) to save immediately via `/factors/updateFactor`

### Trigger
- Implemented maintenance form fields:
    - id (editable only on create)
    - name
    - trigger type (`START_AT_POINT_IN_TIME` / `STOP_AT_POINT_IN_TIME`)
    - recurrence type (`TIMER` / `ONE_TIME` / `WEEKLY`)
    - time
    - date (for `ONE_TIME`)
    - weekdays (for `WEEKLY`, comma-separated weekday codes)
    - from date (optional)
    - to date (optional)
    - recurring
    - activated
    - sequences (multi relation picker)
- Validation:
    - id and name are required
    - time is required
    - `ONE_TIME` requires date
    - `WEEKLY` requires weekdays
- Notes:
    - recurrence type is locked after creation in maintenance UI because backend does not allow changing it on update
    - activated toggle uses dedicated backend endpoints (`/activate` and `/deactivate`)
    - `from date` and `to date` are disabled for `ONE_TIME`
    - time field supports hours, minutes, and seconds
- Actions:
    - Save (create/update)
    - Delete
    - Cancel

### User
- MainSidebar contains a `User` menu item.
- The `User` page shows two action buttons at the top:
    - `Log out` (clears local session and redirects to login)
    - `Change password` (submits old/new password via backend API)
- The `User` page embeds the Users overview below the action buttons.
- The embedded users overview section is labeled `Users awaiting confirmation:`.
- Users overview lists all other users and shows their confirmation state.
- Users with `confirmed=false` have a `Confirm` action.
- Confirm action calls backend endpoint `POST /api/users/{id}/confirm`.
- Change password action calls backend endpoint `POST /api/users/change_password` with payload fields `old_password` and `new_password`.

## Change notes
- Backend app naming is standardized to `TiMa`/`tima`.
- Frontend integrations should use backend defaults and topic/config values based on the `tima` prefix.
- Installer deployment now supports Docker Compose fallback: it uses `docker compose` when available and automatically falls back to `docker-compose`.

## Deployment additions
- `index.html` title now uses Vite env replacement via `%VITE_APP_TITLE%`.
- Frontend public base path supports deployment behind a reverse-proxy prefix:
    - env var: `VITE_PUBLIC_BASE_PATH` (default `/`)
    - examples:
        - `/` for root deployment
        - `/tima/` for prefixed deployment
- API base URL remains configurable via `VITE_API_BASE_URL` and should match reverse-proxy API path (for example `/tima/api`).
- Translation terminology can be adapted at deployment build time via `install.sh` using an optional JSON replacement file.
- The deployment replacement flow rewrites string literals in `FE/src/core/i18n/messages.ts` before frontend artifact generation (runtime app logic remains unchanged).
- Replacement JSON supports:
    - `string_replacements`: global substring replacements in translation strings
    - `key_replacements`: exact dotted-key overrides (for example `en.entities.sequences.fields.executionEvents`)


