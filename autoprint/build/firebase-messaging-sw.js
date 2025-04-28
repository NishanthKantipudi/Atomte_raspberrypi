// public/firebase-messaging-sw.js
importScripts("https://www.gstatic.com/firebasejs/9.1.3/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/9.1.3/firebase-messaging-compat.js");
const firebaseConfig = {
  apiKey: "AIzaSyC7J21mp2hY2JhR5JiDpTl9dvVSWe4gfLA",
  authDomain: "skilldevelopmentapp.firebaseapp.com",
  projectId: "skilldevelopmentapp",
  storageBucket: "skilldevelopmentapp.appspot.com",
  messagingSenderId: "1014404864768",
  appId: "1:1014404864768:web:ebb2c96faf9f82250671e5",
  measurementId: "G-0RDVCP0RXB"
};
firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();
messaging.onBackgroundMessage((payload) => {
  console.log('Received background message:', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/atomicon.png'
  };
  self.registration.showNotification(notificationTitle, notificationOptions);
});



