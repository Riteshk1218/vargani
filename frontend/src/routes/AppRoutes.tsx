import { Navigate, Route, Routes } from 'react-router-dom'
import { AuditPage } from '../pages/audit/AuditPage'
import { MemberLoginPage } from '../pages/auth/MemberLoginPage'
import { MyContributionsPage } from '../pages/portal/MyContributionsPage'
import { ExpensesPage } from '../pages/expenses/ExpensesPage'
import { FinancialSummaryPage } from '../pages/finance/FinancialSummaryPage'
import { OtherIncomePage } from '../pages/income/OtherIncomePage'
import { ReportsPage } from '../pages/reports/ReportsPage'
import { REPORT_PERMISSIONS } from '../utils/permissions'
import { AppLayout } from '../layouts/AppLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { ForgotPasswordPage } from '../pages/auth/ForgotPasswordPage'
import { LoginPage } from '../pages/auth/LoginPage'
import { RegisterPage } from '../pages/auth/RegisterPage'
import { VerifyPage } from '../pages/auth/VerifyPage'
import { ApprovalsPage } from '../pages/approvals/ApprovalsPage'
import { CollectPage } from '../pages/collections/CollectPage'
import { CollectorsPage } from '../pages/collectors/CollectorsPage'
import { ContributionsPage } from '../pages/contributions/ContributionsPage'
import { DashboardPage } from '../pages/dashboard/DashboardPage'
import { EventDetailPage } from '../pages/events/EventDetailPage'
import { EventsPage } from '../pages/events/EventsPage'
import { AcceptInvitePage } from '../pages/invite/AcceptInvitePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { CreateOrganizationPage } from '../pages/onboarding/CreateOrganizationPage'
import { PaymentsPage } from '../pages/payments/PaymentsPage'
import { PlatformPage } from '../pages/platform/PlatformPage'
import { PeoplePage } from '../pages/people/PeoplePage'
import { PublicReceiptPage } from '../pages/receipts/PublicReceiptPage'
import { ReceiptPage } from '../pages/receipts/ReceiptPage'
import { ReceiptsPage } from '../pages/receipts/ReceiptsPage'
import { ProfilePage } from '../pages/settings/ProfilePage'
import { SettingsPage } from '../pages/settings/SettingsPage'
import { AdminStudioPage } from '../pages/studio/AdminStudioPage'
import { UsersPage } from '../pages/users/UsersPage'
import { RedirectIfAuthenticated, RequireAuth, RequireOrganization, RequirePermission } from './guards'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<RedirectIfAuthenticated />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/member-login" element={<MemberLoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>
      </Route>
      <Route element={<AuthLayout />}>
        <Route path="/invite/:token" element={<AcceptInvitePage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route element={<AuthLayout />}>
          <Route path="/onboarding/create-organization" element={<CreateOrganizationPage />} />
        </Route>
        <Route path="/platform" element={<PlatformPage />} />
        <Route element={<RequireOrganization />}>
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="my" element={<RequirePermission permission="portal.self"><MyContributionsPage /></RequirePermission>} />
            <Route path="collect" element={<RequirePermission permission="payments.create"><CollectPage /></RequirePermission>} />
            <Route path="contributions" element={<RequirePermission permission="contributions.view"><ContributionsPage /></RequirePermission>} />
            <Route path="payments" element={<RequirePermission permission="payments.view"><PaymentsPage /></RequirePermission>} />
            <Route path="receipts" element={<RequirePermission permission="receipts.view"><ReceiptsPage /></RequirePermission>} />
            <Route path="receipts/:id" element={<RequirePermission permission="receipts.view"><ReceiptPage /></RequirePermission>} />
            <Route path="collectors" element={<RequirePermission permission="collectors.manage"><CollectorsPage /></RequirePermission>} />
            <Route path="approvals" element={<RequirePermission permission="receipts.void_approve"><ApprovalsPage /></RequirePermission>} />
            <Route path="expenses" element={<RequirePermission permission="expenses.view"><ExpensesPage /></RequirePermission>} />
            <Route
              path="finance"
              element={<RequirePermission permission={['dashboard.view_financial', 'reports.view_financial']}><FinancialSummaryPage /></RequirePermission>}
            />
            <Route path="income" element={<RequirePermission permission="other_income.manage"><OtherIncomePage /></RequirePermission>} />
            <Route path="reports" element={<RequirePermission permission={REPORT_PERMISSIONS}><ReportsPage /></RequirePermission>} />
            <Route path="reports/:type" element={<RequirePermission permission={REPORT_PERMISSIONS}><ReportsPage /></RequirePermission>} />
            <Route path="audit" element={<RequirePermission permission="audit.view"><AuditPage /></RequirePermission>} />
            <Route path="events" element={<RequirePermission permission="events.view"><EventsPage /></RequirePermission>} />
            <Route path="events/:id" element={<RequirePermission permission="events.view"><EventDetailPage /></RequirePermission>} />
            <Route path="people" element={<RequirePermission permission="people.view"><PeoplePage /></RequirePermission>} />
            <Route path="users" element={<RequirePermission permission="members.view"><UsersPage /></RequirePermission>} />
            <Route path="settings" element={<RequirePermission permission="organization.manage"><SettingsPage /></RequirePermission>} />
            <Route path="studio" element={<RequirePermission permission="organization.manage"><AdminStudioPage /></RequirePermission>} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="/r/:token" element={<PublicReceiptPage />} />
      <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
