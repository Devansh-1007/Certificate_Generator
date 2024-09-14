import React, { useEffect, useState } from "react";
import axios from "axios";

const CertificateDesign = () => {
  const [designs, setDesigns] = useState([]);
  const [selectedDesign, setSelectedDesign] = useState(null);
  const token = localStorage.getItem("token");
  const client_id = localStorage.getItem("clientID");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    handleGetCertificateDesigns();
  }, []);

  useEffect(() => {
    console.log(selectedDesign);
    // Perform any actions with the selected design here
  }, [selectedDesign]);

  const handleGetCertificateDesigns = () => {
    const url = "http://localhost:5000/getCertificateDesigns";
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
        setDesigns(response.data.base64_data_list);
      })
      .catch((error) => {
        console.error("Failed to fetch certificate designs:", error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const handleDesignSelect = (design) => {
    setSelectedDesign(design);
    localStorage.setItem("certificate-design", design);
  };

  return (
    <div className="container mx-auto px-4">
      <h2 className="text-2xl font-bold mb-4 mt-8 text-center">
        Certificate Designs (Select One)
      </h2>
      {isLoading ? (
        <p>Loading...</p>
      ) : designs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {designs.map((design, index) => (
            <div
              key={index}
              className={`rounded overflow-hidden shadow-md cursor-pointer ${
                selectedDesign === design ? "border-4 border-blue-500" : ""
              }`}
              style={{ maxWidth: "300px" }}
              onClick={() => handleDesignSelect(design)}
            >
              <img
                src={`data:image/png;base64,${design}`}
                alt={`Design ${index + 1}`}
                className="w-full"
              />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

export default CertificateDesign;
