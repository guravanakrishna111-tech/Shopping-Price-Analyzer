import { initializeApp } from 'firebase/app';
import { getAnalytics, isSupported } from 'firebase/analytics';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: 'AIzaSyC5ZK27m5Gs4IJIFBK_QJmsYRaVpQdGs68',
  authDomain: 'getone4u-41aa1.firebaseapp.com',
  projectId: 'getone4u-41aa1',
  storageBucket: 'getone4u-41aa1.firebasestorage.app',
  messagingSenderId: '788197536831',
  appId: '1:788197536831:web:7c1e691882657a36ef348a',
  measurementId: 'G-6DN8KPM6C6',
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

let analytics = null;
if (typeof window !== 'undefined') {
  isSupported()
    .then((supported) => {
      if (supported) {
        analytics = getAnalytics(app);
      }
    })
    .catch(() => {
      analytics = null;
    });
}

export { analytics, app, auth, db };
