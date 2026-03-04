import { createContext, useContext, useState } from "react";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [loginKey, setLoginKey] = useState(localStorage.getItem("key"));
  const [privacyLevel, setPrivacyLevel] = useState(localStorage.getItem("privacyLevel"));

  const login = (key, privacy) => {
    localStorage.setItem("key", key);
    localStorage.setItem("privacyLevel", privacy);
    setLoginKey(key);
    setPrivacyLevel(privacy);
  };

  const logout = () => {
    localStorage.clear();
    setLoginKey(null);
    setPrivacyLevel(null);
  };

  return (
    <AuthContext.Provider value={{ loginKey, privacyLevel, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}