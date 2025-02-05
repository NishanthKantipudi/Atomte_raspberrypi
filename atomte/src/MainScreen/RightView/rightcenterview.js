import React, { useEffect, useRef, useState } from "react";

const VideoPlayer = ({ videoFile = "/ads/ad1.mp4", width = "640", height = "400" ,mute=true}) => {
  const videoRef = useRef(null);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.muted = mute; // Ensure unmuted
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise.catch((error) => {
          console.log("Autoplay blocked, waiting for user interaction:", error);
          setIsMuted(true); // Mute the video if autoplay is blocked
          video.muted = true;
        });
      }
    }
  }, []);

  // Unmute when the user interacts
  const handleUnmute = () => {
    if (videoRef.current) {
      videoRef.current.muted = false;
      setIsMuted(false);
      videoRef.current.play(); // Restart playback after unmuting
    }
  };

  return (
    <div onClick={handleUnmute} style={{ cursor: isMuted ? "pointer" : "default" }}>
      <video
        ref={videoRef}
        src={window.location.origin + videoFile}
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
      {isMuted && <p style={{ textAlign: "center", color: "red" }}>Click to unmute</p>}
    </div>
  );
};

export default VideoPlayer;
