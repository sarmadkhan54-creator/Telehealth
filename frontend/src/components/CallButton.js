import React, { useState, useRef, useEffect } from 'react';
import { Phone, PhoneCall, PhoneOff } from 'lucide-react';

const CallButton = ({ 
  appointmentId, 
  targetUser, 
  currentUser, 
  size = 'medium',
  variant = 'primary',
  maxRetries = 3,
  retryDelay = 30000 // 30 seconds between retries
}) => {
  const [isCalling, setIsCalling] = useState(false);
  const [callAttempts, setCallAttempts] = useState(0);
  const [isAutoRedialing, setIsAutoRedialing] = useState(false);
  const [nextRetryIn, setNextRetryIn] = useState(0);
  const retryTimeoutRef = useRef(null);
  const countdownIntervalRef = useRef(null);

  import { BACKEND_URL, API_URL } from '../config';
  const API = API_URL;

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, []);

  const startRetryCountdown = (delay) => {
    setNextRetryIn(Math.floor(delay / 1000));
    
    countdownIntervalRef.current = setInterval(() => {
      setNextRetryIn(prev => {
        if (prev <= 1) {
          clearInterval(countdownIntervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const scheduleAutoRedial = () => {
    if (callAttempts < maxRetries) {
      setIsAutoRedialing(true);
      startRetryCountdown(retryDelay);
      
      retryTimeoutRef.current = setTimeout(() => {
        setIsAutoRedialing(false);
        setNextRetryIn(0);
        initiateCall(); // Automatically redial
      }, retryDelay);
      
      console.log(`📞 Auto-redial scheduled in ${retryDelay/1000} seconds (attempt ${callAttempts + 1}/${maxRetries})`);
    } else {
      console.log(`📞 Maximum retry attempts (${maxRetries}) reached for appointment ${appointmentId}`);
      alert(`Call attempts exhausted. Please try again later or contact the ${targetUser?.full_name || 'participant'} directly.`);
    }
  };

  const cancelAutoRedial = () => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    setIsAutoRedialing(false);
    setNextRetryIn(0);
    console.log('📞 Auto-redial cancelled');
  };

  const initiateCall = async () => {
    try {
      setIsCalling(true);
      setCallAttempts(prev => prev + 1);

      // Cancel any pending auto-redial
      cancelAutoRedial();

      // Get or create Jitsi session for this appointment
      const response = await fetch(`${API}/video-call/session/${appointmentId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        
        // Configure Jitsi URL to disable moderator requirement and enable better call handling
        const configuredJitsiUrl = `${data.jitsi_url}#config.startWithAudioMuted=false&config.startWithVideoMuted=false&config.requireDisplayName=false&config.enableWelcomePage=false&config.prejoinPageEnabled=false&config.enableModeratedDiscussion=false&config.disableModeratorIndicator=true&config.callStatsID=greenstar&config.enableCallEndFeedback=true&userInfo.displayName=${currentUser.full_name}`;
        
        // Open video call
        let callWindow;
        if (/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
          // On mobile devices, open in same tab
          window.location.href = configuredJitsiUrl;
        } else {
          // On desktop, open in new window and monitor for call end
          callWindow = window.open(configuredJitsiUrl, `jitsi_call_${appointmentId}`, 'width=1200,height=800');
          
          if (!callWindow || callWindow.closed || typeof callWindow.closed == 'undefined') {
            // Popup blocked, use same tab
            window.location.href = configuredJitsiUrl;
          } else {
            // Monitor call window for closure (call ended)
            const checkCallStatus = setInterval(() => {
              try {
                if (callWindow.closed) {
                  clearInterval(checkCallStatus);
                  console.log('📞 Call window closed - call ended');
                  
                  // Schedule auto-redial if within retry limits
                  if (callAttempts < maxRetries) {
                    scheduleAutoRedial();
                  }
                }
              } catch (error) {
                // Window access might be restricted, but closure detection might still work
                console.log('Call window monitoring limited due to cross-origin restrictions');
              }
            }, 1000);
            
            // Stop monitoring after 5 minutes (assume call is stable)
            setTimeout(() => {
              clearInterval(checkCallStatus);
            }, 300000);
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
        
        // Schedule retry for session failures too
        if (callAttempts < maxRetries) {
          scheduleAutoRedial();
        }
      }

    } catch (error) {
      console.error('Error initiating call:', error);
      alert('Error starting video call. Please try again.');
      setIsCalling(false);
      
      // Schedule retry for network failures
      if (callAttempts < maxRetries) {
        scheduleAutoRedial();
      }
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
      primary: (isCalling || isAutoRedialing)
        ? "bg-green-600 text-white animate-pulse" 
        : "bg-green-500 text-white hover:bg-green-600 active:bg-green-700",
      secondary: (isCalling || isAutoRedialing)
        ? "bg-blue-600 text-white animate-pulse" 
        : "bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700",
      outline: (isCalling || isAutoRedialing)
        ? "border-2 border-green-600 text-green-600 animate-pulse" 
        : "border-2 border-green-500 text-green-500 hover:bg-green-50 active:bg-green-100",
      ghost: (isCalling || isAutoRedialing)
        ? "text-green-600 animate-pulse" 
        : "text-green-500 hover:bg-green-50 active:bg-green-100"
    };

    return `${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]}`;
  };

  const getIcon = () => {
    if (isCalling) {
      return <PhoneCall className={`${size === 'small' ? 'w-3 h-3' : size === 'large' ? 'w-6 h-6' : 'w-4 h-4'} animate-bounce`} />;
    }
    if (isAutoRedialing) {
      return <Phone className={`${size === 'small' ? 'w-3 h-3' : size === 'large' ? 'w-6 h-6' : 'w-4 h-4'} animate-pulse`} />;
    }
    return <Phone className={`${size === 'small' ? 'w-3 h-3' : size === 'large' ? 'w-6 h-6' : 'w-4 h-4'}`} />;
  };

  const getButtonText = () => {
    if (isCalling) {
      return 'Calling...';
    }
    if (isAutoRedialing && nextRetryIn > 0) {
      return `Retry in ${nextRetryIn}s`;
    }
    if (callAttempts > 0) {
      return `Call Again (${callAttempts}/${maxRetries})`;
    }
    return 'Call';
  };

  return (
    <div className="flex flex-col items-center space-y-2">
      <button
        onClick={isCalling || isAutoRedialing ? null : initiateCall}
        disabled={isCalling || isAutoRedialing}
        className={getButtonClasses()}
        title={`Call ${targetUser?.full_name || 'participant'}`}
      >
        {getIcon()}
        <span>{getButtonText()}</span>
        
        {callAttempts > 0 && !isAutoRedialing && (
          <span className={`ml-1 px-1.5 py-0.5 text-xs bg-opacity-20 bg-white rounded-full ${
            size === 'small' ? 'text-xs' : 'text-xs'
          }`}>
            {callAttempts}
          </span>
        )}
      </button>
      
      {isAutoRedialing && (
        <button
          onClick={cancelAutoRedial}
          className="text-xs text-red-500 hover:text-red-700 underline"
        >
          Cancel Auto-Redial
        </button>
      )}
      
      {callAttempts >= maxRetries && (
        <div className="text-xs text-orange-600 text-center">
          <p>Max attempts reached</p>
          <button
            onClick={() => {
              setCallAttempts(0);
              setIsAutoRedialing(false);
              setNextRetryIn(0);
            }}
            className="text-blue-500 hover:text-blue-700 underline"
          >
            Reset
          </button>
        </div>
      )}
    </div>
  );
};

export default CallButton;