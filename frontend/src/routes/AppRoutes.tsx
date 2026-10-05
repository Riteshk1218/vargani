import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { AuthLayout } from '../layouts/AuthLayout'
import { ForgotPasswordPage } from '../pages/auth/ForgotPasswordPage'
import { LoginPage } from '../pages/auth/LoginPage'
import { RegisterPage } from '../pages/auth/RegisterPage'
import { VerifyPage } from '../pages/auth/VerifyPage'
import { DashboardPage } from '../pages/dashboard/DashboardPage'
import { EventDetailPage } from '../pages/events/EventDetailPage'
import { EventsPage } from '../pages/events/EventsPage'
import { AcceptInvitePage } from '../pages/invite/AcceptInvitePage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { CreateOrganizationPage } from '../pages/onboarding/CreateOrganizationPage'
import { PeoplePage } from '../pages/people/PeoplePage'
import { ProfilePage } from '../pages/settings/ProfilePage'
import { SettingsPage } from '../pages/settings/SettingsPage'
import { UsersPage } from '../pages/users/UsersPage'
import { RedirectIfAuthenticated, RequireAuth, RequireOrganization, RequirePermission } from './guards'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<RedirectIfAuthenticated />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
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
        <Route element={<RequireOrganization />}>
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="events" element={<RequirePermission permission="events.view"><EventsPage /></RequirePermission>} />
            <Route path="events/:id" element={<RequirePermission permission="events.view"><EventDetailPage /></RequirePermission>} />
            <Route path="people" element={<RequirePermission permission="people.view"><PeoplePage /></RequirePermission>} />
            <Route path="users" element={<RequirePermission permission="members.view"><UsersPage /></RequirePermission>} />
            <Route path="settings" element={<RequirePermission permission="organization.manage"><SettingsPage /></RequirePermission>} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
