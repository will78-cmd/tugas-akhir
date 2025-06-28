importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyBLf0rYNYb5aQ22K_pDi3ombEhbgioQXnM",
  authDomain: "tugas-akhir-8ec00.firebaseapp.com",
  projectId: "tugas-akhir-8ec00",
  messagingSenderId: "557339400572",
  appId: "1:557339400572:web:22490592e955944a08acf9"
});
const messaging = firebase.messaging();
messaging.onBackgroundMessage(function(payload) {
  self.registration.showNotification(
    payload.notification.title,
    {
      body: payload.notification.body,
      icon: '/streamlit.png'
    }
  );
});
