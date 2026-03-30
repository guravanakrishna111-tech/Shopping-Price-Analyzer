import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth';
import { auth } from './firebase';

const Login = ({ className = '', label = 'Sign in with Google' }) => {
  const handleLogin = async () => {
    const provider = new GoogleAuthProvider();
    await signInWithPopup(auth, provider);
  };

  return (
    <button className={className} onClick={handleLogin} type="button">
      {label}
    </button>
  );
};

export default Login;
