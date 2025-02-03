import React, { useEffect, useRef } from "react";
const VideoPlayer = ({ videoFile = "/ads/ad1.mp4", width = "640", height = "419", mute = true }) => {
  const videoRef = useRef(null);

  useEffect(() => {
    videoRef.current.play();
    videoRef.current.muted = mute;
  }, []);
  return (
    <div>
      
      <video
        ref={videoRef}
        src={window.location.origin + videoFile}
        width={width}
        height={height}
        muted
        loop
        controls
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
