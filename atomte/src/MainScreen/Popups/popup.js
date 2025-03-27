import React, { useState, useEffect } from "react";
import app from "../../firebase/firebase";
import { getDatabase, ref, onValue } from "firebase/database";
import "./popup.css";
import VideoPlayer from "../RightView/rightcenterview";
import ad1 from "../ads/ad1.mp4"; //testing

const PrinterErrorPopup = ({ code }) => {
  const [error, setError] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [errVideo, setErrVideo] = useState("");
  const db = getDatabase(app);

  const checkInternetConnection = async () => {
    if (!navigator.onLine) {
      setIsOffline(true);
      setShowPopup(true);
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
      // console.log("First check failed, retrying...");
  
      // Retry after 1 second to avoid false positives
      setTimeout(async () => {
        try {
          await fetch("https://www.gstatic.com/generate_204", { method: "GET", mode: "no-cors" });
          setIsOffline(false);
        } catch (err) {
          // console.log("Second check failed. Confirming offline mode.");
          setIsOffline(true);
          setShowPopup(true);
        }
      }, 1000);
    }
  };
  

  // Function to check printer error
  const checkPrinterError = () => {
    if (!code) return;

    const errorRef = ref(db, `Printers/${code}/details/status_message`);

    const unsubscribe = onValue(errorRef, (snapshot) => {
      const errorMessage = snapshot.val();

      if (errorMessage && !errorMessage.toLowerCase().includes("active")) {
        setError(errorMessage);
        if(errorMessage.toLowerCase().includes("jammed")){
          setErrVideo("")
        }
        else if(errorMessage.toLowerCase().includes("empty")){
          setErrVideo("https://atomte.com/printer-error.mp4")
        }
        else if(errorMessage.toLowerCase().includes("toner")){
          setErrVideo("https://atomte.com/printer-error.mp4")
        }
        else if(errorMessage.toLowerCase().includes("power")){
          setErrVideo(ad1)
        }
      else{
        setErrVideo("https://atomte.com/printer-error.mp4")
      }
        setShowPopup(true);
      } else {
        setError(null);
        setShowPopup(false);
      }
    });

    return () => unsubscribe(); // Cleanup listener
  };

  // Check internet connectivity every 3 seconds
  useEffect(() => {
    checkInternetConnection();
    const interval = setInterval(checkInternetConnection, 3000);
    return () => clearInterval(interval);
  }, []);

  // Check printer error when internet is available
  useEffect(() => {
    if (!isOffline) {
      checkPrinterError();
    }
  }, [code, isOffline]);

  if (!showPopup) return null; // Hide popup if no issue

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        {isOffline ? (
          <>
          <p className="contact-info">
              For assistance, call: <strong>9849033249</strong> (Available 24/7)
            </p>
            <p className="contact-info">
              <strong>NO Internet Connection</strong>
            </p>
          </>
        ) : (
          <>
            <p className="contact-info">
              For assistance, call: <strong>9849033249</strong>
            </p>
            <p className="error-message">
              <strong>Printer Error:</strong> {error}
            </p>
            <VideoPlayer className="error-video" videoFile={errVideo} width="100%" height="100%" mute={false} />
          </>
        )}
      </div>
    </div>
  );
};

export default PrinterErrorPopup;
