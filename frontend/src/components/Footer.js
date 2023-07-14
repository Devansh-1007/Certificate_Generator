import React from "react";

const Footer = () => {
  return (
    <footer className="bg-gray-200">
      <div className="container mx-auto py-8 px-4">
        <div className="flex flex-col md:flex-row md:justify-between">
          <div className="mb-4 md:mb-0">
            <h2 className="text-lg font-semibold mb-2">
              Certificate Generator
            </h2>
            <p className="text-gray-600">
              Create and manage certificates with ease.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-2">Contact</h3>
            <p className="text-gray-600">
              Email: choudhary.devansh1007@gmail.com
            </p>
            <p className="text-gray-600">Phone: +91 8318638999</p>
          </div>
        </div>
        <hr className="my-6 border-gray-300" />
        <p className="text-center text-gray-600">
          &copy; 2023 Certificate Generator. All rights reserved.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
