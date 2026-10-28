import { Navigate } from "react-router";

export default function AuthIndex() {
  return <Navigate to="/auth/login" replace />;
}
