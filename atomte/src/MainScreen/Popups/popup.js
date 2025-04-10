import React, { useState, useEffect } from "react";
import app from "../../firebase/firebase";
import { getDatabase, ref, onValue } from "firebase/database";
import "./popup.css";
import VideoPlayer from "../RightView/rightcenterview";
import ad1 from "../ads/ad1.mp4"; //testing

const PrinterErrorPopup = ({ code }) => {
  const [error, setError] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [errVideo, setErrVideo] = useState("");
  const db = getDatabase(app);

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

  // Check printer error 
  useEffect(() => {
    checkPrinterError();
  }, [code]);

  if (!showPopup) return null; // Hide popup if no issue

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        <h2 className="contact-info">
          For assistance, call: <strong>9849033249 </strong>(Available 24/7)
        </h2>
        <p className="error-message">
          Printer Error: {error}
        </p>
        <VideoPlayer className="error-video" videoFile={errVideo} width="100%" height="100%" mute={false} />
      </div>
    </div>
  );
};

export default PrinterErrorPopup;