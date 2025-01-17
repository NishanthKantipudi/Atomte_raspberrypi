import React, { useState, useEffect } from 'react';
import './rightview.css';
const WelcomeMessage = () => {
  const messages = [
    "Welcome to our service!",
    "Thank you for choosing us.",
    "We're here to make your life easier.",
    "Experience seamless automation.",
    "Your satisfaction is our priority.",
    "Simplifying your tasks, one click at a time.",
    "Empowering you with technology.",
    "Where efficiency meets excellence.",
    "Automation made simple.",
    "Transforming ideas into reality.",
    "Your partner in innovation.",
    "Leading the way in automated solutions.",
    "Pioneering the future of convenience.",
    "Crafting intelligent solutions for you.",
    "Reliability at its best.",
    "Innovating the everyday.",
    "Where your needs meet our expertise.",
    "Taking the hassle out of your tasks.",
    "Excellence in every interaction.",
    "Redefining service standards."
  ];

  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessageIndex((prevIndex) => (prevIndex + 1) % messages.length);
    }, 60000); // Change message every minute (60000 ms)
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container">
      <h1 className="title">Welcome!</h1>
      <h2 className="big-text">Innovate, Automate, Excel</h2>
      <p className="message">{messages[currentMessageIndex]}</p>
      <h2 className="big-text">Your Future, Our Technology</h2>
      <p className="thank-you">Thank you for using our service!</p>
    </div>
  );
};

export default WelcomeMessage;
