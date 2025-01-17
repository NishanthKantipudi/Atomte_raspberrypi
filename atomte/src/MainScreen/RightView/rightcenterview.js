import React from "react";

const VideoPlayer = ({ videoFile="./ad1.mp4", width = "640", height = "309" }) => {
  return (
    <div>
      <video
        src={videoFile}
        width={width}
        height={height}
        autoPlay
        loop
        muted
        preload="auto" // Preload video data
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
