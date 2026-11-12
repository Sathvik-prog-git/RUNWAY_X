import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar.jsx";
import Topbar from "./Topbar.jsx";

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-app-bg">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto px-5 py-5 lg:px-8">
        <Topbar />
        <div className="mt-6"><Outlet /></div>
      </main>
    </div>
  );
}
