# SportHub frontend

React, TypeScript and Vite with Tailwind, shadcn/ui and Lucide. The independent Django API and PostgreSQL database live in `../backend`. Feature progress is recorded in [the migration checklist](../docs/MIGRATION.md).

## Run locally

Use Node.js 22.12 or later. From this directory:

```powershell
npm ci
npm run dev
```

Start Django separately on `127.0.0.1:8000`, or run `scripts/start.ps1` from the repository root for the existing bundled Windows setup. Vite serves `http://localhost:5173` and proxies `/api/` and `/media/`. Copy `.env.example` to `.env` only to change `API_PROXY_TARGET`; browser requests always use the same origin.

Implemented routes: `/`, `/shop`, `/search`, `/categories/:slug`, `/products/:id`, `/about`, `/contact`, `/register`, `/login`, `/admin/login`, `/account`, `/cart`, `/wishlist`, `/checkout`, `/orders`, `/orders/:id`, `/payments`, `/payments/:id`, `/payment/return`, `/admin`, `/admin/catalog`, `/admin/orders`, `/admin/users`, `/admin/accounts`, `/admin/messages`. Staff can manage categories, products, inventory, fulfillment, accounts and contact messages. Checkout accepts cash on delivery and configured Khalti payments, with payment history and return/recovery screens. Create initial staff with `python manage.py createsuperuser` from `backend`; there are no seeded accounts or default passwords. Actual merchant sandbox verification, outlet maps and production cutover checks remain pending. See [payment setup](../docs/PAYMENTS.md).

## OOP boundaries

`src/lib/api.ts` defines `ApiTransport` and its `ApiClient` implementation. `features/auth/auth-service.ts` defines account types and `AuthService`, which receives its transport through constructor injection. The React provider manages session state; pages handle presentation and form submission. Keep domain/network behavior in focused services and keep React components functional. See [architecture](../docs/ARCHITECTURE.md) for backend service and inheritance conventions.

## Verify

```powershell
npm run build
npm run lint
```

Run backend tests from `backend` so Django discovers the apps:

```powershell
..\.venv\Scripts\python.exe manage.py test --noinput
```

Optional browser tests start Vite on port 5174 and point it at Django's live test server. They cover identity, staff catalog CRUD, public browsing, contact, wishlist/cart, selected COD checkout, order history, staff management, mobile navigation and Khalti contract flows (return/login recovery, pending/outage/recheck, receipt, cancellation/retry and uncertain initiation). Only the external provider is substituted in payment tests; React, Django and PostgreSQL run together. Accounts and catalog fixtures exist only in the disposable PostgreSQL test database, and uploads use temporary storage. Install `backend/requirements-dev.txt`; install Chromium with `python -m playwright install chromium`, or select an installed Edge browser as below. From `backend`:

```powershell
$env:SPORTHUB_BROWSER_TESTS = '1'
$env:SPORTHUB_BROWSER_CHANNEL = 'msedge'
..\.venv\Scripts\python.exe manage.py test accounts.test_browser --noinput
```

Omit `SPORTHUB_BROWSER_CHANNEL` to use Playwright Chromium. The test runner closes its own Vite/browser processes. Screenshots and Vite output are written under the ignored `.runtime/` directory. Never point tests at the legacy database.
