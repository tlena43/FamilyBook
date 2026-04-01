import React from "react";
import "./index.css";
import { useInput, LabelInputField } from "./formfunctions.js";
import { apiJson } from "./global.js";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./authContext.js"; 

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth(); 

  const { value: username, bind: bindUsername, reset: resetUsername } = useInput("");
  const { value: password, bind: bindPassword, reset: resetPassword } = useInput("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    const content = {
      username: username.trim(),
      password: password,
    };

    try {
      const data = await apiJson("login", {
        method: "POST",
        body: content,
      });

      login(data.key, data.privacyLevel);

      resetUsername();
      resetPassword();

      navigate("/", { replace: true });
    } catch (error) {
      console.error("Login failed:", error);
      alert("Failed to log in\nPlease review your login details and try again");
    }
  };

  return (
    <div id="login-page">
      <div className="form-style">
        <h1>Welcome</h1>
        <h2 className="section">Kischook Family History Database</h2>

        <div className="inner-wrap">
          <p>
            This is a private collection of Kischook family history documents focused on the children,
            grandchildren, and extended family of Alexandria Kischook. All members of the Kischook family
            are welcome to view and share documents.
          </p>
        </div>

        <h2 className="section">Login</h2>

        <form id="login-form" onSubmit={handleSubmit}>
          <div className="inner-wrap">
            <LabelInputField binding={bindUsername} label={"Username"} id={"username-input"} type={"text"} />
            <LabelInputField binding={bindPassword} label={"Password"} id={"password-input"} type={"password"} />
          </div>

          <input type="submit" value="Submit" />
        </form>

        <div className="inner-wrap" style={{ marginTop: "20px", textAlign: "center" }}>
          <p>
            Don't have an account?{" "}
            <a href="/signup" style={{ color: "blue", textDecoration: "underline", cursor: "pointer" }}>
              Sign up here
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;