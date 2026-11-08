# SportHub migration checklist

The legacy application was inspected as source only. No connection to its MySQL database is permitted. The new application uses its own PostgreSQL cluster, credentials, database, and Django migrations. Existing records are not imported. Empty operational tables are intentional until users and staff create real records.

## Evidence preservation

All original source, assets, uncommitted changes, and local configuration were archived before implementation to `C:\Users\ACER\sporthub-migration-backups\legacy-20261008-150428.zip`. This private archive is outside the application and must not be published. Git history also retains tracked legacy source.

## Batch gates

Each feature batch includes both API and React UI, then regression checks before the next batch. `[ ]` means not yet verified; implementation alone does not close a gate.

- [x] 0. Source audit: customer/admin/payment/map pages, shared PHP/JS/CSS, SQL, configuration, assets.
- [x] 1. Foundation: React/TypeScript/Vite, Tailwind/shadcn/Lucide; Django/DRF; normalized models and PostgreSQL constraints/migrations; isolated environment; build and database checks.
- [x] 2. Identity and layout: registration, customer/staff login, session/CSRF, profile/password, navigation, guards, logout.
- [x] 3. Catalog and content: home/carousels/offers/featured/latest, shop filters/sorts, categories/search/detail, about/testimonials, contact; staff product/category CRUD, image validation.
- [x] 4. Commerce: cart/wishlist ownership and stock, selected checkout, delivery validation, transactional COD orders, order history; staff orders/dashboard/accounts/messages.
- [ ] 5. Khalti: initiation/ledger/verification/receipt/failure/retry, amounts and ownership, duplicate callback safety; real gateway verification distinguished from automated contract tests.
- [ ] 6. Outlets: public shops/graph APIs, searchable map, location/manual origin, Dijkstra routing, graph overlay, metrics; staff data management.
- [ ] 7. Cutover: legacy route coverage, remove PHP/runtime dependencies, production config/runbook, security/dependency checks, PostgreSQL integration and browser end-to-end tests, final unresolved-limitations report.

## Architecture decisions

- Same-origin `/api/` with Django sessions in HttpOnly cookies and CSRF validation. No auth tokens in browser storage.
- PostgreSQL only, using the new database `sporthub_next`; local development port `55432`. No SQLite fallback or legacy database adapter.
- Server-calculated Decimal NPR prices and immutable order line snapshots. Inventory checked under transactional locks.
- Customer and staff authorization in API permissions, independently of frontend guards.
- shadcn/ui source components, Tailwind tokens, Lucide icons; accessible dialogs and responsive navigation.
- Khalti is an external integration requiring merchant configuration. Provider errors are real errors; no successful-payment simulation in application code.
- Fresh operational data is managed through staff APIs/UI. Existing editorial copy and static assets can be preserved; SQL sample shops must not masquerade as verified business data.
- Maintain OOP boundaries: Django models/managers, serializers, class-based views and domain service objects; TypeScript services composed with transport interfaces. React presentation remains functional. See `ARCHITECTURE.md` for concrete examples and extension rules.

## Reference documentation

- https://docs.djangoproject.com/en/5.2/
- https://www.django-rest-framework.org/
- https://ui.shadcn.com/docs/installation/vite
- https://docs.khalti.com/khalti-epayment/
- https://www.postgresql.org/download/windows/

## Verification log

### 2026-10-08: foundation and identity

- Django system check, migrations and migration-drift check passed on the isolated PostgreSQL setup; static collection passed.
- Frontend production build (TypeScript + Vite) and ESLint passed. Installed missing UI dependencies and replaced the carousel's effect-driven state updates with subscriptions to its external state.
- All 31 tests passed: 29 backend/schema/API cases and two opt-in real-browser flows in headless Microsoft Edge. Browser tests cover customer registration, session persistence after reload, profile update, password change, logout/login, case-insensitive sign-in, staff-only API/UI access, invalid credentials and mobile navigation at 390px. Browser fixtures are confined to the disposable test database.
- Security cases cover anonymous CSRF enforcement, rotated tokens, untrusted origins, role-field rejection, identity uniqueness, contact/password validation, inactive accounts, rate limiting and invalidation of other sessions after password changes.
- Desktop login and mobile account screenshots were inspected; artifacts are under ignored `.runtime/`. Browser commands are documented in `frontend/README.md`.
- Corrected the Windows launcher to wait for `pg_ctl` itself instead of the persistent PostgreSQL child process.

### 2026-11-05: catalog and content

- Connected home, shop, category, search and product detail routes to the catalog API. Home includes hero/offer carousels with navigation dots, featured picks and sortable latest products; shop filters persist in the URL. Empty operational data produces empty states.
- Added About with the original mission/testimonials, and guest/authenticated Contact with validation, CSRF, duplicate detection and throttling.
- Added `/admin/catalog` for category creation/rename/deletion and product creation/edit/deletion, image upload, inventory, discounts and featured picks. API checks enforce staff access, six featured products, protected categories and active reservation limits. JPEG/PNG/WebP content is decoded and re-encoded under generated filenames.
- Fixed omitted boolean query flags incorrectly excluding discounted/featured products from default catalog results. Corrected dropdown accessible labels and a logout redirect race from protected routes.
- All 46 tests passed against the disposable PostgreSQL test database: 42 schema/API cases and four real-browser flows in headless Microsoft Edge. Catalog browser coverage includes staff CRUD/upload, protected deletion, public filters and refresh, category/search/detail, logout, contact and 390px mobile navigation. No legacy database access or operational fixture imports.
- TypeScript/Vite production build, ESLint, Django system checks and migration-drift check passed. Desktop staff and mobile shop screenshots were inspected; artifacts are in ignored `.runtime/catalog-admin-desktop.png` and `.runtime/catalog-shop-mobile.png`.

### 2026-11-05: commerce and requested legacy cleanup

- Added owner-scoped cart/wishlist APIs and UI, quantity controls, duplicate handling, cart/wishlist counts, confirmed removal/clearing and atomic wishlist-to-cart moves. Customer login returns to the requested product or selected checkout URL.
- Added selected COD checkout with delivery validation, URL-persisted item selection, server-priced immutable order snapshots, active reservation checks, transactional inventory decrement and removal of purchased cart rows only. Failed submissions retain delivery inputs. Order history and detail expose only the authenticated owner's orders.
- Added staff dashboard, filtered fulfillment management, customer/staff account management and contact message management. COD completion records payment collection; Khalti settlement cannot be forged through fulfillment changes. Account creation preserves the creator's session; account deletion protects the acting/last active staff user and active reservations.
- All 67 tests passed against the isolated disposable PostgreSQL database: 61 schema/API/concurrency tests and six real-browser flows. Concurrent checkout tests prove the final stock unit cannot be sold twice and duplicate checkout cannot create two orders; injected write failure rolls back stock, cart and order writes. Concurrent staff deletion leaves an active staff account. Browser coverage includes wishlist-to-cart, quantity updates, selected checkout after refresh, mobile order details, unselected cart preservation, order fulfillment, account creation/deletion and message deletion.
- TypeScript/Vite build, ESLint, Django checks and migration-drift checks passed. Mobile checkout/order and desktop dashboard screenshots were inspected under `.runtime/commerce-*.png`. The local development API was restarted and the frontend, health and protected commerce endpoints were checked through port 5173.
- At the user's explicit request, legacy source cleanup was performed ahead of the remaining cutover checks. Removed 72 obsolete files: root PHP pages, legacy `admin/`, `api/`, `components/`, `css/`, `js/`, duplicate `images/`, SQL dump and root legacy `.env`/`.env.example`. The current bytes of every removed file were archived and hash-verified in `C:\Users\ACER\sporthub-migration-backups\legacy-cleanup-20261105-230144.zip` before removal. This private archive contains sensitive legacy configuration and must not be published. No legacy database was opened.
- Preserved React's `frontend/public/images`, the new backend/frontend environment files, `.htaccess`, unique original uploads and project reference screenshots. Added the root README with the current startup instructions and asset/backup locations. Historical PHP paths in the audit documents now refer to archived source.

Next batch: Khalti payment initiation, ledger, verification, receipt/failure/retry, with gateway configuration and verification distinguished from automated contract tests. Outlet maps and remaining production cutover checks are still pending. PHP removal does not close the production-readiness gate.

### 2026-11-06: outlet API foundation

- Added public active-outlet search and graph APIs, and staff CRUD APIs for outlets, intersections and roads. No sample data is inserted.
- Added a database constraint against reverse-duplicate roads. Existing duplicate pairs must be resolved before applying the migration.
- Four outlet schema/API tests passed against the disposable PostgreSQL test database; migration drift check passed. The React map, routing, staff interface and browser verification remain outstanding, so batch 6 remains open.
