// Signup page for FamilyBook (there's a link to the login page for existing users):
import React from "react";
import "./index.css";
// useInput -> custom hook to manage form inputs
// LabelInputField -> reusable input component
import { useInput, LabelInputField } from "./formfunctions.js";
// apiJson -> helper for API requests
import { apiJson } from "./global.js";
// useNavigate -> redirect users after signup
// useSearchParams -> allows us to read URL params
import { useNavigate, useSearchParams } from "react-router-dom"; 
// useAuth -> uses our custom auth system that stores our login state
import { useAuth } from "./authContext.js";

const SignupPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth(); // login() function to store auth data in localStorage

  // Form inputs:
  const { value: username, bind: bindUsername, reset: resetUsername } = useInput("");
  const { value: password, bind: bindPassword, reset: resetPassword } = useInput("");
  const { value: passwordConfirm, bind: bindPasswordConfirm, reset: resetPasswordConfirm } = useInput("");

  const [errorMessage, setErrorMessage] = React.useState(""); // Display validation/API errors.
  const [isLoading, setIsLoading] = React.useState(false); // Disable buttons and displays loading text.

  // Main logic for form submission:
  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent the page from reloading after form is submitted.
    setErrorMessage("");

    // Client-side validation for input fields:
    if (username.trim().length < 3) {
      setErrorMessage("Username must be at least 3 characters long.");
      return;
    }

    if (password.length < 6) {
      setErrorMessage("Password must be at least 6 characters long.");
      return;
    }

    if (password !== passwordConfirm) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    // Start loading: 
    setIsLoading(true);

    // Prepare the request to be sent to the backend:
    const content = {
      username: username.trim(),
      password: password,
      passwordConfirm: passwordConfirm,
    };

    // Call the backend (goes to POST /signup):
    try {
      const data = await apiJson("signup", {
        method: "POST",
        body: content,
      });

      // Auto-login after signup:
      login(data.key, data.privacyLevel);

      // Reset the form:
      resetUsername();
      resetPassword();
      resetPasswordConfirm();

      // Redirect to home or tree page:
      const redirectTo = searchParams.get("redirect") || "/";
      navigate(redirectTo, { replace: true });
      // Error handling:
    } catch (error) {
      console.error("Signup failed:", error);
      setErrorMessage(error.message || "Failed to create account. Please try again.");
      // Stop loading:
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="signup-page">
      <div className="form-style">
        <h1>Create Account</h1>
        <h2 className="section">Kischook Family History Database</h2>

        <div className="inner-wrap">
          <p>
            Join the Kischook family history database to view and share family documents.
            Create an account with a username and password to get started.
          </p>
        </div>

        <h2 className="section">Sign Up</h2>

        {errorMessage && (
          <div style={{ color: "red", marginBottom: "10px", padding: "10px", border: "1px solid red", borderRadius: "4px" }}>
            {errorMessage}
          </div>
        )}

        <form id="signup-form" onSubmit={handleSubmit}>
          <div className="inner-wrap">
            <LabelInputField
              binding={bindUsername}
              label={"Username (min 3 characters)"}
              id={"username-input"}
              type={"text"}
            />
            <LabelInputField
              binding={bindPassword}
              label={"Password (min 6 characters)"}
              id={"password-input"}
              type={"password"}
            />
            <LabelInputField
              binding={bindPasswordConfirm}
              label={"Confirm Password"}
              id={"password-confirm-input"}
              type={"password"}
            />
          </div>

          <input type="submit" value={isLoading ? "Creating Account..." : "Sign Up"} disabled={isLoading} />
        </form>

        <div className="inner-wrap" style={{ marginTop: "20px", textAlign: "center" }}>
          <p>
            Already have an account?{" "}
            <a href="/login" style={{ color: "blue", textDecoration: "underline", cursor: "pointer" }}>
              Log in here
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
