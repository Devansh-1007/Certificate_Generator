import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Swal from "sweetalert2";
import Navbar from "./Navbar";
import Footer from "./Footer";
import axios from "axios";
import Loader from "./Loader/Loader";
import CertificateDesign from "./CertificateDesign";

const Dashboard = () => {
  const token = localStorage.getItem("token");
  const client_id = localStorage.getItem("clientID");
  const [loggedIn] = useState(token !== null && token !== undefined);
  const [certData, setCertData] = useState([]);
  const [idData, setIdData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!loggedIn) {
      Swal.fire({
        icon: "info",
        title: "Please Log In",
        text: "You need to log in before proceeding.",
        showCancelButton: false,
        confirmButtonText: "OK",
      });
      navigate("/login");
    }
  }, [loggedIn, navigate]);

  const handleGetAllcertificate = () => {
    const url = "http://localhost:5000/getAllCertificate";
    const config = {
      headers: {
        "x-client-id": client_id,
        "x-token": token,
      },
    };

    setIsLoading(true);
    axios
      .get(url, config)
      .then((response) => {
        // console.log("Base64 data:", response.data.base64_data_list);
        setCertData(response.data.base64_data_list);
      })
      .catch((error) => {
        console.error("Image download error:", error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };
  const handleGetAllid = () => {
    const url = "http://localhost:5000/getAllId";
    const config = {
      headers: {
        "x-client-id": client_id,
        "x-token": token,
      },
    };

    setIsLoading(true);
    axios
      .get(url, config)
      .then((response) => {
        // console.log("Base64 data:", response.data.base64_data_list);
        setIdData(response.data.base64_data_list);
      })
      .catch((error) => {
        console.error("Image download error:", error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <div className="container mx-auto px-4 py-8 flex-grow">
        <h1 className="text-3xl font-bold mb-16 text-center">
          Welcome to the Dashboard
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/generate-id"
            className="inline-block bg-blue-500 text-white py-2 px-4 m-auto rounded hover:bg-blue-700"
          >
            Generate ID
          </Link>
          <Link
            to="/generate-certificate"
            className="inline-block bg-blue-500 text-white py-2 px-4 m-auto rounded hover:bg-blue-700"
          >
            Generate Certificate
          </Link>
          <button
            onClick={handleGetAllid}
            className="inline-block bg-blue-500 text-white py-2 px-4 m-auto rounded hover:bg-blue-700"
          >
            Get Previously Generated Ids
          </button>
          <button
            onClick={handleGetAllcertificate}
            className="inline-block bg-blue-500 text-white py-2 px-4 m-auto rounded hover:bg-blue-700"
          >
            Get Previously Generated certificates
          </button>
        </div>

        <CertificateDesign />

        {/* ALL CRTIFICATES */}
        {isLoading ? (
          <div className="mt-8">
            <Loader />
          </div>
        ) : certData.length > 0 ? (
          <div className="mt-8">
            <h2 className="text-xl font-bold mb-4">
              Previously Generated Items:
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {certData.map((base64Data, index) => (
                <img
                  key={index}
                  src={`data:image/png;base64,${base64Data}`}
                  alt="Generated Item"
                  className="max-w-xs"
                />
              ))}
            </div>
          </div>
        ) : null}
        {/* ALL ID */}
        {isLoading ? (
          <div className="mt-8">
            <Loader />
          </div>
        ) : idData.length > 0 ? (
          <div className="mt-8">
            <h2 className="text-xl font-bold mb-4">
              Previously Generated Items:
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {idData.map((base64Data, index) => (
                <img
                  key={index}
                  src={`data:image/png;base64,${base64Data}`}
                  alt="Generated Item"
                  className="max-w-xs"
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
      <Footer />
    </div>
  );
};

export default Dashboard;
