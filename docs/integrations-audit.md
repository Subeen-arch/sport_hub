# Payment and shop-map migration audit

Audit date: 2026-10-08 (Asia/Katmandu).

Status: legacy source audit complete; integration implementation and runtime verification remain subject to the migration batch gates in `MIGRATION.md`. This document does not assert that any replacement feature is implemented. The audit read source files only. It did not connect to, read, initialize, or modify the legacy database and did not load the root `.env`.

## Reviewed source

- `khalti_payment.php`, `khalti_verify.php`, `khalti_failed.php`.
- `components/khalti_config.php`, `components/khalti_success_view.php`.
- Payment portions of `checkout.php`, `components/connect.php`, and `shop_db.sql`; `.htaccess` access rules.
- `shop_map.php`, `components/map_schema.php`, `api/get_shops.php`, `api/get_graph.php`.
- `js/dijkstra.js`, `js/shop_map.js`, `css/shop_map.css`.
- References to payment/map features in the shared header, customer orders, and administration orders pages.

Runtime logs were not needed to understand the contracts. Existing credentials must not be transferred automatically to the new configuration.

## Route and feature inventory

The replacement routes below are intended migration destinations, not evidence of completed implementation. The final route inventory must record the actual API paths and application routes before the feature batch closes.

| Legacy entry point | Access and responsibility | Replacement requirement | Dependency |
| --- | --- | --- | --- |
| `checkout.php` with Khalti method | Authenticated; selected cart lines and customer/address form | React checkout posts validated owned line IDs/customer details to a Django service | Accounts, catalog, cart, order models |
| `khalti_payment.php` | Authenticated; snapshot and initiate external checkout | Protected CSRF-safe POST API; React follows validated provider checkout URL | Checkout and payment ledger |
| `khalti_verify.php?pidx=...` | Provider return; missing login currently allowed; foreign logged-in owner rejected | React payment-return route plus server verification API; safe expired-session recovery | Khalti client, order finalization |
| `components/khalti_success_view.php` | Included only after verified payment/order | React receipt showing owned verified order and provider references | Callback and order detail API |
| `khalti_failed.php?reason=...&pidx=...` | Public feedback; optional verification retry | React failure/pending presentation, actionable recovery and checkout/cart links | Payment status API |
| `shop_map.php` | Public | React shop map with shadcn/ui controls/cards/status/results | Public location APIs |
| `api/get_shops.php?search=...` | GET only, public; active outlet search | Public Django list/search API backed by fresh PostgreSQL models | Shop model |
| `api/get_graph.php` | GET only, public; all routing vertices and edges | Public Django graph API backed by fresh PostgreSQL models | Node/edge models |
| Header Shop Map link | Public navigation | React navigation route entry | Shared layout |
| Customer/admin orders references | Payment method, status, transaction reference | Integrated customer/admin order presentation | Orders batch |

## Existing checkout-to-payment behavior

1. `checkout.php` requires `user_id` in PHP session. JSON `selected_items_data` from cart is stored as `selected_checkout_items`; an existing session selection is reused when no new nonempty selection is supplied.
2. The form collects name, phone (`number`), email, flat, street, city, state, country, pin code, and method. Offered methods are `cash on delivery` and `khalti`. The legacy code changes unknown methods to COD instead of rejecting the input.
3. The Khalti choice stores the customer/address/selection in `pending_order` and redirects to initiation. These session objects are not persisted orders.
4. Initiation requires login and both checkout session objects. Selected IDs are cast to integers, falsey entries removed, and matching cart rows restricted to the authenticated owner.
5. Amount is recalculated on the server as the sum of stored cart price multiplied by quantity. Empty selection, empty matching cart, or an amount below NPR 10 stops initiation. Amount is rounded to integer paisa (`NPR * 100`).
6. A unique purchase-order string is generated. The provider request contains `return_url`, `website_url`, `amount`, `purchase_order_id`, `purchase_order_name`, and `customer_info`.
7. Customer name is included; email is included only when valid; phone is stripped to digits and included only when exactly ten digits. This omission behavior must not substitute for validation of required checkout data in Django.
8. The provider response must contain a `pidx` and `payment_url`. Before redirecting to that URL, the application records a ledger snapshot of customer details and exact line name, price, quantity, product ID, image, plus selected cart IDs.
9. Failure to initiate or persist the ledger leaves the cart and checkout state available for retry.

### Verification and order finalization

- Callback query parameters are not proof of payment. Only the server-to-server provider lookup is trusted.
- Callback rejects missing or unknown `pidx`. A logged-in account different from the ledger owner is rejected. Legacy permits a missing session, so an expired login can still complete checkout.
- A ledger already marked `Completed` with an order link displays the existing receipt immediately.
- Otherwise the server looks up `pidx`. Transient lookup failure retains the payment and provides a recheck action.
- The returned provider status/reference is saved. Only exact status `Completed` permits order creation, and lookup `total_amount` must exactly equal the initiation ledger's integer paisa amount.
- Customer/address and line items are reconstructed from the initiation snapshot, rather than the possibly changed cart. Empty snapshotted items are rejected.
- Within a database transaction, the payment row is locked and checked for an existing order again. This prevents concurrent callbacks from creating duplicate orders.
- The resulting order is marked payment `completed`, method `khalti`; contains purchase-order and provider references, shipping address and item snapshot; decrements product quantities; removes only the selected cart rows belonging to the payer; and links the ledger to the order.
- After commit, pending checkout session state is cleared. A persistence error after provider completion directs the customer to support; it must remain recoverable through idempotent reconciliation.

### Payment presentation

Receipt fields: customer name, method, numeric order number, purchase-order ID, Khalti transaction reference (or N/A), amount formatted to two decimal NPR places. Actions: View Orders and Continue Shopping.

Failure UI uses the reason codes below and offers Try Again (checkout) and Back to Cart. A Check Payment Again action appears only for `lookup_failed` and `payment_pending` with a retained `pidx`.

| Code | Meaning / required behavior |
| --- | --- |
| `cancelled` | User cancelled checkout |
| `invalid_response` | Missing/invalid return identifier |
| `connection_error` | Unable to connect to provider |
| `initiation_failed` | Initiation or local ledger creation failed |
| `lookup_failed` | Payment not confirmed; retry lookup without initiating a second payment |
| `unknown_payment` | Unknown payment or wrong authenticated owner |
| `payment_pending` | Provider pending/initiated; keep retry available |
| `payment_expired` | Provider session expired |
| `payment_refunded` | Provider reports refund; do not create a paid order |
| `amount_too_low` | Less than NPR 10; offer COD or cart changes |
| `session_expired` | Legacy reason supported by UI |
| `no_items` | Missing checkout/snapshot items |
| `cart_empty` | Selected owned rows no longer exist |
| `not_complete` | Other noncompleted status |
| `amount_mismatch` | Provider paid total differs; do not fulfill |
| `database_error` | Money confirmed but order persistence failed; recovery/support needed |
| `unknown` | Generic fallback |

Provider mappings: `Pending` and `Initiated` map to pending; `Refunded` to refunded; `Expired` to expired; `User canceled` to cancelled. Preserve honest copy: the legacy blanket statement that an order was not placed is inappropriate for an uncertain result or a previously completed order.

## Khalti configuration and HTTP contract

These describe observed legacy behavior. Recheck the official provider documentation during the payment implementation batch before relying on current URLs/statuses/timeouts.

| Item | Legacy contract |
| --- | --- |
| Mode | `KHALTI_ENV`, sandbox by default, literal `live` selects production |
| API origin | Sandbox `https://dev.khalti.com/api/v2`; live `https://khalti.com/api/v2`; optional `KHALTI_API_URL` override |
| Secret | `KHALTI_SECRET_KEY`, server only |
| Public app URL | `APP_BASE_URL`; legacy fallback derives scheme/host/path from request |
| Initiation | POST `/epayment/initiate/` with checkout payload |
| Lookup | POST `/epayment/lookup/` with `{ "pidx": "..." }` |
| Authentication | HTTP `Authorization: Key <secret>` |
| Content type | JSON |
| Success handling | HTTP 200 and decoded object |
| Timeouts | 15-second connection; 30-second overall request |
| Attempts | Two for initiation; three for lookup; 500ms delay; stop on 4xx |

Environment files are read once, with process environment taking precedence. Missing secrets produce a configuration error. Error bodies are flattened from provider `detail` or field messages. Legacy logs request failure status and a truncated response body; sensitive values must be redacted in the replacement. Root `.htaccess` blocks `.env` and `.log`, but that is an Apache protection rather than a Django deployment policy.

### Required fresh data model

Model names are architectural recommendations, not a duplicate schema implementation. The backend model owner defines the authoritative migration.

- Payment ledger: owned user FK; optional unique linked order; unique pidx; unique purchase-order identifier; positive integer paisa amount; currency NPR; explicit provider and fulfillment statuses; optional unique provider transaction reference; immutable validated customer/item snapshots; selected cart line identity/version; created/updated timestamps.
- Orders and normalized order lines: immutable product name/unit-price/quantity snapshots and decimal totals, shipping/contact snapshot, payment method/state, linked ledger. Keep order history when product records change or retire.
- Inventory/reservation mechanism: supports atomic checkout, provider wait, cancellation/expiry and eventual verification without overselling.
- Recovery identity: authenticate the owning account or use a scoped signed token that permits only payment reconciliation/status recovery. Knowing a provider identifier alone should not expose customer data.

### Legacy defects that must not be preserved

- Cart price is server-side stored data but may be stale or have originated from untrusted cart fields. Recalculate against authoritative product pricing and validate product availability.
- Quantity updates clamp stock to zero, allowing overselling; products are not locked/stock-checked before fulfillment.
- Completed order total is rounded to integer NPR, losing paisa. Use Decimal/integer minor units consistently.
- The ledger is marked `Completed` before amount/snapshot validation. Separate provider state from fulfillment state.
- Deleting a selected cart row after payment can delete quantities added during the external checkout. Snapshot and reconcile by line identity/version/quantity.
- Expired-session callback exposes receipt details based on pidx possession. Preserve recovery with a limited secure credential.
- Initiation retry after a network timeout may create another provider session. Use documented idempotency/reconciliation semantics and avoid assuming a failed response means no provider-side initiation.
- Return URLs should be configured and validated rather than derived from an arbitrary host header. Validate redirect targets from provider responses.
- Enforce authenticated/authorized CSRF-protected mutations, rate limits, field bounds, and safe user-visible errors.

## Shop map behavior

The page is public; optional PHP session only affects the shared header. Data is fetched from the application, and no external routing service chooses the path.

### View and interactions

- Leaflet 1.9.4 draws markers/lines over OpenStreetMap raster tiles. Default center is Kathmandu `[27.7041, 85.3140]`, zoom 13; tile maximum zoom is 19 and OpenStreetMap attribution is displayed.
- Graph and store data are fetched concurrently. The UI reports loading/failure and loaded store/intersection/road counts.
- After load, geolocation is requested automatically. Use My Location explicitly repeats it. Options: high accuracy, 10s timeout, 60s cached position. Unsupported/denied/unavailable location directs the visitor to manual map selection.
- Clicking the map sets origin and green marker. Store list distances and selected-store details refresh.
- Search filters store cards by case-insensitive name or address substring; map markers remain visible. Empty results have a message.
- Store markers have name/address/phone popups. Selecting a marker or card highlights its card, zooms to 15, opens popup and shows details.
- Store details include name/address/phone, optional hours, numeric rating or unrated label, origin-to-store direct distance, and Find Shortest Route.
- Routing requires origin and selected shop. It snaps both ends to nearest graph vertices, runs Dijkstra and displays a green route plus dashed direct connectors and intersection markers.
- Results include road distance, total distance including connectors, estimated duration, segment count, start label, network entry/exit names and distances, destination, visited/total vertex count and each road leg's endpoints/distance.
- Show/Hide Road Graph toggles orange roads and intersection dots, with road-name/distance tooltips.
- Clear Route removes route/results only; origin, selected shop, data and graph overlay remain.
- The layout is sidebar + map/results, collapsing to a single column below 991px. Existing map heights are 520px, 450px below 991px and 380px below 768px. React should maintain accessible responsive behavior with shadcn/ui controls and Lucide icons around Leaflet.

### API contracts

Both PHP APIs permit GET only (405 otherwise), return JSON with numeric coordinates and safe 500 errors, and currently create/seed schema during reads. Django must perform no schema mutation in HTTP handlers.

`api/get_shops.php` accepts optional `search`, trimmed and capped at 100 characters. It returns only active shops ordered by name, using SQL LIKE on name/address.

```json
{
  "success": true,
  "count": 0,
  "shops": []
}
```

Each shop object contains integer `shop_id`, `shop_name`, `address`, numeric `latitude`/`longitude`, `phone`, nullable numeric `rating`, nullable `opening_hours`.

`api/get_graph.php` returns `{ "success": true, "nodes": [], "edges": [] }`. Nodes are ordered by ID; each has integer `node_id`, `node_name`, numeric `latitude`/`longitude`. Edges are ordered by edge ID and contain integer `from_node`, integer `to_node`, nullable `road_name`. Distances are deliberately not stored or returned; they derive from coordinates.

### Fresh schema requirements

| Entity | Legacy fields and constraints | Required stronger constraints |
| --- | --- | --- |
| Shop | Name 100, address 255, decimal(10,7) lat/lng, phone 20, nullable decimal(2,1) rating, nullable hours 60, active boolean | Latitude -90..90, longitude -180..180, rating 0..5, bounded validated strings |
| Node | Name 100, decimal(10,7) lat/lng | Geographic bounds, stable identity |
| Edge | From/to node FKs with cascade, optional road name 100, unique ordered pair | No self-loop, no duplicate reversed undirected pair; normalize ordering or equivalent constraint |

Legacy source starter data has 20 Kathmandu intersections, 29 roads, and 8 outlets. `map_schema.php` inserts these whenever the corresponding table is empty; SQL dump duplicates the data. These are a coarse demonstration graph and unverified outlet records, not a complete street network. The new application must fetch real persisted records, support deliberate administrator/import maintenance, and handle an initially empty fresh database honestly. Do not silently hardcode starter shop/graph data into React as a working-data substitute. If source starter content is deliberately imported later, label provenance and limitations explicitly.

### Routing algorithm

- Haversine weights in metres with Earth radius 6,371,000m; undirected adjacency list expands each road to both directions.
- Binary minimum heap, lazy stale-entry skipping, finalized visited set, early stop at destination, predecessor reconstruction.
- `buildGraph` maps string node IDs, ignores edges referencing missing vertices, and keeps a unique edge list for drawing.
- `findNearestNode` returns closest node ID and direct Haversine connector distance.
- `dijkstra` returns `found`, `path`, `distance`, `hops`, `visitedCount`, trace `steps`, and an optional error. Missing endpoints and disconnected paths return failure, empty path, infinite distance and explanatory text.
- Distance formatting: rounded metres below 1000; two-decimal kilometres otherwise; nonfinite values show unreachable.
- Duration estimate: 20km/h along graph and 4.5km/h connectors; rounded minutes, under a minute/minutes/hours display.
- Keep routing in a typed pure module separate from Leaflet/React. It must operate on API data, not a built-in substitute graph.
- Fix stale route output when origin/destination changes. Guard empty graph and loading states, reject invalid coordinates/weights, bound numerical Haversine roundoff, preserve rating 0 as a value, and make selection keyboard accessible.

## Verification gates

These checks are pending until their associated feature batch is implemented. A passing foundation check does not complete payment/map migration.

### Payments

- [ ] Protected API rejects anonymous initiation and another user's cart lines.
- [ ] CSRF, rate limits and malformed/bounded checkout input are enforced.
- [ ] Price tampering, stale product price, invalid stock/quantity and below-minimum amounts are rejected correctly.
- [ ] COD and Khalti preserve selected-only checkout and owned line isolation.
- [ ] Initiation persists an immutable snapshot and handles provider/DB/network errors without false success.
- [ ] Missing/unknown/foreign pidx, malformed response, pending, expired, refunded, cancelled and lookup outage show correct recovery behavior.
- [ ] Forged callback status cannot place an order; amount mismatch cannot fulfill.
- [ ] Repeat and concurrent verification produce exactly one order and inventory deduction.
- [ ] Inventory race, payment/cart mutation, deleted/retired product and fractional NPR amount scenarios are tested.
- [ ] Completed-payment persistence failure can safely reconcile later.
- [ ] Expired-session recovery exposes only scoped authorized information.
- [ ] Receipt, order history/admin, cart cleanup, failure retry and redirects work through React and Django together.
- [ ] Real sandbox transaction/cancel/recheck is exercised with explicitly configured valid credentials; live payment is not implied by sandbox tests.

### Map

- [ ] Fresh PostgreSQL APIs list/search only active stores and return actual persisted graph records.
- [ ] Model/API validation rejects invalid coordinates, ratings, dangling/self/duplicate-undirected edges and unauthorized mutations.
- [ ] Empty database/network, API failure and loading states render honestly.
- [ ] Algorithm tests cover competing paths, same endpoint, missing/disconnected nodes, nearest node, distance and formatting.
- [ ] Map tiles/attribution, store marker/list selection, filtering, origin changes, geolocation accepted/denied and manual origin work in a browser.
- [ ] Route lines/connectors, graph overlay, metrics, per-leg breakdown, clear route and stale-result invalidation agree with algorithm output.
- [ ] Responsive and keyboard interactions use the shared shadcn/ui design system.
- [ ] No PHP/MySQL dependency or legacy database access remains in the running replacement.

## Foundation tooling provenance

The PostgreSQL project directs Windows users to EDB distributions and documents the binary ZIP option: [PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/).

The official [EDB binary downloads page](https://www.enterprisedb.com/download-postgresql-binaries) advertised PostgreSQL 17.11 for Windows x64 during this audit. Its download link `https://sbp.enterprisedb.com/getfile.jsp?fileid=1260616` redirected to `https://get.enterprisedb.com/postgresql/postgresql-17.11-5-windows-x64-binaries.zip`. The foundation task downloads/extracts this package under workspace `.tools/pgsql` only. Cluster initialization, database creation, and migration execution are separate foundation responsibilities. A local SHA-256 records downloaded bytes; without a publisher checksum it is not independent signature verification.
