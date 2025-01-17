import React from "react";
import LeftView from "./LeftView/leftview";
import RightTopView from "./RightView/righttopview";
import VideoPlayer from "./RightView/rightcenterview";
import SuperRightView from "./RightView/superrightview";
import "./main.css";
import ad1 from "./ads/ad1.mp4";
import ad2 from "./ads/ad2.mp4";
import ad3 from "./ads/ad3.mp4";
import { signInWithEmailAndPassword, getAuth } from 'firebase/auth';
import { get } from "firebase/database";
import { onValue, ref, getDatabase, set, child } from "firebase/database";
import { useState,useEffect } from "react";
import app from "../firebase/firebase";





export default function MainScreen() {
  const [code, setCode] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    // Parse the URL parameters
    const params = new URLSearchParams(window.location.search);
    const codeParam = params.get("code");

    if (codeParam) {
      setCode(codeParam);
      setEmail(codeParam+"@gmail.com");
      setPassword(codeParam);
      console.log("Code from URL:", codeParam);
    }
  }, []);
  const loginWithEmailPassword = async (email, password) => {
        try {
          const userCredential = await signInWithEmailAndPassword(getAuth(app), email, password);
          const user = userCredential.user;
          console.log('User signed in:', user);
          return user;
        } catch (error) {
          console.error('Error signing in:', error.message);
          throw error;
        }
      };
      useEffect(() => {
        if (!email || !password) {
          return;
        }
        const loginUser = async () => {
          try {
            await loginWithEmailPassword(email, password);
          } catch (error) {
            console.error("Failed to log in:", error);
          }
        };
        loginUser();
      }, [email, password]);


    return (
        <div className="MainScreen">
            <div className="LeftView" >
                <LeftView code={code}/>
            </div>
            <div className="separator"></div>
            <div className="CenterView">
            <h1 className="title-atomte">ATOMTE</h1>
                <RightTopView className="RightTopView" code={code}/>
                <VideoPlayer className="ad1" videoFile={ad1} width="100%" />
            </div>
            <div className="separator"></div>
            <div className="RightView">
                <SuperRightView code={code} videoFile1={ad2} videoFile2={ad3}/>
            </div>
        </div>
    );
}