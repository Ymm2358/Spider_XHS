import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import Accounts from "./pages/Accounts";
import Collect from "./pages/Collect";
import Drafts from "./pages/Drafts";
import Library from "./pages/Library";
import Overview from "./pages/Overview";
import Publish from "./pages/Publish";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="collect" element={<Collect />} />
        <Route path="library" element={<Library />} />
        <Route path="drafts" element={<Drafts />} />
        <Route path="publish" element={<Publish />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
