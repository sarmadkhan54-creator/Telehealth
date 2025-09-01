import React, { useState, useEffect } from 'react';

const PWAInstallPrompt = () => {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Check if app is already installed
    const checkIfInstalled = () => {
      // Check for standalone mode (installed PWA)
      if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
        setIsInstalled(true);
        return;
      }
      
      // Check for Android WebAPK
      if (document.referrer.includes('android-app://')) {
        setIsInstalled(true);
        return;
      }
    };

    checkIfInstalled();

    // Listen for the beforeinstallprompt event
    const handleBeforeInstallPrompt = (e) => {
      console.log('📱 PWA install prompt available');
      e.preventDefault(); // Prevent the default browser install prompt
      setDeferredPrompt(e);
      setIsVisible(true);
    };

    // Listen for app installed event
    const handleAppInstalled = () => {
      console.log('🎉 PWA installed successfully');
      setIsInstalled(true);
      setIsVisible(false);
      
      // Show success notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Greenstar Health Installed!', {
          body: 'The app has been installed successfully and can be accessed from your home screen.',
          icon: '/icons/icon-192x192.png'
        });
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    try {
      // Show the install prompt
      const result = await deferredPrompt.prompt();
      console.log('📱 Install prompt result:', result.outcome);

      if (result.outcome === 'accepted') {
        console.log('✅ User accepted the install prompt');
      } else {
        console.log('❌ User dismissed the install prompt');
      }

      // Clear the deferredPrompt
      setDeferredPrompt(null);
      setIsVisible(false);
    } catch (error) {
      console.error('Error showing install prompt:', error);
    }
  };

  const handleDismiss = () => {
    setIsVisible(false);
    setDeferredPrompt(null);
  };

  // Don't show if already installed or prompt not available
  if (isInstalled || !isVisible || !deferredPrompt) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:left-auto md:right-4 md:w-96">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <img 
              src="/icons/icon-72x72.png" 
              alt="Greenstar Health" 
              className="w-12 h-12 rounded-lg"
            />
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-gray-900">
              Install Greenstar Health
            </h3>
            <p className="text-xs text-gray-600 mt-1">
              Add to your home screen for quick access to appointments and video calls
            </p>
            
            <div className="flex space-x-2 mt-3">
              <button
                onClick={handleInstallClick}
                className="flex-1 bg-green-600 text-white text-xs font-medium px-3 py-2 rounded-md hover:bg-green-700 transition-colors"
              >
                📱 Install App
              </button>
              <button
                onClick={handleDismiss}
                className="flex-1 bg-gray-100 text-gray-700 text-xs font-medium px-3 py-2 rounded-md hover:bg-gray-200 transition-colors"
              >
                Later
              </button>
            </div>
          </div>
          
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 text-gray-400 hover:text-gray-500"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default PWAInstallPrompt;