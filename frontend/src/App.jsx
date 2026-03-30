import { useEffect, useState } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { addDoc, collection, deleteDoc, doc, limit, onSnapshot, orderBy, query, serverTimestamp } from 'firebase/firestore';
import './App.css';
import Dashboard from './Pages/Dashboard';
import { auth, db } from './firebase';
import Login from './Login';

const App = () => {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [searchHistory, setSearchHistory] = useState([]);
  const [wishlist, setWishlist] = useState([]);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (!currentUser) {
        setSearchHistory([]);
        setWishlist([]);
      }
      setAuthLoading(false);
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (!user) {
      return undefined;
    }

    const historyRef = query(collection(db, 'users', user.uid, 'searchHistory'), orderBy('timestamp', 'desc'), limit(8));
    const wishlistRef = query(collection(db, 'users', user.uid, 'wishlist'), orderBy('addedAt', 'desc'), limit(20));

    const unsubscribeHistory = onSnapshot(historyRef, (snapshot) => {
      setSearchHistory(snapshot.docs.map((entry) => ({ id: entry.id, ...entry.data() })));
    });

    const unsubscribeWishlist = onSnapshot(wishlistRef, (snapshot) => {
      setWishlist(snapshot.docs.map((entry) => ({ id: entry.id, ...entry.data() })));
    });

    return () => {
      unsubscribeHistory();
      unsubscribeWishlist();
    };
  }, [user]);

  const saveSearchHistory = async (entry) => {
    if (!user) {
      return;
    }

    await addDoc(collection(db, 'users', user.uid, 'searchHistory'), {
      ...entry,
      userId: user.uid,
      timestamp: serverTimestamp(),
    });
  };

  const toggleWishlist = async (item) => {
    if (!user) {
      return false;
    }

    const existingItem = wishlist.find(
      (wishlistItem) =>
        (wishlistItem.asin && wishlistItem.asin === item.asin) ||
        (
          wishlistItem.name === item.name &&
          wishlistItem.platform === item.platform &&
          wishlistItem.brand === item.brand
        )
    );

    if (existingItem) {
      await deleteDoc(doc(db, 'users', user.uid, 'wishlist', existingItem.id));
      return false;
    }

    await addDoc(collection(db, 'users', user.uid, 'wishlist'), {
      ...item,
      userId: user.uid,
      addedAt: serverTimestamp(),
    });
    return true;
  };

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div>
          <p className="app-kicker">GetOne4u</p>
          <h1 className="app-heading">Shopping intelligence workspace</h1>
        </div>
        <div className="auth-panel">
          {authLoading ? (
            <p className="auth-status">Checking account...</p>
          ) : user ? (
            <>
              <div className="user-chip">
                {user.photoURL ? <img alt={user.displayName || 'User'} src={user.photoURL} /> : <span>{user.email?.slice(0, 1).toUpperCase()}</span>}
                <div>
                  <strong>{user.displayName || 'Signed in user'}</strong>
                  <p>{user.email}</p>
                </div>
              </div>
              <button className="auth-action secondary" onClick={() => signOut(auth)} type="button">
                Sign out
              </button>
            </>
          ) : (
            <>
              <p className="auth-status">Sign in to sync history and save favourites.</p>
              <Login className="auth-action" />
            </>
          )}
        </div>
      </header>

      <Dashboard
        onSaveSearch={saveSearchHistory}
        onToggleWishlist={toggleWishlist}
        searchHistory={searchHistory}
        user={user}
        wishlist={wishlist}
      />
    </div>
  );
};

export default App;
