import React from "react";
import VideoPlayer from "./rightcenterview";
import "./rightview.css";
import QRCode from "qrcode.react";
const SuperRightView = ({ code,videoFile1, videoFile2, width = "500" }) => {
  return (
    <div className="super-right-view">
      <VideoPlayer className="ad2" videoFile={videoFile1} width={width} height="230" />
        <div className="separator"></div>
      <VideoPlayer className="ad3" videoFile={videoFile2} width={width} height="230" />
      {/* <div className="center">
         
            <div className="qrcode">
                <h3>For Advertising</h3>
            <QRCode
                value={'https://atomte.com/ads?code='+code}
                size={200}
                bgColor="#ffffff"
                fgColor="#000000"
                level="H"
                includeMargin={true}
            />
            </div>
        </div> */}
    </div>
  );
};

export default SuperRightView;
