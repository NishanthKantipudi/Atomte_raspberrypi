import React, { useEffect, useRef } from "react";

const VideoPlayer = ({ videoFile = "/ads/ad1.mp4", width = "640", height = "419" }) => {
  const videoRef = useRef(null);
  const audioContextRef = useRef(null);
  const sourceRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;

    // Step 1: Start muted (autoplay allowed)
    video.muted = true;
    video.play().catch((error) => console.log("Muted autoplay failed:", error));

    // Step 2: Create an AudioContext
    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    sourceRef.current = audioContextRef.current.createMediaElementSource(video);
    sourceRef.current.connect(audioContextRef.current.destination);

    // Step 3: Unmute video after a delay
    setTimeout(() => {
      audioContextRef.current.resume().then(() => {
        video.muted = false;
        video.play().catch((error) => console.log("Unmuted autoplay failed:", error));
      });
    }, 1000); 

  }, []);

  return (
    <div>
      <video
        ref={videoRef}
        src={window.location.origin + videoFile}
        width={width}
        height={height}
        loop
        autoPlay
        preload="auto"
        playsInline
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
