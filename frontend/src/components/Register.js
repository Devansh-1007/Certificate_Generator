import React, { useState } from "react";
import axios from "axios";
import Swal from "sweetalert2";
import Navbar from "./Navbar";
import Footer from "./Footer";

const Register = () => {
  const [client_id, setClientId] = useState("");
  const [client_name, setClientName] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");

  const handleRegister = () => {
    
    const url = "http://localhost:5000/registerClient";

    const data = {
      CLIENT_ID: client_id,
      CLIENT_NAME: client_name,
      PASSWORD: password,
    };

    const config = {
      headers: {
        "Content-Type": "application/json",
        "x-token": token,
      },
    };

    axios
      .post(url, data, config)
      .then((response) => {
        console.log(response.data);
        Swal.fire({
          icon: "success",
          title: "Registration Successful",
          text: "Proceed to login",
          showCancelButton: false,
          confirmButtonText: "Proceed",
        }).then((result) => {
          if (result.isConfirmed) {
            window.location.href = "/login";
          }
        });
      })
      .catch((error) => {
        console.error(error);
        Swal.fire({
          icon: "error",
          title: "Admin access not verified",
          text: "Please try again later.",
          confirmButtonText: "OK",
        });
      });
  };

  const validateForm = () => {
    if (!client_id || !client_name || !password || !token) {
      Swal.fire({
        icon: "error",
        title: "Incomplete Form",
        text: "Please fill in all the fields.",
        confirmButtonText: "OK",
      });
    } else {
      handleRegister();
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <Navbar />
      <div className="flex flex-col items-center justify-center flex-grow">
        <div className="max-w-sm w-full p-6 bg-white rounded shadow">
          <h2 className="mb-6 text-2xl font-bold text-center text-gray-800">
            Client Registration
          </h2>
          <div className="mb-4">
            <label className="block mb-2 text-sm font-bold text-gray-800">
              Client ID
            </label>
            <input
              type="text"
              placeholder="Client ID"
              value={client_id}
              onChange={(e) => setClientId(e.target.value)}
              className="input"
            />
          </div>
          <div className="mb-4">
            <label className="block mb-2 text-sm font-bold text-gray-800">
              Client Name
            </label>
            <input
              type="text"
              placeholder="Client Name"
              value={client_name}
              onChange={(e) => setClientName(e.target.value)}
              className="input"
            />
          </div>
          <div className="mb-4">
            <label className="block mb-2 text-sm font-bold text-gray-800">
              Password
            </label>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
            />
          </div>
          <div className="mb-4">
            <label className="block mb-2 text-sm font-bold text-gray-800">
              Token
            </label>
            <input
              type="text"
              placeholder="Token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="input"
              onKeyPress={(event) => {
                if (event.key === "Enter") {
                  handleRegister();
                }
              }}
            />
          </div>
          <button
            onClick={validateForm}
            className="btn bg-blue-500 text-white hover:bg-blue-600 mt-4 mx-auto  rounded-xl px-16 py-2  "
          >
            Register
          </button>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Register;
