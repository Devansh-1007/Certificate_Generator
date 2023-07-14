import React from "react";
import { Link } from "react-router-dom";

const HeroSection = () => {
  return (
    <section className="bg-blue-500 text-white py-12 flex-grow">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            Welcome to the Certificate Generator
          </h1>
          <p className="text-lg md:text-xl mb-6">
            Create and customize stunning certificates in minutes.
          </p>

          <Link
            to="/login"
            className="inline-block bg-white text-blue-500 py-3 px-6 rounded-lg hover:bg-blue-100 transition-colors duration-300"
          >
            Get Started
          </Link>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
