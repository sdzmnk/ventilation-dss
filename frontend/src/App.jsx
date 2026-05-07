import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./api/auth.jsx";
import AppLayout from "./components/AppLayout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import SensorsPage from "./pages/SensorsPage.jsx";
import OptimizationPage from "./pages/OptimizationPage.jsx";
import ConfigPage from "./pages/ConfigPage.jsx";
import UsersPage from "./pages/UsersPage.jsx";
import RolesPage from "./pages/RolesPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import ChatPage from "./pages/ChatPage.jsx";

function Protected({ children, role }) {
  const { user, ready } = useAuth();
  if (!ready) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return <AppLayout>{children}</AppLayout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<Protected><DashboardPage /></Protected>} />
      <Route path="/sensors" element={<Protected><SensorsPage /></Protected>} />
      <Route path="/optimization" element={<Protected><OptimizationPage /></Protected>} />
      <Route path="/config" element={<Protected><ConfigPage /></Protected>} />
      <Route path="/users" element={<Protected role="admin"><UsersPage /></Protected>} />
      <Route path="/roles" element={<Protected role="admin"><RolesPage /></Protected>} />
      <Route path="/profile" element={<Protected><ProfilePage /></Protected>} />
      <Route path="/chat" element={<Protected><ChatPage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
