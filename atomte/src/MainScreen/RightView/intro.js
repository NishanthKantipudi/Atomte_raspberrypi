import React, { useState, useEffect } from 'react';
import './rightview.css';
import { WifiOff } from "lucide-react";

const WelcomeMessage = () => {
  const messages = [
    "Welcome to our service!",
    "Thank you for choosing us.",
    "We're here to make your life easier.",
    "Experience seamless automation.",
    "Your satisfaction is our priority.",
    "Simplifying your tasks, one click at a time.",
    "Empowering you with technology.",
    "Where efficiency meets excellence.",
    "Automation made simple.",
    "Transforming ideas into reality.",
    "Your partner in innovation.",
    "Leading the way in automated solutions.",
    "Pioneering the future of convenience.",
    "Crafting intelligent solutions for you.",
    "Reliability at its best.",
    "Innovating the everyday.",
    "Where your needs meet our expertise.",
    "Taking the hassle out of your tasks.",
    "Excellence in every interaction.",
    "Redefining service standards."
  ];

  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [isOffline, setIsOffline] = useState(false);

  const checkInternetConnection = async () => {
    if (!navigator.onLine) {
      setIsOffline(true);
      return;
    }
  
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000); // 3-second timeout
  
      await fetch("https://www.gstatic.com/generate_204", {
        method: "GET",
        mode: "no-cors",
        signal: controller.signal
      });
  
      clearTimeout(timeout);
      setIsOffline(false); // Internet is active
    } catch (error) {
      // Retry after 1 second to avoid false positives
      setTimeout(async () => {
        try {
          await fetch("https://www.gstatic.com/generate_204", { method: "GET", mode: "no-cors" });
          setIsOffline(false);
        } catch (err) {
          setIsOffline(true);
        }
      }, 1000);
    }
  };

  useEffect(() => {
    // Message rotation interval
    const messageInterval = setInterval(() => {
      setCurrentMessageIndex((prevIndex) => (prevIndex + 1) % messages.length);
    }, 60000); // Change message every minute (60000 ms)
    
    // Internet connection check
    checkInternetConnection();
    const connectionInterval = setInterval(checkInternetConnection, 3000);
    
    return () => {
      clearInterval(messageInterval);
      clearInterval(connectionInterval);
    };
  }, []);

  if (isOffline) {
    return (
      <div className="container">
        <h1 className="title">Connection Error</h1>
        <p className="message">
          <WifiOff size={70} /> No Internet Connection
        </p>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="guide-steps">
        <div className="guide-step">
          <div className="step-number">1</div>
          <div className="step-content">
            <h3>Scan QR Code</h3>
            <p>Scan the QR code located at the top-left of the screen.</p>

          </div>
        </div>

        <div className="guide-step">
          <div className="step-number">2</div>
          <div className="step-content">
            <h3>Upload Files</h3>
            <p>Select and upload the files you want to print.</p>
          </div>
        </div>

        <div className="guide-step">
          <div className="step-number">3</div>
          <div className="step-content">
            <h3>Make Payment</h3>
            <p>Choose a payment method and Complete the payment securely.</p>
          </div>
        </div>

        <div className="guide-step">
          <div className="step-number">4</div>
          <div className="step-content">
            <h3>Collect Prints</h3>
            <p>Collect your printed documents from the printer.</p>
          </div>
        </div>
      </div>
      <p className="thank-you">Thank you for using our service!</p>
    </div>

  );
};

export default WelcomeMessage;