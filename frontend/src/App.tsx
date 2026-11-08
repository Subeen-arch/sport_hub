import { Link, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/AppLayout'
import { Button } from '@/components/ui/button'
import { AuthPage } from '@/features/auth/AuthPage'
import { AccountPage } from '@/features/auth/AccountPage'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { StaffPage } from '@/features/auth/StaffPage'
import { useAuth } from '@/features/auth/auth-context'
import { HomePage } from '@/features/catalog/HomePage'
import { ShopPage } from '@/features/catalog/ShopPage'
import { ProductPage } from '@/features/catalog/ProductPage'
import { CatalogAdminPage } from '@/features/catalog/CatalogAdminPage'
import { AboutPage } from '@/features/content/AboutPage'
import { ContactPage } from '@/features/content/ContactPage'
import { CommerceProvider } from '@/features/commerce/CommerceProvider'
import { CartPage } from '@/features/commerce/CartPage'
import { WishlistPage } from '@/features/commerce/WishlistPage'
import { CheckoutPage } from '@/features/commerce/CheckoutPage'
import { OrdersPage, OrderPage } from '@/features/commerce/OrdersPage'
import { PaymentsPage, PaymentPage } from '@/features/commerce/PaymentsPage'
import { StaffOrdersPage } from '@/features/staff/StaffOrdersPage'
import { StaffPeoplePage } from '@/features/staff/StaffPeoplePage'
import { StaffMessagesPage } from '@/features/staff/StaffMessagesPage'

export default function App() {
  const { loading, error, retry } = useAuth()
  if (loading) return <main className="grid min-h-screen place-items-center"><p role="status">Loading SportHub…</p></main>
  if (error) return <main className="mx-auto mt-20 max-w-lg space-y-5 p-6"><h1 className="page-title">Unable to connect</h1><p role="alert">{error}</p><Button onClick={retry}>Try again</Button></main>
  return <CommerceProvider><Routes>
    <Route element={<AppLayout />}>
      <Route index element={<HomePage />} />
      <Route path="shop" element={<ShopPage />} />
      <Route path="search" element={<ShopPage search />} />
      <Route path="categories/:slug" element={<ShopPage />} />
      <Route path="products/:id" element={<ProductPage />} />
      <Route path="about" element={<AboutPage />} />
      <Route path="contact" element={<ContactPage />} />
      <Route path="login" element={<AuthPage key="login" mode="login" />} />
      <Route path="register" element={<AuthPage key="register" mode="register" />} />
      <Route path="admin/login" element={<AuthPage key="staff" mode="staff" />} />
      <Route element={<RequireAuth />}><Route path="account" element={<AccountPage />} /><Route path="cart" element={<CartPage />} /><Route path="wishlist" element={<WishlistPage />} /><Route path="checkout" element={<CheckoutPage />} /><Route path="orders" element={<OrdersPage />} /><Route path="orders/:id" element={<OrderPage />} /></Route>
      <Route element={<RequireAuth />}><Route path="payments" element={<PaymentsPage />} /><Route path="payments/:id" element={<PaymentPage />} /><Route path="payment/return" element={<PaymentPage returning />} /></Route>
      <Route element={<RequireAuth staff />}><Route path="admin" element={<StaffPage />} /><Route path="admin/catalog" element={<CatalogAdminPage />} /><Route path="admin/orders" element={<StaffOrdersPage />} /><Route path="admin/users" element={<StaffPeoplePage key="customers" />} /><Route path="admin/accounts" element={<StaffPeoplePage key="staff" staff />} /><Route path="admin/messages" element={<StaffMessagesPage />} /></Route>
      <Route path="*" element={<section className="page-panel space-y-4"><h1 className="page-title">Page not found</h1><p>We couldn’t find the page you requested.</p><Button asChild><Link to="/">Back to home</Link></Button></section>} />
    </Route>
  </Routes></CommerceProvider>
}
