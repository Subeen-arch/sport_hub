# SportHub API contract

This document is the agreed integration contract. The migration checklist records which batches have implemented and tested each endpoint. All routes have a trailing slash and return JSON under `/api/`; there are no PHP routes or legacy database connections in the new application.

## Transport, authentication, validation

- React and Django share an origin in production. Vite proxies `/api/` and `/media/` during development. Requests include credentials.
- Django session cookies are HttpOnly and SameSite=Lax, Secure outside development. Obtain `{ "csrfToken": "..." }` from `GET /api/auth/csrf/`, then send `X-CSRFToken` with every unsafe request, including login and registration. Refresh this token after login/registration because Django rotates it.
- Staff authentication accepts username/password; customers authenticate with email/password. Registration cannot grant staff privileges.
- `GET /api/auth/me/` returns the current user. Anonymous access to protected resources returns 401 or 403; the frontend treats either as unauthenticated. Authenticated customers receive 403 from staff-only resources.
- DRF field errors use `{ "field": ["message"] }`; general errors use `{ "detail": "message" }` or `non_field_errors`. Validation errors are 400, missing objects 404, successful creation 201, deletion 204.
- Monetary values are decimal strings in NPR, e.g. `"1999.50"`; gateway amounts are server-computed integer paisa. IDs are integers unless described as UUIDs. Dates use timezone-aware ISO 8601.
- Paginated resources use `{ "count": 42, "next": "...", "previous": null, "results": [...] }`, 24 items per page. Requests can follow next/previous links or supply `?page=2`.
- All mutations run server-side validation. Client-supplied user IDs, totals, product prices, role flags, and payment outcomes are never authoritative.

## Resources

User: `{ id, username, name, email, phone, country_code, is_staff }`.

Category: `{ id, name }`.

Product: `{ id, name, category, category_name, brand, details, original_price, discount_percent, price, quantity, featured, image, stock_status, created_at, updated_at }`. `category` is an integer FK; `image` is an HTTP URL or relative media URL; `stock_status` is `out_of_stock`, `low_stock` (1–3), or `in_stock`. `price` is read-only and rounded to two decimal places. Prices and stock come from the database. Six featured products maximum.

CartItem: `{ id, product: Product, quantity, subtotal }`. Product prices remain current until checkout snapshots them. WishlistItem: `{ id, product: Product }`.

Order: `{ id, reference, name, email, phone, country_code, flat, street, city, region, postal_code, country, method, fulfillment_status, payment_status, total, currency, transaction_id, payment_ref, created_at, items: OrderItem[] }`.

OrderItem: `{ id, product, name, image, unit_price, quantity, subtotal }`. Product can become null after catalog deletion; order snapshots remain intact.

Order payment methods: `cod`, `khalti`. Fulfillment stages: `pending`, `Dispatched`, `completed`. Payment settlement is separately `pending`, `paid`, or `refunded`; gateway verification is the only source of paid status for Khalti.

Checkout input: `{ cart_item_ids: number[], name, email, phone, country_code, flat, street, city, region, postal_code, country }`. `cart_item_ids` must be nonempty, unique, owned by the current customer, and available. The server snapshots and totals the selected current products, never all cart rows implicitly. All delivery fields are required; `region` maps to the legacy state field and `postal_code` maps to its pin code. Contact and address fields are validated. Only selected rows are removed after successful ordering.

## Foundation (Batch 1)

| Method | URL | Response |
|---|---|---|
| GET | `/api/health/` | `{ status: "ok", service: "sporthub-api" }` (liveness only) |

## Accounts (Batch 2)

| Method | URL | Input / response |
|---|---|---|
| GET | `/api/auth/csrf/` | `{ csrfToken }` |
| GET | `/api/auth/me/` | User |
| POST | `/api/auth/register/` | `{ name, email, password, password_confirm, phone, country_code }` → User, session starts; phone exactly 10 digits, country code `+977` or `+91` |
| POST | `/api/auth/login/` | `{ email, password }` or `{ username, password }` → User, session starts |
| POST | `/api/auth/logout/` | `{}` → 204 |
| PATCH | `/api/auth/profile/` | `{ name?, email?, phone?, country_code?, username? }` → User; username editable for staff |
| POST | `/api/auth/password/` | `{ old_password, new_password, password_confirm }` → `{ detail }`; current session retained |

Passwords use Django password hashing and validation (minimum eight characters and a special character, not common/numeric or similar to identity); no password or hash is returned. Identity uniqueness is case-insensitive.

`GET /api/admin/session/` returns the User for staff only; customers and guests receive 403. Account input rejects unexpected fields, including role flags and user IDs. Customer usernames are generated by the server; username login is staff-only. Account responses use `Cache-Control: no-store`. Login, registration and password changes are limited to ten requests per minute per throttle identity; production deployments must use a shared cache when running multiple workers. Password changes invalidate other sessions while retaining the current one. The CSRF cookie is HttpOnly: obtain the masked token from the CSRF endpoint, not `document.cookie`.

## Public catalog and content (Batch 3)

| Method | URL | Behavior |
|---|---|---|
| GET | `/api/categories/` | Paginated alphabetical categories |
| GET | `/api/products/` | Paginated catalog; filters `search` (name/details/brand), `category` (ID), `category_name` (substring), `brand`, `min_price`, `max_price`, `stock` (`in_stock`/`out_of_stock`), `featured=true`, `discounted=true`; `ordering` (`-id`, `id`, `price`, `-price`, `name`, `-name`, `-discount_percent`) |
| GET | `/api/products/{id}/` | Product |
| GET | `/api/catalog/options/` | `{ brands: string[] }`, distinct nonempty brands in alphabetical order |
| POST | `/api/messages/` | `{ name, email, phone, country_code?, message }` → saved ContactMessage; guest allowed, authenticated user associated automatically |

Static about/announcement content is React content, not fabricated database data. Empty database listings render honest empty states.

## Customer commerce (Batch 4)

| Method | URL | Behavior |
|---|---|---|
| GET | `/api/cart/` | `{ items: CartItem[], total, count }` for authenticated owner |
| POST | `/api/cart/` | `{ product_id, quantity }` → CartItem; validates stock and rejects existing item (update separately); atomically removes that product from the owner's wishlist |
| PATCH | `/api/cart/{id}/` | `{ quantity }` → CartItem |
| DELETE | `/api/cart/{id}/` | Remove owned row |
| DELETE | `/api/cart/clear/` | Remove all owned rows |
| GET | `/api/wishlist/` | `{ items: WishlistItem[], count }` |
| POST | `/api/wishlist/` | `{ product_id }` → WishlistItem, duplicate rejected |
| DELETE | `/api/wishlist/{id}/` | Remove owned row |
| DELETE | `/api/wishlist/clear/` | Remove all owned wishlist rows |
| POST | `/api/orders/checkout/` | Checkout input → COD Order; stock locked, validated, decremented atomically |
| GET | `/api/orders/` | Paginated own order history |
| GET | `/api/orders/{id}/` | Own Order only |

Successful cart creation and removal of the matching wishlist item occur in one backend transaction. Failed cart creation leaves the wishlist unchanged.

Cart quantities are positive integers; duplicate products must be updated explicitly. Wishlist additions reject products already in the owner's cart. Available stock excludes active payment reservations. Checkout accepts at most 100 distinct cart rows, checks their ownership and current inventory, snapshots current Decimal prices, and removes only purchased rows. Repeating the same checkout after success returns 400 because its cart rows no longer exist. Checkout selections are carried in the frontend URL (`/checkout?items=1,2`) so refresh preserves them; the server independently validates every ID. The frontend retains delivery inputs after a failed submission and links to order history for recovery after an uncertain network response.

## Khalti (Batch 5)

| Method | URL | Behavior |
|---|---|---|
| GET | `/api/payments/config/` | `{ khalti_enabled, environment }`; no keys |
| POST | `/api/payments/khalti/initiate/` | Checkout input → `{ pidx, payment_url, expires_at }`; real gateway request only |
| POST | `/api/payments/khalti/verify/` | `{ pidx }` → `{ status, order }`; server lookup, ownership/amount/purchase reference verification, idempotent settlement |

Khalti returns the browser to `/payment/return?pidx=...`; React invokes verification with CSRF. The response order is null unless checkout was finalized. A failed/canceled/pending gateway session preserves the selected cart. Payment snapshots and inventory reservations prevent concurrent checkouts overselling reserved units. A database ledger makes repeat callbacks idempotent. Missing configuration returns an actionable unavailable error, never simulated payment success. Exact expiry/reconciliation policy is documented with the payment batch.

## Staff administration (catalog in Batch 3; remaining workflows in Batch 4)

| Method | URL | Behavior |
|---|---|---|
| GET | `/api/admin/dashboard/` | `{ pending_total, completed_total, order_count, product_count, customer_count, admin_count, message_count, featured_count }` |
| GET/POST | `/api/admin/products/` | Paginated searchable products / multipart create |
| GET/PATCH/DELETE | `/api/admin/products/{id}/` | Retrieve/update/delete catalog product |
| GET/POST | `/api/admin/categories/` | Paginated categories / `{ name }` → Category |
| GET/PATCH/DELETE | `/api/admin/categories/{id}/` | Retrieve/rename/delete category; categories containing products cannot be deleted |
| GET | `/api/admin/orders/` | Paginated all orders; `status` fulfillment filter |
| GET/PATCH/DELETE | `/api/admin/orders/{id}/` | Retrieve/update `{ fulfillment_status }`/delete order; cannot forge Khalti paid status |
| GET | `/api/admin/users/` | Paginated customers |
| DELETE | `/api/admin/users/{id}/` | Confirmed customer deletion with related cart/wishlist/messages/orders and payment records |
| GET/POST | `/api/admin/accounts/` | Paginated staff / `{ username, name, email, password, password_confirm }` → new staff |
| DELETE | `/api/admin/accounts/{id}/` | Delete another staff; reject current user/last active staff |
| GET | `/api/admin/messages/` | Paginated contact submissions |
| DELETE | `/api/admin/messages/{id}/` | Delete contact submission |

Product multipart input: `name`, `category` ID, `brand`, `details`, `original_price`, `discount_percent`, `quantity`, `featured`, required `image` on create/optional on update. Image content is validated, restricted to JPEG/PNG/WebP, limited to 2,000,000 bytes, and stored under generated filenames. Deleting products removes cart/wishlist rows but preserves historical order snapshots; active reservations block deletion.

Staff order completion also marks COD payment collected; it never changes Khalti settlement. Completed orders cannot be reopened. Order deletion removes the record without restocking or refunding. Dashboard `pending_total` sums pending/dispatched order values; `completed_total` sums completed order values (these are fulfillment totals, not gateway settlement reports). Account deletion rejects the current user, the last active staff account, and accounts with active payment reservations. Creating staff never grants superuser privileges or replaces the creator's session. Commerce, order and staff responses are not cached.

## Outlet map (Batch 6)

Shop: `{ id, name, address, latitude, longitude, phone, rating, opening_hours, is_active }`.
MapNode: `{ id, name, latitude, longitude }`; MapEdge: `{ id, from_node, to_node, road_name }`.

| Method | URL | Behavior |
|---|---|---|
| GET | `/api/outlets/` | `{ shops: Shop[] }`, active only |
| GET | `/api/outlets/graph/` | `{ nodes: MapNode[], edges: MapEdge[] }` |
| GET/POST | `/api/admin/outlets/` | Paginated outlet management / create |
| GET/PATCH/DELETE | `/api/admin/outlets/{id}/` | Outlet management |
| GET/POST | `/api/admin/map-nodes/` | Paginated graph nodes / create |
| PATCH/DELETE | `/api/admin/map-nodes/{id}/` | Node management |
| GET/POST | `/api/admin/map-edges/` | Paginated graph edges / create |
| PATCH/DELETE | `/api/admin/map-edges/{id}/` | Edge management |

Map APIs contain real configured data; no automatic sample-shop creation. Coordinates are range-constrained; edges reference valid distinct nodes. The frontend computes Haversine weights and undirected Dijkstra routes, including geolocation connectors, reachability feedback, and distance/time estimates. Staff management permits fresh database operation without legacy imports.
