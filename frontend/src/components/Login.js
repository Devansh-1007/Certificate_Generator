import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import Swal from "sweetalert2";
import Navbar from "./Navbar";
import Footer from "./Footer";

const Login = () => {
  const [clientID, setClientID] = useState("");
  const [clientName, setClientName] = useState("");
  const [password, setPassword] = useState("");
  const token = localStorage.getItem("token");
  const [loggedIn, setLoggedIn] = useState(
    token !== null && token !== undefined
  );
  const navigate = useNavigate();

  const handleLogin = () => {
    if (!clientID || !clientName || !password) {
      Swal.fire({
        icon: "error",
        title: "Validation Error",
        text: "Please enter all details.",
      });
      return;
    }

    axios
      .post("http://localhost:5000/loginClient", {
        CLIENT_ID: clientID,
        CLIENT_NAME: clientName,
        PASSWORD: password,
      })
      .then((response) => {
        console.log(response.data);
        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("clientID", clientID);
        setLoggedIn(true);
        Swal.fire({
          icon: "success",
          title: response.data.status,
          text: response.data.description,
          showCancelButton: false,
          confirmButtonText: "Proceed",
        }).then((result) => {
          if (result.isConfirmed) {
            navigate("/dashboard");
          }
        });
      })
      .catch((error) => {
        console.error(error);
        Swal.fire({
          icon: "error",
          title: "Login Failed",
          text: "Please try again.",
        });
      });
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    const storedClientID = localStorage.getItem("clientID");
    if (token && storedClientID) {
      Swal.fire({
        icon: "info",
        title: "Already Logged In",
        text: "Redirected to dashboard.",
        showCancelButton: false,
        confirmButtonText: "OK",
      });
      setLoggedIn(true);
      setClientID(storedClientID);
    }
  }, []);

  useEffect(() => {
    if (loggedIn) {
      navigate("/dashboard");
    }
  }, [loggedIn, navigate]);

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Navbar />
      <div className="flex-grow flex items-center justify-center">
        {loggedIn ? (
          <Link to="/dashboard" />
        ) : (
          <div className="max-w-md w-full mx-auto px-6 py-8 bg-white rounded-lg shadow-md">
            <h2 className="text-2xl font-bold text-gray-800 mb-8 text-center">
              Client Login
            </h2>
            <div className="mb-4">
              <input
                type="text"
                placeholder="Client ID"
                value={clientID}
                onChange={(e) => setClientID(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="mb-4">
              <input
                type="text"
                placeholder="Client Name"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="mb-6">
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button
              onClick={handleLogin}
              className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-700"
            >
              Login
            </button>
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
};

export default Login;
