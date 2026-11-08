"""Opt-in real-browser checks using only Django's disposable PostgreSQL test DB."""
import os
from pathlib import Path
import shutil
import subprocess
import time
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import urlopen

from django.core.cache import cache
from django.test import LiveServerTestCase, override_settings

from .models import User


@skipUnless(os.getenv("SPORTHUB_BROWSER_TESTS") == "1", "Set SPORTHUB_BROWSER_TESTS=1 for browser checks.")
@override_settings(CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5174"])
class IdentityBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"
    frontend_url = "http://127.0.0.1:5174"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(__file__).resolve().parents[2]
        bundled_nodes = list((root / ".tools").glob("node-*-win-x64/node.exe"))
        node = str(bundled_nodes[0]) if bundled_nodes else shutil.which("node")
        if not node:
            raise RuntimeError("Install Node.js before running browser checks.")
        runtime = root / ".runtime"
        runtime.mkdir(exist_ok=True)
        log = (runtime / "identity-browser-vite.log").open("w", encoding="utf-8")
        cls.addClassCleanup(log.close)
        cls.frontend = subprocess.Popen(
            [node, "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5174"],
            cwd=root / "frontend", env={**os.environ, "API_PROXY_TARGET": cls.live_server_url},
            stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        cls.addClassCleanup(cls.stop_frontend)
        for _ in range(100):
            if cls.frontend.poll() is not None:
                raise RuntimeError("Vite exited; check .runtime/identity-browser-vite.log and free port 5174.")
            try:
                with urlopen(cls.frontend_url, timeout=1):
                    break
            except (URLError, TimeoutError):
                time.sleep(0.2)
        else:
            raise RuntimeError("Vite did not become ready.")

    @classmethod
    def stop_frontend(cls):
        cls.frontend.terminate()
        try:
            cls.frontend.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.frontend.kill()
            cls.frontend.wait(timeout=5)

    def setUp(self):
        from playwright.sync_api import sync_playwright

        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        media_override = override_settings(MEDIA_ROOT=media.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        cache.clear()
        User.objects.create_user(username="BrowserCoach", name="Browser Coach", email="coach@example.com", password="Staff!Browser8426", is_staff=True)
        if self._testMethodName.startswith('test_commerce_'):
            from catalog.models import Category, Product
            from catalog.test_api import raster_upload
            from commerce.models import CartItem
            from commerce.services import CheckoutService
            from commerce.test_api import delivery
            from support.models import ContactMessage
            runner = User.objects.create_user(username='BrowserRunner', name='Browser Runner', email='runner@example.com', phone='9812345678', password='Runner!Trail8426')
            category = Category.objects.create(name='Football')
            ball = Product.objects.create(name='Training ball', category=category, details='For practice', original_price='99.95', discount_percent=10, quantity=5, image=raster_upload())
            boots = Product.objects.create(name='Training boots', category=category, details='For the pitch', original_price='1000', quantity=2, image=raster_upload())
            self.ball_id, self.boots_id = ball.pk, boots.pk
            ContactMessage.objects.create(name='Guest Runner', email='guest@example.com', phone='9812345678', message='Do you have training gear?')
            if self._testMethodName == 'test_commerce_staff_workflows':
                cart = CartItem.objects.create(user=runner, product=ball, quantity=2)
                self.order_id = CheckoutService().place_cod(runner, delivery([cart.pk])).pk
        # Start Playwright after ORM setup; stop its event loop before Django flushes.
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        channel = os.getenv("SPORTHUB_BROWSER_CHANNEL")
        self.browser = self.playwright.chromium.launch(headless=True, **({"channel": channel} if channel else {}))
        self.addCleanup(self.browser.close)
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))

    def tearDown(self):
        self.assertEqual(self.page_errors, [])

    def test_customer_account_lifecycle_and_mobile_navigation(self):
        from playwright.sync_api import expect

        page = self.page
        page.goto(self.frontend_url + "/account")
        expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / ".runtime/identity-login-desktop.png"), full_page=True)
        page.get_by_role("link", name="Create an account").click()
        page.get_by_label("Full name", exact=True).fill("Browser Runner")
        page.get_by_label("Email address", exact=True).fill("browser@example.com")
        page.get_by_label("Phone number", exact=True).fill("9812345678")
        page.get_by_label("Password", exact=True).fill("Trail!Browser8426")
        page.get_by_label("Confirm password", exact=True).fill("Trail!Browser8426")
        page.get_by_role("button", name="Create account", exact=True).click()
        expect(page.get_by_role("heading", name="My account", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_label("Full name", exact=True)).to_have_value("Browser Runner")
        page.get_by_label("Full name", exact=True).fill("Updated Runner")
        page.get_by_role("button", name="Save changes").click()
        expect(page.get_by_role("status")).to_contain_text("Your profile has been updated.")
        page.get_by_label("Current password", exact=True).fill("Trail!Browser8426")
        page.get_by_label("New password", exact=True).fill("Summit!Browser8426")
        page.get_by_label("Confirm new password", exact=True).fill("Summit!Browser8426")
        page.get_by_role("button", name="Update password").click()
        expect(page.get_by_text("Password changed successfully.", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_role("heading", name="My account", exact=True)).to_be_visible()
        page.goto(self.frontend_url + "/admin")
        expect(page.get_by_role("heading", name="Staff access required")).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="Open navigation").click()
        page.get_by_role("navigation", name="Mobile navigation").get_by_role("link", name="My account").click()
        expect(page.get_by_role("heading", name="My account", exact=True)).to_be_visible()
        self.assertFalse(page.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / ".runtime/identity-account-mobile.png"), full_page=True)
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.get_by_role("alertdialog").get_by_role("button", name="Sign out", exact=True).click()
        expect(page.get_by_role("link", name="Sign in", exact=True).first).to_be_visible()
        page.goto(self.frontend_url + "/login")
        page.get_by_label("Email address").fill("BROWSER@example.com")
        page.get_by_label("Password", exact=True).fill("Summit!Browser8426")
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("heading", name="My account", exact=True)).to_be_visible()

    def test_staff_login_and_invalid_credentials(self):
        from playwright.sync_api import expect

        page = self.page
        page.goto(self.frontend_url + "/admin")
        expect(page.get_by_role("heading", name="Staff sign in", exact=True)).to_be_visible()
        page.get_by_label("Staff username", exact=True).fill("BROWSERCOACH")
        page.get_by_label("Password", exact=True).fill("wrong")
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("The sign-in details are incorrect.")
        page.get_by_label("Password", exact=True).fill("Staff!Browser8426")
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("heading", name="Staff workspace", exact=True)).to_be_visible()
        expect(page.get_by_text("Your staff account is active.", exact=False)).to_be_visible()

    def test_catalog_staff_crud_and_public_browsing(self):
        from playwright.sync_api import expect
        from catalog.test_api import raster_upload

        page = self.page
        page.goto(self.frontend_url + "/admin/catalog")
        page.get_by_label("Staff username", exact=True).fill("BrowserCoach")
        page.get_by_label("Password", exact=True).fill("Staff!Browser8426")
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("heading", name="Manage catalog")).to_be_visible()
        page.get_by_label("New category name").fill("Football")
        page.get_by_role("button", name="Add category", exact=True).click()
        expect(page.get_by_text("Category saved.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Add product", exact=True).click()
        editor = page.get_by_role("form", name="Product editor")
        editor.get_by_label("Product name", exact=True).fill("Browser match ball")
        editor.get_by_label("Category", exact=True).select_option(label="Football")
        editor.get_by_label("Brand", exact=True).fill("Sport Brand")
        editor.get_by_label("Original price (NPR)").fill("99.95")
        editor.get_by_label("Discount (%)").fill("10")
        editor.get_by_label("Stock quantity").fill("5")
        editor.get_by_label("Description", exact=True).fill("A durable match ball.")
        editor.get_by_label("Featured", exact=False).check()
        editor.get_by_label("Product image", exact=True).set_input_files({"name": "ball.png", "mimeType": "image/png", "buffer": raster_upload().read()})
        editor.get_by_role("button", name="Save product").click()
        expect(page.get_by_text("Product saved.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Edit Browser match ball", exact=True).click()
        editor.get_by_label("Stock quantity").fill("2")
        editor.get_by_role("button", name="Save product").click()
        expect(page.get_by_text("2 in stock", exact=False)).to_be_visible()
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / ".runtime/catalog-admin-desktop.png"), full_page=True)

        page.get_by_role("button", name="Sign out", exact=True).click()
        page.get_by_role("alertdialog").get_by_role("button", name="Sign out", exact=True).click()
        expect(page.get_by_role("heading", name="Featured picks")).to_be_visible()
        expect(page.get_by_role("heading", name="Browser match ball").first).to_be_visible()
        page.goto(self.frontend_url + "/shop")
        page.get_by_label("Brand", exact=True).select_option(label="Sport Brand")
        page.get_by_label("Minimum price (NPR)").fill("89.96")
        page.get_by_label("Maximum price (NPR)").fill("89.96")
        page.get_by_role("button", name="Apply filters").click()
        expect(page.get_by_text("1 products", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_label("Minimum price (NPR)")).to_have_value("89.96")
        page.get_by_role("link", name="View Browser match ball", exact=True).click()
        expect(page.get_by_role("heading", name="Browser match ball", exact=True)).to_be_visible()
        expect(page.get_by_text("Only 2 left", exact=True)).to_be_visible()
        expect(page.get_by_text("A durable match ball.", exact=True)).to_be_visible()
        page.goto(self.frontend_url + "/categories/football")
        expect(page.get_by_role("heading", name="Browser match ball", exact=True)).to_be_visible()
        page.goto(self.frontend_url + "/search?search=missing")
        expect(page.get_by_text("No products found.", exact=False)).to_be_visible()
        page.goto(self.frontend_url + "/shop")
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_role("heading", name="Browser match ball", exact=True)).to_be_visible()
        self.assertFalse(page.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / ".runtime/catalog-shop-mobile.png"), full_page=True)

        page.goto(self.frontend_url + "/admin/login")
        page.get_by_label("Staff username", exact=True).fill("BrowserCoach")
        page.get_by_label("Password", exact=True).fill("Staff!Browser8426")
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("heading", name="Staff workspace", exact=True)).to_be_visible()
        page.get_by_role("link", name="Manage catalog", exact=True).click()
        page.get_by_role("button", name="Delete category Football", exact=True).click()
        dialog = page.get_by_role("alertdialog")
        dialog.get_by_role("button", name="Delete", exact=True).click()
        expect(dialog.get_by_role("alert")).to_contain_text("Move or delete")
        dialog.get_by_role("button", name="Cancel", exact=True).click()
        page.get_by_role("button", name="Delete product Browser match ball", exact=True).click()
        dialog.get_by_role("button", name="Delete", exact=True).click()
        expect(page.get_by_text("0 products", exact=True)).to_be_visible()
        page.get_by_role("button", name="Rename Football", exact=True).click()
        page.get_by_label("Rename category").fill("Fitness")
        page.get_by_role("button", name="Save category", exact=True).click()
        page.get_by_role("button", name="Delete category Fitness", exact=True).click()
        dialog.get_by_role("button", name="Delete", exact=True).click()
        expect(page.get_by_text("Create a category before adding your first product.")).to_be_visible()

    def test_about_contact_and_mobile_navigation(self):
        from playwright.sync_api import expect

        page = self.page
        page.goto(self.frontend_url + "/about")
        expect(page.get_by_role("heading", name="Why choose SportHub?")).to_be_visible()
        page.get_by_role("region", name="Client testimonials").get_by_role("button", name="Next slide").click()
        page.get_by_role("link", name="Contact us", exact=True).click()
        for label, value in [("Full name", "Guest Runner"), ("Email address", "guest@example.com"), ("Phone number", "9812345678"), ("Message", "Can you help me choose a ball?")]:
            page.get_by_label(label, exact=True).fill(value)
        page.get_by_role("button", name="Send message", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Your message has been sent.")
        page.set_viewport_size({"width": 390, "height": 844})
        self.assertFalse(page.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        page.get_by_role("button", name="Open navigation").click()
        page.get_by_role("navigation", name="Mobile navigation").get_by_role("link", name="Shop", exact=True).click()
        expect(page.get_by_role("heading", name="Shop sports gear", exact=True)).to_be_visible()

    def test_commerce_customer_checkout_and_order_history(self):
        from playwright.sync_api import expect

        page = self.page
        page.goto(self.frontend_url + f'/products/{self.ball_id}')
        page.get_by_role('button', name='Save to wishlist', exact=True).click()
        expect(page.get_by_role('heading', name='Welcome back', exact=True)).to_be_visible()
        page.get_by_label('Email address', exact=True).fill('runner@example.com')
        page.get_by_label('Password', exact=True).fill('Runner!Trail8426')
        page.get_by_role('button', name='Sign in', exact=True).click()
        expect(page.get_by_role('heading', name='Training ball', exact=True)).to_be_visible()
        page.get_by_role('button', name='Save to wishlist', exact=True).click()
        shopping = page.get_by_role('navigation', name='Shopping navigation')
        expect(shopping.get_by_role('link', name='Wishlist (1)', exact=True)).to_be_visible()
        shopping.get_by_role('link', name='Wishlist (1)', exact=True).click()
        page.get_by_label('Quantity for Training ball', exact=True).fill('2')
        page.get_by_role('button', name='Add to cart', exact=True).click()
        expect(page.get_by_text('Your wishlist is empty.', exact=False)).to_be_visible()
        expect(shopping.get_by_role('link', name='Cart (1)', exact=True)).to_be_visible()
        page.goto(self.frontend_url + f'/products/{self.boots_id}')
        page.get_by_role('button', name='Add to cart', exact=True).click()
        expect(shopping.get_by_role('link', name='Cart (2)', exact=True)).to_be_visible()
        shopping.get_by_role('link', name='Cart (2)', exact=True).click()
        expect(page.get_by_role('button', name='Checkout selected items')).to_be_disabled()
        ball = page.get_by_role('article').filter(has=page.get_by_role('link', name='Training ball', exact=True))
        ball.get_by_label('Quantity for Training ball', exact=True).fill('3')
        ball.get_by_role('button', name='Update', exact=True).click()
        expect(ball.get_by_text('Subtotal:', exact=False)).to_contain_text('269.88')
        ball.get_by_label('Quantity for Training ball', exact=True).fill('2')
        ball.get_by_role('button', name='Update', exact=True).click()
        expect(ball.get_by_text('Subtotal:', exact=False)).to_contain_text('179.92')
        page.get_by_role('checkbox', name='Select Training ball', exact=True).check()
        page.get_by_role('button', name='Checkout selected items').click()
        expect(page.get_by_role('heading', name='Checkout', exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_role('heading', name='Selected items', exact=True)).to_be_visible()
        expect(page.get_by_text('Training boots', exact=True)).to_have_count(0)
        for label, value in [('House or flat', '12'), ('Street', 'Sports Road'), ('City', 'Kathmandu'), ('Province or state', 'Bagmati'), ('Postal code', '44600')]:
            page.get_by_label(label, exact=True).fill(value)
        expect(page.get_by_label('Recipient name', exact=True)).to_have_value('Browser Runner')
        page.set_viewport_size({'width': 390, 'height': 844})
        self.assertFalse(page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / '.runtime/commerce-checkout-mobile.png'), full_page=True)
        page.get_by_role('button', name='Place order', exact=True).click()
        expect(page.get_by_role('heading', name='Order details', exact=True)).to_be_visible()
        expect(page.get_by_text('Payment: pending', exact=True)).to_be_visible()
        expect(page.get_by_text('Training ball', exact=True)).to_be_visible()
        expect(page.get_by_text('Training boots', exact=True)).to_have_count(0)
        page.reload()
        expect(page.get_by_role('heading', name='Order details', exact=True)).to_be_visible()
        expect(page.get_by_text('Payment: pending', exact=True)).to_be_visible()
        expect(page.get_by_text('Training ball', exact=True)).to_be_visible()
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / '.runtime/commerce-order-mobile.png'), full_page=True)
        shopping.get_by_role('link', name='Cart (1)', exact=True).click()
        expect(page.get_by_role('link', name='Training boots', exact=True)).to_be_visible()
        expect(page.get_by_role('link', name='Training ball', exact=True)).to_have_count(0)
        page.get_by_role('button', name='Clear cart', exact=True).click()
        page.get_by_role('alertdialog').get_by_role('button', name='Cancel', exact=True).click()
        expect(page.get_by_role('link', name='Training boots', exact=True)).to_be_visible()
        page.get_by_role('button', name='Remove', exact=True).click()
        page.get_by_role('alertdialog').get_by_role('button', name='Confirm', exact=True).click()
        expect(page.get_by_text('Your cart is empty.', exact=True)).to_be_visible()
        shopping.get_by_role('link', name='Your orders', exact=True).click()
        expect(page.get_by_text('Training ball', exact=True)).to_be_visible()

    def test_commerce_staff_workflows(self):
        from playwright.sync_api import expect

        page = self.page
        page.goto(self.frontend_url + '/admin')
        page.get_by_label('Staff username', exact=True).fill('BrowserCoach')
        page.get_by_label('Password', exact=True).fill('Staff!Browser8426')
        page.get_by_role('button', name='Sign in', exact=True).click()
        expect(page.get_by_role('heading', name='Staff workspace', exact=True)).to_be_visible()
        page.get_by_role('link', name='Manage orders', exact=True).click()
        page.get_by_label(f'Status for order {self.order_id}', exact=True).select_option('Dispatched')
        page.get_by_role('button', name='Save status', exact=True).click()
        expect(page.get_by_text('Fulfillment: Dispatched', exact=True)).to_be_visible()
        page.get_by_label(f'Status for order {self.order_id}', exact=True).select_option('completed')
        page.get_by_role('button', name='Save status', exact=True).click()
        expect(page.get_by_text('Payment: paid', exact=True)).to_be_visible()
        page.get_by_label('Filter by fulfillment', exact=True).select_option('pending')
        expect(page.get_by_text('No orders match this filter.', exact=True)).to_be_visible()
        page.goto(self.frontend_url + '/admin/accounts')
        for label, value in [('Staff username', 'newcoach'), ('Full name', 'New Coach'), ('Email address', 'newcoach@example.com'), ('Password', 'Summit!River8426'), ('Confirm password', 'Summit!River8426')]:
            page.get_by_label(label, exact=True).fill(value)
        page.get_by_role('button', name='Create staff account', exact=True).click()
        expect(page.get_by_text('Staff account created.', exact=True)).to_be_visible()
        page.get_by_role('button', name='Delete New Coach', exact=True).click()
        page.get_by_role('alertdialog').get_by_role('button', name='Confirm', exact=True).click()
        expect(page.get_by_role('heading', name='New Coach', exact=True)).to_have_count(0)
        page.goto(self.frontend_url + '/admin/messages')
        expect(page.get_by_text('Do you have training gear?', exact=True)).to_be_visible()
        page.get_by_role('button', name='Delete message from Guest Runner', exact=True).click()
        page.get_by_role('alertdialog').get_by_role('button', name='Confirm', exact=True).click()
        expect(page.get_by_text('No contact messages yet.', exact=True)).to_be_visible()
        page.goto(self.frontend_url + '/admin')
        expect(page.get_by_text('Completed order value', exact=True)).to_be_visible()
        page.screenshot(path=str(Path(__file__).resolve().parents[2] / '.runtime/commerce-dashboard-desktop.png'), full_page=True)
        page.get_by_role('link', name='Customers', exact=True).click()
        page.get_by_role('button', name='Delete Browser Runner', exact=True).click()
        page.get_by_role('alertdialog').get_by_role('button', name='Confirm', exact=True).click()
        expect(page.get_by_text('No accounts found.', exact=True)).to_be_visible()
        page.goto(self.frontend_url + '/admin/orders')
        expect(page.get_by_text('No orders match this filter.', exact=True)).to_be_visible()

    def open_khalti_checkout(self):
        from playwright.sync_api import expect

        page = self.page
        page.goto(self.frontend_url + f'/products/{self.ball_id}')
        page.get_by_role('button', name='Add to cart', exact=True).click()
        page.get_by_label('Email address', exact=True).fill('runner@example.com')
        page.get_by_label('Password', exact=True).fill('Runner!Trail8426')
        page.get_by_role('button', name='Sign in', exact=True).click()
        expect(page.get_by_role('heading', name='Training ball', exact=True)).to_be_visible()
        page.get_by_role('button', name='Add to cart', exact=True).click()
        page.get_by_role('navigation', name='Shopping navigation').get_by_role('link', name='Cart (1)', exact=True).click()
        page.get_by_role('checkbox', name='Select Training ball', exact=True).check()
        page.get_by_role('button', name='Checkout selected items').click()
        for label, value in [('House or flat', '12'), ('Street', 'Sports Road'), ('City', 'Kathmandu'), ('Province or state', 'Bagmati'), ('Postal code', '44600')]:
            page.get_by_label(label, exact=True).fill(value)
        expect(page.get_by_role('option', name='Khalti (sandbox)', exact=True)).to_be_enabled()
        page.get_by_label('Payment method', exact=True).select_option('khalti')

    @override_settings(KHALTI_SECRET_KEY='test-only-key', KHALTI_ENV='sandbox', FRONTEND_URL='http://127.0.0.1:5174')
    def test_commerce_khalti_return_login_pending_outage_and_receipt(self):
        from playwright.sync_api import expect
        from commerce.khalti import GatewayError
        from commerce.test_payments import initiated

        page = self.page
        # Only the external provider is substituted; React, Django and PostgreSQL are real.
        page.route('https://test-pay.khalti.com/**', lambda route: route.fulfill(content_type='text/html', body='<h1>Gateway contract test</h1>'))
        with patch('commerce.khalti.KhaltiClient.initiate', side_effect=initiated), patch('commerce.khalti.KhaltiClient.lookup') as lookup_mock:
            self.open_khalti_checkout()
            page.get_by_role('button', name='Pay with Khalti', exact=True).click()
            expect(page.get_by_role('heading', name='Gateway contract test')).to_be_visible()
            payment = self.context.request.get(self.frontend_url + '/api/payments/').json()['results'][0]
            lookup_mock.return_value = {'pidx': payment['pidx'], 'total_amount': payment['amount_paisa'], 'status': 'Pending', 'transaction_id': None, 'refunded': False}
            self.context.clear_cookies()
            page.goto(self.frontend_url + '/payment/return?' + urlencode({'attempt': payment['id'], 'pidx': payment['pidx'], 'status': 'Completed', 'amount': '1'}))
            expect(page.get_by_role('heading', name='Welcome back', exact=True)).to_be_visible()
            page.reload()
            page.get_by_label('Email address', exact=True).fill('runner@example.com')
            page.get_by_label('Password', exact=True).fill('Runner!Trail8426')
            page.get_by_role('button', name='Sign in', exact=True).click()
            expect(page.get_by_role('heading', name='Payment pending', exact=True)).to_be_visible()
            expect(page.get_by_role('link', name='Return to cart to retry')).to_have_count(0)
            lookup_mock.side_effect = GatewayError('connection_error')
            page.get_by_role('button', name='Check payment again').click()
            expect(page.get_by_role('alert')).to_contain_text('verification is unavailable')
            expect(page.get_by_role('link', name='Continue to Khalti')).to_have_count(0)
            lookup_mock.side_effect = None
            lookup_mock.return_value = {**lookup_mock.return_value, 'status': 'Completed', 'transaction_id': 'browser_txn_1'}
            page.get_by_role('button', name='Check payment again').click()
            expect(page.get_by_role('heading', name='Payment confirmed', exact=True)).to_be_visible()
            expect(page.get_by_text('Payment: paid', exact=True)).to_be_visible()
            expect(page.get_by_role('link', name='Cart (0)', exact=True)).to_be_visible()
            page.reload()
            expect(page.get_by_role('heading', name='Payment confirmed', exact=True)).to_be_visible()
            expect(page.get_by_text('Transaction: browser_txn_1', exact=True)).to_be_visible()
            page.set_viewport_size({'width': 390, 'height': 844})
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
            page.screenshot(path=str(Path(__file__).resolve().parents[2] / '.runtime/payment-receipt-mobile.png'), full_page=True)
            page.get_by_role('link', name='Your payments', exact=True).last.click()
            expect(page.get_by_role('heading', name='Your payments', exact=True)).to_be_visible()
            page.get_by_role('link', name='View payment', exact=True).click()
            expect(page.get_by_role('heading', name='Payment confirmed', exact=True)).to_be_visible()

    @override_settings(KHALTI_SECRET_KEY='test-only-key', KHALTI_ENV='sandbox', FRONTEND_URL='http://127.0.0.1:5174')
    def test_commerce_khalti_cancel_and_retry(self):
        from playwright.sync_api import expect
        from commerce.test_payments import initiated

        page = self.page
        page.route('https://test-pay.khalti.com/**', lambda route: route.fulfill(content_type='text/html', body='<h1>Gateway contract test</h1>'))
        with patch('commerce.khalti.KhaltiClient.initiate', side_effect=initiated), patch('commerce.khalti.KhaltiClient.lookup') as lookup_mock:
            self.open_khalti_checkout()
            page.get_by_role('button', name='Pay with Khalti', exact=True).click()
            expect(page.get_by_role('heading', name='Gateway contract test')).to_be_visible()
            payment = self.context.request.get(self.frontend_url + '/api/payments/').json()['results'][0]
            lookup_mock.return_value = {'pidx': payment['pidx'], 'total_amount': payment['amount_paisa'], 'status': 'User canceled', 'transaction_id': None, 'refunded': False}
            page.goto(self.frontend_url + '/payment/return?' + urlencode({'pidx': payment['pidx']}))
            expect(page.get_by_role('heading', name='Payment canceled', exact=True)).to_be_visible()
            page.get_by_role('link', name='Return to cart to retry', exact=True).click()
            expect(page.get_by_role('link', name='Training ball', exact=True)).to_be_visible()
            page.get_by_role('checkbox', name='Select Training ball', exact=True).check()
            page.get_by_role('button', name='Checkout selected items').click()
            for label, value in [('House or flat', '12'), ('Street', 'Sports Road'), ('City', 'Kathmandu'), ('Province or state', 'Bagmati'), ('Postal code', '44600')]:
                page.get_by_label(label, exact=True).fill(value)
            page.get_by_role('button', name='Place order', exact=True).click()
            expect(page.get_by_role('heading', name='Order details', exact=True)).to_be_visible()
            expect(page.get_by_text('Cash on delivery', exact=True)).to_be_visible()

    @override_settings(KHALTI_SECRET_KEY='test-only-key', KHALTI_ENV='sandbox', FRONTEND_URL='http://127.0.0.1:5174')
    def test_commerce_khalti_uncertain_attempt_recovery(self):
        from playwright.sync_api import expect
        from commerce.khalti import GatewayError

        page = self.page
        with patch('commerce.khalti.KhaltiClient.initiate', side_effect=GatewayError('connection_error')) as initiate_mock:
            self.open_khalti_checkout()
            page.get_by_role('button', name='Pay with Khalti', exact=True).click()
            expect(page.get_by_role('heading', name='Payment needs review', exact=True)).to_be_visible()
            expect(page.get_by_role('link', name='Continue to Khalti')).to_have_count(0)
            expect(page.get_by_role('link', name='Return to cart to retry')).to_have_count(0)
            page.set_viewport_size({'width': 390, 'height': 844})
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
            page.screenshot(path=str(Path(__file__).resolve().parents[2] / '.runtime/payment-review-mobile.png'), full_page=True)
            page.get_by_role('link', name='Cart (1)', exact=True).click()
            page.get_by_role('checkbox', name='Select Training ball', exact=True).check()
            page.get_by_role('button', name='Checkout selected items').click()
            for label, value in [('House or flat', '12'), ('Street', 'Sports Road'), ('City', 'Kathmandu'), ('Province or state', 'Bagmati'), ('Postal code', '44600')]:
                page.get_by_label(label, exact=True).fill(value)
            page.get_by_role('button', name='Place order', exact=True).click()
            expect(page.get_by_role('heading', name='Payment needs review', exact=True)).to_be_visible()
            initiate_mock.assert_called_once()
