import React, { useState, useEffect } from "react";
import LeftView from "./LeftView/leftview";
import RightTopView from "./RightView/righttopview";
import VideoPlayer from "./RightView/rightcenterview";
import SuperRightView from "./RightView/superrightview";
import "./main.css";
import PrinterErrorPopup from "./Popups/popup";

import { signInWithEmailAndPassword, getAuth } from "firebase/auth";
import app from "../firebase/firebase";
import ad1 from "./ads/ad1.mp4";
import ad2 from "./ads/ad2.mp4";
import ad3 from "./ads/ad3.mp4";
import logo from "../media/A.png"

export default function MainScreen() {
  const [code, setCode] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [userLoggedIn, setUserLoggedIn] = useState(false);

  useEffect(() => {
    // Parse URL parameters
    const params = new URLSearchParams(window.location.search);
    const codeParam = params.get("code");

    if (codeParam) {
      setCode(codeParam);
      setEmail(`${codeParam}@gmail.com`);
      setPassword(codeParam);
      console.log("Code from URL:", codeParam);
    }
  }, []);

  const loginWithEmailPassword = async (email, password) => {
    try {
      const userCredential = await signInWithEmailAndPassword(
        getAuth(app),
        email,
        password
      );
      console.log("User signed in:", userCredential.user);
      setUserLoggedIn(true);
    } catch (error) {
      console.error("Error signing in:", error.message);
    }
  };

  useEffect(() => {
    if (!email || !password || userLoggedIn) return;

    loginWithEmailPassword(email, password);
  }, [email, password, userLoggedIn]);


  return (
    
    <div className="Total">
      
      <div className="MainScreen">
        <div className="LeftView">
          <LeftView code={code} />
        </div>
        <div className="separator"></div>
        <div className="CenterView">
          <div className="logo-container">
            <img src={logo} className="logo" alt="A"/>
            <h1 className="title-atomte">TOMTE</h1>
          </div>
          <span><p>Any issues call 9849033249, Available 24/7</p></span>
          <RightTopView className="RightTopView" code={code} />
        </div>
      </div>
      <div className="separator"></div>


      
      {/* {ad1 && (
        <div className="ad1-container">
          <VideoPlayer className="ad1" videoFile={ad1} width="100%" height="100%" mute={false} />
        </div>
      )} */}

      {/* <div className="RightView full-screen">
        <SuperRightView code={code} videoFile1={ad2} videoFile2={ad3} />
      </div> */}


      <PrinterErrorPopup code={code} />
      
    </div>
  );
}
