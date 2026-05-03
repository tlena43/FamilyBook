import React, { useState, useEffect, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { apiFetch } from "./global.js";
import { faBars } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { AuthProvider, useAuth } from "./authContext.js";

const LoginPage = lazy(() => import("./login"));
const SignupPage = lazy(() => import("./signup"));
const PersonForm = lazy(() => import("./personform"));
const ContentForm = lazy(() => import("./contentform"));
const DisplayContent = lazy(() => import("./displaycontent"));
const DisplayPeople = lazy(() => import("./displaypeople"));
const IndividualPerson = lazy(() => import("./individualperson"));
const IndividualContent = lazy(() => import("./individualcontent"));
//const FamilyTree = lazy(() => import("./familytree"))
const FamilyTree = lazy(() => import("./flow"));

// start navigation functions
function NavItem({ menuOpen, closeMenu }) {
  const items = [
    { name: "Add Person", key: 1, route: "person/new" },
    { name: "People", key: 2, route: "person" },
    { name: "Add Content", key: 3, route: "content/new" },
    { name: "View Content", key: 4, route: "content" },
    { name: "Family Tree", key: 5, route: "tree" },
    { name: "Log out", key: 6, route: "logout" },
  ];

  const navItems = items.map((item) => (
    <Link to={"/" + item.route} className="nav-item" key={item.key} onClick={closeMenu}>
      {item.name}
    </Link>
  ));

  return (
    <div id="nav-list-style" className={menuOpen ? "mobile-nav" : ""}>
      <div id="nav-items">{navItems}</div>
      <div className="greyed-out" onClick={closeMenu}></div>
    </div>
  );
}

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  function toggleMenu() {
    setMenuOpen((prev) => !prev);
  }

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <div id="head-wrapper">
      <div id="head">
        <h1 id="header-title-container">Kischook Family</h1>
        <FontAwesomeIcon icon={faBars} onClick={toggleMenu} />
        <NavItem menuOpen={menuOpen} closeMenu={closeMenu} />
      </div>
    </div>
  );
}
// end navigation functions

// start sitewide building
function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

// Logs out and redirects
function LogOut() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  return null;
}

function PageState() {
  const { loginKey } = useAuth();

  if (loginKey == null) {
    return (
      <Suspense fallback={<div>Loading...</div>}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </Suspense>
    );
  }

  return (
    <div>
      <Header />
      <div id="page-body">
        <Suspense fallback={<div>Loading...</div>}>
          <Routes>
            <Route path="/person/new" element={<PersonForm />} />
            <Route path="/person" element={<DisplayPeople admin={true} />} />
            <Route path="/person/edit/:id" element={<PersonForm />} />
            <Route path="/person/:id" element={<IndividualPerson admin={true} />} />
            <Route path="/content/new" element={<ContentForm />} />
            <Route path="/content/edit/:id" element={<ContentForm />} />
            <Route path="/content" element={<DisplayContent />} />
            <Route path="/tree" element={<FamilyTree />} />
            <Route path="/" element={<DisplayContent />} />
            <Route path="/content/:id" element={<IndividualContent admin={true} />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/logout" element={<LogOut />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}

function NotFound() {
  return (
    <div>
      <h1>404</h1>
      <h1>The page you were looking for doesn't exist</h1>
    </div>
  );
}

function LoginCheck() {
  const { loginKey, logout } = useAuth();

  useEffect(() => {
    if (loginKey == null) return;

    let cancelled = false;

    (async () => {
      try {
        await apiFetch("loginCheck", { loginKey, method: "GET" });
      } catch (e) {
        if (!cancelled) logout();
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [loginKey, logout]);

  return null;
}

function Main() {
  return (
    <div id="main-page">
      <Router>
        <ScrollToTop />
        <LoginCheck />
        <PageState />
      </Router>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <Main />
    </AuthProvider>
  </React.StrictMode>
);