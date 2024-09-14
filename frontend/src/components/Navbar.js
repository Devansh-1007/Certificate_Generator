import React, { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import Swal from "sweetalert2";

const Navbar = () => {
  const token = localStorage.getItem("token");
  const [loggedIn, setLoggedIn] = useState(
    token !== null && token !== undefined
  );
  const navigate = useNavigate();

  const handleLogout = useCallback(() => {
    // Clear the authentication token from localStorage
    localStorage.removeItem("token");
    localStorage.removeItem("clientID");
    setLoggedIn(false);
    navigate("/");
  }, [navigate]);

  // Check if the client is already logged in
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      setLoggedIn(true);
    }
  }, []);

  useEffect(() => {
    let logoutTimer;

    const resetLogoutTimer = () => {
      clearTimeout(logoutTimer);
      logoutTimer = setTimeout(() => {
        handleLogout();
        Swal.fire({
          icon: "info",
          title: "Logged Out",
          text: "You have been automatically logged out due to inactivity.",
        });
      }, 30 * 60 * 1000); // 30 minutes (30 minutes * 60 seconds * 1000 milliseconds)
    };

    const handleActivity = () => {
      resetLogoutTimer();
    };

    window.addEventListener("mousemove", handleActivity);
    window.addEventListener("keydown", handleActivity);

    resetLogoutTimer();

    return () => {
      clearTimeout(logoutTimer);
      window.removeEventListener("mousemove", handleActivity);
      window.removeEventListener("keydown", handleActivity);
    };
  }, [handleLogout]);

  return (
    <nav className="bg-blue-500">
      <div className="container mx-auto px-4 py-2">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-white text-3xl font-bold">
            Certificate Generator
          </Link>
          <div className="space-x-4">
            {loggedIn ? (
              <Link
                to="/dashboard"
                className="text-white rounded-md  px-3 py-1 hover:bg-white hover:text-blue-500 font-medium"
              >
                Dashboard
              </Link>
            ) : (
              <Link
                to="/login"
                className="text-white rounded-md  px-3 py-1 hover:bg-white hover:text-blue-500 font-medium"
              >
                Login as Client
              </Link>
            )}

            <Link
              to="/"
              className="inline-block bg-gray-500 text-white  px-3 py-1 rounded-md hover:bg-gray-700 font-medium"
            >
              Go to Home
            </Link>
            <Link
              to="/register"
              className="inline-block text-white rounded-md  px-3 py-1 hover:bg-white hover:text-blue-500 font-medium"
            >
              Register new Client as Admin
            </Link>
            {loggedIn && (
              <button
                onClick={handleLogout}
                className="inline-block bg-red-500 text-white px-3 py-1 rounded-md  hover:bg-red-700 font-medium"
              >
                Logout
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
