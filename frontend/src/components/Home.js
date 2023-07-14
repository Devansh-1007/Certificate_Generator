import React from "react";
import Navbar from "./Navbar";
import Footer from "./Footer";
import HeroSection from "./HeroSection";

const Home = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <HeroSection />
      <section className="bg-gray-100 py-8 flex-grow">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold mb-6">Why Choose Us</h2>
          <div className="flex flex-wrap -mx-4">
            <div className="w-full md:w-1/2 lg:w-1/3 px-4 mb-4">
              <div className="bg-white rounded-lg shadow-lg p-6 h-full">
                <h3 className="text-xl font-semibold mb-2">
                  Easy-to-use Interface
                </h3>
                <p className="text-gray-700">
                  Our certificate generator features a user-friendly interface
                  that allows you to effortlessly create and customize
                  certificates.
                </p>
              </div>
            </div>
            <div className="w-full md:w-1/2 lg:w-1/3 px-4 mb-4">
              <div className="bg-white rounded-lg shadow-lg p-6 h-full">
                <h3 className="text-xl font-semibold mb-2">
                  Customization Options
                </h3>
                <p className="text-gray-700">
                  Customize your certificates with various design options,
                  including fonts, colors, backgrounds, and more.
                </p>
              </div>
            </div>
            <div className="w-full md:w-1/2 lg:w-1/3 px-4 mb-4">
              <div className="bg-white rounded-lg shadow-lg p-6 h-full">
                <h3 className="text-xl font-semibold mb-2">
                  Time-saving Templates
                </h3>
                <p className="text-gray-700">
                  Choose from a wide range of professionally-designed templates
                  that save you time and effort in creating certificates.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Home;
