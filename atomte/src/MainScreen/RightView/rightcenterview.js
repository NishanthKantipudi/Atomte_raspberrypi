import React, { useEffect, useRef, useState } from "react";
const VideoPlayer = ({ videoFile = "/ads/ad1.mp4", width = "640", height = "400" ,mute=true}) => {
  const videoRef = useRef(null);

  return (
    <div>
      <video
        ref={videoRef}
        src={videoFile}
        width={width}
        height={height}
        crossOrigin="anonymous"
        muted={mute}
        loop
        autoPlay
        playsInline
        preload="auto"
        style={{ 
          display: "block",
          margin: "0 auto",
          objectFit: "cover",
        }}
      >
        Your browser does not support the video tag.
      </video>
    </div>
  );
};

export default VideoPlayer;
