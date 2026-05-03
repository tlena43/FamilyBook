import { createContext, useContext, useState } from "react";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [loginKey, setLoginKey] = useState(localStorage.getItem("key"));

  const login = (key) => {
    localStorage.setItem("key", key);
    setLoginKey(key);
  };

  const logout = () => {
    localStorage.clear();
    setLoginKey(null);
  };

  return (
    <AuthContext.Provider value={{ loginKey, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}