import React, { useState } from 'react';
import { Phone, PhoneCall, PhoneOff } from 'lucide-react';

const CallButton = ({ 
  appointmentId, 
  targetUser, 
  currentUser, 
  size = 'medium',
  variant = 'primary' 
}) => {
  const [isCalling, setIsCalling] = useState(false);
  const [callAttempts, setCallAttempts] = useState(0);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  const initiateCall = async () => {
    try {
      setIsCalling(true);
      setCallAttempts(prev => prev + 1);

      // Get or create Jitsi session for this appointment
      const response = await fetch(`${API}/video-call/session/${appointmentId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        
        // Configure Jitsi URL to disable moderator requirement
        const configuredJitsiUrl = `${data.jitsi_url}#config.startWithAudioMuted=false&config.startWithVideoMuted=false&config.requireDisplayName=false&config.enableWelcomePage=false&config.prejoinPageEnabled=false&config.enableModeratedDiscussion=false&config.disableModeratorIndicator=true&userInfo.displayName=${currentUser.full_name}`;
        
        // Open video call
        if (/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
          // On mobile devices, open in same tab for better reliability
          window.location.href = configuredJitsiUrl;
        } else {
          // On desktop, try new window first, fallback to same tab
          const newWindow = window.open(configuredJitsiUrl, '_blank', 'width=1200,height=800');
          if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
            // Popup blocked, use same tab
            window.location.href = configuredJitsiUrl;
          }
        }

        console.log(`📞 Call initiated (attempt ${callAttempts + 1}) to ${targetUser?.full_name}`);
        
        // Reset calling state after a brief delay
        setTimeout(() => {
          setIsCalling(false);
        }, 2000);

      } else {
        console.error('Failed to get video call session');
        alert('Error starting video call. Please try again.');
        setIsCalling(false);
      }

    } catch (error) {
      console.error('Error initiating call:', error);
      alert('Error starting video call. Please try again.');
      setIsCalling(false);
    }
  };

  const getButtonClasses = () => {
    const baseClasses = "flex items-center justify-center space-x-2 rounded-lg font-medium transition-all duration-200";
    
    const sizeClasses = {
      small: "px-2 py-1 text-xs",
      medium: "px-4 py-2 text-sm",
      large: "px-6 py-3 text-base"
    };

    const variantClasses = {
      primary: isCalling 
        ? "bg-green-600 text-white animate-pulse" 
        : "bg-green-500 text-white hover:bg-green-600 active:bg-green-700",
      secondary: isCalling 
        ? "bg-blue-600 text-white animate-pulse" 
        : "bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700",
      outline: isCalling 
        ? "border-2 border-green-600 text-green-600 animate-pulse" 
        : "border-2 border-green-500 text-green-500 hover:bg-green-50 active:bg-green-100",
      ghost: isCalling 
        ? "text-green-600 animate-pulse" 
        : "text-green-500 hover:bg-green-50 active:bg-green-100"
    };

    return `${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]}`;
  };

  const getIcon = () => {
    if (isCalling) {
      return <PhoneCall className={`${size === 'small' ? 'w-3 h-3' : size === 'large' ? 'w-6 h-6' : 'w-4 h-4'} animate-bounce`} />;
    }
    return <Phone className={`${size === 'small' ? 'w-3 h-3' : size === 'large' ? 'w-6 h-6' : 'w-4 h-4'}`} />;
  };

  const getButtonText = () => {
    if (isCalling) {
      return 'Calling...';
    }
    if (callAttempts > 0) {
      return `Call Again (${callAttempts})`;
    }
    return 'Call';
  };

  return (
    <button
      onClick={initiateCall}
      disabled={isCalling}
      className={getButtonClasses()}
      title={`Call ${targetUser?.full_name || 'participant'}`}
    >
      {getIcon()}
      <span>{getButtonText()}</span>
      
      {callAttempts > 0 && (
        <span className={`ml-1 px-1.5 py-0.5 text-xs bg-opacity-20 bg-white rounded-full ${
          size === 'small' ? 'text-xs' : 'text-xs'
        }`}>
          {callAttempts}
        </span>
      )}
    </button>
  );
};

export default CallButton;