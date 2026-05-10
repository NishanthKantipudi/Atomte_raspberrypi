import React, { useState, useEffect } from "react";
import app from "../../firebase/firebase";
import { getDatabase, ref, onValue, set,get } from "firebase/database";
import "./popup.css";
import VideoPlayer from "../RightView/rightcenterview";

const PrinterErrorPopup = ({ code }) => {
  const [error, setError] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [errVideo, setErrVideo] = useState("");
  const db = getDatabase(app);
  const [mobile, setMobile] = useState("");

  // Function to check printer error
  const checkPrinterError = () => {
    if (!code) return;

    const errorRef = ref(db, `Printers/${code}/details/status_message`);

    const unsubscribe = onValue(errorRef, (snapshot) => {
      const errorMessage = snapshot.val();

      if (errorMessage && !errorMessage.toLowerCase().includes("active")) {
        setError(errorMessage);
        if(errorMessage.toLowerCase().includes("jammed")){
          setErrVideo("http://localhost:7000/videos/jammed.mp4")
        }
        else if(errorMessage.toLowerCase().includes("empty")){
          setErrVideo("http://localhost:7000/videos/empty.mp4")
        }
        else if(errorMessage.toLowerCase().includes("toner")){
          setErrVideo("http://localhost:7000/videos/tonor.mp4")
        }
        else if(errorMessage.toLowerCase().includes("power")){
          setErrVideo("http://localhost:7000/videos/power.mp4")
        }
        else{
          setErrVideo("http://localhost:7000/videos/error.mp4")
        }
        setShowPopup(true);
      } else {
        setError(null);
        setShowPopup(false);
      }
    });

    return () => unsubscribe(); // Cleanup listener
  };
 const fetchMobile = async () => {
  try {
    const snapshot = await get(ref(db, `Printers/${code}/details/service_number`));

    if (snapshot.exists()) {
      setMobile(snapshot.val());
    } else {
      console.log("No mobile number found for this printer.");
      setMobile("");
    }
  } catch (error) {
    console.error("Error fetching mobile number:", error);
    setMobile("");
  }
};

  // Check printer error 
  useEffect(() => {
    fetchMobile();
    checkPrinterError();

    
  }, [code]);

  if (!showPopup) return null; // Hide popup if no issue

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        <h2 className="contact-info">
          For assistance, call: <strong>{mobile} </strong>(Available 24/7)
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