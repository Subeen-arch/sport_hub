# Customer application audit

Audited the checked-in PHP, templates, JavaScript, CSS, assets and SQL. The existing database was not accessed. This inventory describes the actual source, including workflows absent from the incomplete SQL dump. Security defects are recorded for correction, not compatibility.

## Technology and shared presentation

Every customer page includes the PDO connection, starts a PHP session, emits HTML and handles its own POST/GET actions. Shared includes provide navigation, notifications and cart/wishlist actions. There is no frontend router, build pipeline or dependency manifest. CSS is handwritten, with a green `#00bf63` primary, off-white backgrounds, orange warnings and red destructive actions. Nunito loads from Google Fonts; Font Awesome 6.1.1 supplies icons. Swiper 8 drives promotional, category, offer and review carousels. JavaScript toggles mobile navigation/account menus and has dormant thumbnail-switch code. Responsive breakpoints are 991px, 768px and 450px.

The header links Home, About, Shop, Shop Map and Contact, with Orders visible to signed-in customers. Search, wishlist and cart icons remain visible to guests. Counts represent distinct rows, not total quantities. The profile dropdown shows the customer's name, profile update, orders and logout confirmation; guests see login/register. Menus close on scroll. Notifications can be dismissed. An announcement promotes discounts and free delivery above Rs 3000; the checkout contains no shipping-fee calculation.

## Page and workflow inventory

| Legacy source | New route | Functionality and interactions |
| --- | --- | --- |
| `home.php` | `/` | Three original hero slides and shop links, seven sport category links, special-offer carousel, featured grid, latest product grid, sorting, pagination dots for carousels |
| `shop.php` | `/shop` | Category, brand, minimum price, maximum price, stock availability filters; sorting; Apply and Reset; product cards and empty state |
| `category.php` | `/categories/:slug` | Product listing for a sport category; quantities bounded by stock; wishlist/cart actions; empty state |
| `search_page.php` | `/search` | Required search term up to 100 characters; product-name substring search; results with wishlist/cart actions and empty state |
| `quick_view.php` | `/products/:id` | Single product image, complete description, price, quantity, stock availability, add to cart/wishlist; missing-product state |
| `cart.php` | `/cart` | Owned cart list, per-line checkbox, quantity update, item removal and clear-all confirmation, subtotals and total, continue shopping, checkout selected items |
| `wishlist.php` | `/wishlist` | Owned wishlist, per-product quantity and move-to-cart, remove/clear confirmations, aggregate total, continue shopping |
| `checkout.php` | `/checkout` | Selected owned items and total, contact/delivery form, cash on delivery or Khalti, order creation, stock decrement, removal of purchased rows only |
| `orders.php` | `/orders` | Newest-first order history with date/contact/address, product snapshots/images/quantity/unit price, total, payment method, Khalti reference and status |
| `user_login.php` | `/login` | Email/password form, incorrect-credentials notice, register link; successful login redirects home |
| `user_register.php` | `/register` | Name/email, Nepal or India dialing code, ten-digit phone, password and confirmation, validation notices, login link |
| `update_user.php` | `/account` | Edit name/email and change password using old/new/confirmation fields |
| `contact.php` | `/contact` | Guest or customer contact submission, duplicate detection, success/error notification |
| `about.php` | `/about` | Original SportHub mission, about illustration, Contact link, four testimonial slides with photo and 4.5-star display |
| `components/user_logout.php` | Session logout action | Clear session and return home |

The map and Khalti integration inventories are maintained separately. No customer product-review creation, coupon, shipping calculator, password-reset, order-cancellation or order-tracking event system exists in these sources.

### Catalog behavior

- Hero content: latest Nike football and cricket kit at up to 50% off, basketball at up to 70% off. Existing artwork is reusable editorial content; no product data should be invented to populate an empty new database.
- Sport links: Football, Cricket, Basketball, Badminton, Fitness, Volleyball and Table Tennis. The SQL category seeds omit Badminton even though it has a home link and icon.
- Special offers: `discount_percent > 0`, highest discount first, maximum ten products, original price struck out, discount badge, calculated sale price and stock-aware cart form.
- Featured: `featured = 1`, descending product ID, maximum six. Latest: selected ordering, maximum twelve. Shop has no limit.
- Sort options: newest, oldest, price low/high, price high/low, name A/Z, name Z/A.
- Shop category names come from the category table; brands come from distinct nonempty product brands. Stock filters distinguish positive and zero stock.
- Product cards show image/name/description excerpt, price, wishlist, detail and cart. More than three units shows In Stock; one to three shows Only N Left; zero disables purchasing. Quantity starts at one and is bounded by available stock; older templates also limit typing to two digits.
- The effective discounted price is `original_price * (1 - discount_percent / 100)`. The migrated backend must own price calculation and round consistently to two decimals.
- Category and search implementations currently interpolate substring queries; migration must use ORM filtering and normalized category relationships.

### Cart and wishlist behavior

- Both require a signed-in customer. Anonymous add attempts redirect to login.
- Wishlist rejects an existing wishlist product and products already in the customer's cart.
- Cart add rejects duplicate products rather than silently increasing quantity. A successful add removes the corresponding wishlist item.
- Cart add verifies stock and clamps requested quantity to at least one. Requests above availability report the available count. The new implementation should reject malformed/nonpositive values instead of silently accepting them.
- Legacy duplicate checks use product name; new uniqueness must use the user/product relationship.
- Cart supports updating quantity, removing an item, clearing all, totals and explicit selection for checkout. Subtotals are unit price times quantity. Cart and checkout refresh discounted prices.
- Selecting zero items prevents proceeding. Selected IDs are held in the PHP session for checkout refreshes and Khalti handoff. A React implementation must preserve selected IDs through refresh/payment navigation while rechecking ownership on the backend.
- Wishlist total is one unit per item. Removal and clear actions require confirmation.

### Checkout and order history

- Required form fields: recipient name, phone, email, flat, street, city, state/province, country and postcode. Payment options are cash on delivery and Khalti only.
- Only selected cart rows belonging to the current user are included. Order lines and total are rebuilt server-side; unselected rows remain in the cart.
- COD stores contact details, a concatenated address, JSON product snapshots (name, price, quantity, product ID and image), total and pending status. A transaction inserts the order, decrements product quantity and deletes purchased cart rows.
- The existing COD flow does not recheck availability at purchase and clamps inventory to zero, so it can oversell. New order creation must lock/recheck stock and remain atomic.
- Khalti stores pending details in session and redirects to `khalti_payment.php`; its detailed lifecycle is covered in the integration audit.
- History shows newest first; guests see a login instruction. Customer contact, address, original item details, date/time, total, payment method/reference and order status are retained. Existing status mixes payment and fulfillment semantics and should be separated in the new model while preserving displayed information.

### Accounts and contact validation

- Registration name maximum 20; email maximum 50; password maximum 20 in legacy HTML. Client validation requires a syntactically valid email, ten phone digits, password minimum eight and a special character, and matching confirmation. Dialing codes are +977 and +91.
- **Phone persistence defect:** phone/country controls have no submitted field names, and users table has no phone fields. New registration should persist these visible user inputs.
- Legacy passwords use SHA1; session login queries email/hash. New users must use Django password hashing and server-enforced validation. No existing accounts/password hashes are to be imported.
- Duplicate email checks exist on registration only, without a database unique constraint. New email identity must be normalized and unique.
- Profile updates save name/email before checking password, and trust a hidden copy of the previous hash. New APIs must authenticate ownership, never expose hashes, validate unique email, and verify current password server-side before password changes.
- Contact accepts guests and signed-in users. Name max20/email max50 and phone up to ten digits are HTML constraints; message is optional in HTML but SQL limits it to 500. Exact duplicate name/email/phone/message submissions are rejected.
- About testimonials are original static content by Ayush Shrestha, Subika Maharjan, Anmol Shrestha and Khushi Pachhai. They are editorial copy with original photos, not dynamic customer review records.

## Schema requirements and defects

Required commerce entities: customer/admin identity, category, product, cart item, wishlist item, order, immutable order line and contact message. Product requirements include name, description, category, brand, image, original/effective price, discount percentage, quantity and featured flag. Money requires decimal storage; stock and order/cart quantities require constraints. Cart and wishlist need user/product uniqueness and foreign keys. Orders need structured delivery fields and preserved line snapshots, with independent payment/fulfillment status. Message user ownership should be nullable for guest submissions.

The SQL file is a source artifact, not a valid migration: it starts with stray `admins`, contains `PRIMARY KEY (id)cart`, adds `featured` after a nonexistent-yet `discount_percent`, and omits product `brand`, `stock` and `quantity` fields required by PHP. Its cart/wishlist/order amounts are integer columns. Most relationships lack foreign keys and uniqueness. Build fresh PostgreSQL models and migrations from the complete source requirements; never execute/import this dump into the new system.

## Security corrections required

The migration must eliminate client-supplied price/name/image authority, raw search SQL interpolation, cross-user cart/wishlist edits and deletion, GET mutations, missing CSRF, exposed password hashes, SHA1 hashing, incomplete validation, unescaped output and overselling. Use session rotation, secure cookies, CSRF for unsafe requests, owner-scoped querysets, Django password validation, database constraints, transaction locks and server-owned payment/price calculations. These defects are not business rules to preserve.
