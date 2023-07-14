import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import Swal from "sweetalert2";
import Loader from "./Loader/Loader";
import Navbar from "./Navbar";
import Footer from "./Footer";

const GenerateID = () => {
  const [certificate, setCertificate] = useState("");
  const [certificateName, setCertificateName] = useState("");
  const [response, setResponse] = useState({});
  const [imageData, setImageData] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false); // Loading state
  const token = localStorage.getItem("token");
  const client_id = localStorage.getItem("clientID");
  const [loggedIn, setLoggedIn] = useState(
    token !== null && token !== undefined
  );
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      setLoggedIn(true);
    }
  }, []);

  const handleLogout = () => {
    // Clear the authentication token from localStorage
    localStorage.removeItem("token");
    localStorage.removeItem("clientID");
    setLoggedIn(false);
  };

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
  }, []);

  useEffect(() => {
    if (!loggedIn) {
      Swal.fire({
        icon: "info",
        title: "Please Log In",
        text: "You need to log in before proceeding.",
        showCancelButton: false,
        confirmButtonText: "OK",
      });

      navigate("/login"); // Change "/dashboard" to the desired page
    }
  }, [loggedIn, navigate]);

  const handleGenerateCertificate = () => {
    console.log(certificate);
    const url = "http://localhost:5000/generateCertificate";
    const data = {
      CERTIFICATE_NAME: certificateName,
    };
    const config = {
      headers: {
        "x-client-id": client_id,
        "x-token": token,
      },
    };

    setIsLoading(true); // Start loading

    // API call to generate ID for the logged-in client
    axios
      .post(url, data, config)
      .then((response) => {
        console.log(response.data);
        Swal.fire({
          icon: "success",
          title: response.data.status,
          text: response.data.description,
          showCancelButton: false,
          confirmButtonText: "Proceed",
        }).then((result) => {
          if (result.isConfirmed) {
            // Update the state in the next render cycle using a callback
            setCertificate(
              () => response.data.CERTIFICATE_DETAILS.CERTIFICATE_NAME
            );
            setResponse(() => response.data);
          }
        });
      })
      .catch((error) => {
        console.error(error);
        Swal.fire({
          icon: "error",
          title: "Error",
          text: "An error occurred while generating the certificate.",
          showCancelButton: "Cancel",
        });
      })
      .finally(() => {
        setIsLoading(false); // Stop loading
      });
  };

  const handleDownloadImage = () => {
    const url = "http://localhost:5000/getCertificate";
    const config = {
      headers: {
        "x-client-id": client_id,
        "x-token": token,
      },
      params: {
        CERTIFICATE_NAME: response.CERTIFICATE_DETAILS.CERTIFICATE_NAME,
        EXTENSION: "img",
      },
      responseType: "blob",
    };

    setIsLoading(true); // Start loading

    // API call to download the image
    axios
      .get(url, config)
      .then((response) => {
        console.log("Image download response:", response);
        const blob = new Blob([response.data], {
          type: response.headers["content-type"],
        });
        const imageUrl = URL.createObjectURL(blob);
        setImageUrl(() => imageUrl);
      })
      .catch((error) => {
        console.error("Image download error:", error);
      })
      .finally(() => {
        setIsLoading(false); // Stop loading
      });
  };

  const handleDownloadPDF = () => {
    const url = "http://localhost:5000/getCertificate";
    const config = {
      headers: {
        "x-client-id": client_id,
        "x-token": token,
      },
      params: {
        CERTIFICATE_NAME: response.CERTIFICATE_DETAILS.CERTIFICATE_NAME,
        EXTENSION: "pdf",
      },
      responseType: "arraybuffer",
    };

    setIsLoading(true); // Start loading

    // API call to download the PDF file
    axios
      .get(url, config)
      .then((response) => {
        console.log("PDF download response:", response);
        const pdfBlob = new Blob([response.data], { type: "application/pdf" });
        const pdfUrl = URL.createObjectURL(pdfBlob);
        window.open(pdfUrl);
      })
      .catch((error) => {
        console.error("PDF download error:", error);
      })
      .finally(() => {
        setIsLoading(false); // Stop loading
      });
  };

  const handleCertificateNameChange = (e) => {
    setCertificateName(e.target.value);
    setCertificate("");
    setResponse({});
    setImageData("");
    setImageUrl("");
  };

  const validateForm = () => {
    if (!certificateName) {
      Swal.fire({
        icon: "error",
        title: "Incomplete Form",
        text: "Please fill in all the fields.",
        confirmButtonText: "OK",
      });
    } else {
      handleGenerateCertificate();
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <div className="flex-grow container mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold mb-4">Generate Certificate</h2>
        <div className="mb-4">
          <label htmlFor="certificateName" className="mr-2">
            Certificate Name:
          </label>
          <input
            type="text"
            id="certificateName"
            className="border border-gray-300 p-2 rounded"
            value={certificateName}
            onChange={handleCertificateNameChange} // Handle ID name change
          />
        </div>
        <button
          onClick={validateForm}
          className="inline-block bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-700"
        >
          Generate
        </button>
        {response.CERTIFICATE_DETAILS && (
          <div className="mt-4">
            <h3 className="text-lg font-bold mb-2">Your Certificate:</h3>
            <pre className="border border-gray-300 p-4 bg-gray-100 rounded-md overflow-auto">
              <code>{JSON.stringify(response, null, 2)}</code>
            </pre>

            <div className="mt-4">
              <h3 className="text-lg font-bold mb-2">Download Options:</h3>
              <button
                onClick={handleDownloadImage}
                className="inline-block bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-700 mr-2"
              >
                Download as Image
              </button>
              <button
                onClick={handleDownloadPDF}
                className="inline-block bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-700"
              >
                Download as PDF
              </button>
            </div>
          </div>
        )}
        {isLoading ? (
          <div className="fixed inset-0 flex items-center justify-center z-50">
            <Loader />
          </div>
        ) : imageUrl ? (
          <div className="mt-4">
            <h3 className="text-lg font-bold mb-2">Downloaded Image:</h3>
            <img src={imageUrl} alt="Downloaded Certificate" />
            <h3 className="text-lg font-bold mb-2">{imageData}</h3>
          </div>
        ) : null}
      </div>

      <Footer />
    </div>
  );
};

export default GenerateID;
