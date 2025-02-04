import React, { useEffect, useRef, useState } from "react";

const VideoPlayer = ({ videoFile = "/ads/ad1.mp4", width = "640", height = "400", mute = true }) => {
  const videoRef = useRef(null);
  const [isMuted, setIsMuted] = useState(mute);

  useEffect(() => {
    const video = videoRef.current;

    // Try to play the video when the component mounts
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise.catch((error) => {
        console.log("Autoplay blocked, waiting for user interaction:", error);
      });
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
    <div onClick={handleUnmute} style={{ cursor: "pointer" }}>
      <video
        ref={videoRef}
        src={window.location.origin + videoFile}
        width={width}
        height={height}
        muted={isMuted}
        loop
        autoPlay
        playsInline // Important for iOS devices
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
