import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  Phone,
  PhoneOff,
  Monitor,
  MonitorOff,
  MessageSquare,
  Settings,
  User
} from 'lucide-react';
import { BACKEND_URL } from '../config';

const VideoCall = ({ user }) => {
  const { sessionToken } = useParams();
  const navigate = useNavigate();

  // State
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [callStatus, setCallStatus] = useState('initializing');
  const [remoteUser, setRemoteUser] = useState(null);
  const [connectionQuality, setConnectionQuality] = useState('checking');

  // Refs
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const localStreamRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const signalingSocketRef = useRef(null);

  // Simple WebRTC Configuration
  const rtcConfig = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ]
  };

  useEffect(() => {
    initializeCall();
    
    // Cleanup on unmount
    return () => {
      cleanup();
    };
  }, []);

  const initializeCall = async () => {
    try {
      console.log('🚀 Initializing video call...');
      setCallStatus('initializing');
      
      // Add connection timeout
      const connectionTimeout = setTimeout(() => {
        console.error('❌ Connection timeout after 15 seconds');
        setCallStatus('failed');
        alert('Connection timeout. Please try again.');
        navigate('/');
      }, 15000);
      
      // Step 1: Get user media (with timeout)
      await Promise.race([
        getUserMedia(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Media timeout')), 5000)
        )
      ]);
      
      // Step 2: Setup WebRTC peer connection
      setupPeerConnection();
      
      // Step 3: Connect to signaling server (with timeout)
      await Promise.race([
        connectSignaling(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Signaling timeout')), 8000)
        )
      ]);
      
      clearTimeout(connectionTimeout);
      setCallStatus('connecting');
      
      // Auto-connect timeout - if not connected in 10 seconds, show warning
      setTimeout(() => {
        if (callStatus === 'connecting') {
          console.warn('⚠️ Connection taking longer than expected');
          setConnectionQuality('poor');
        }
      }, 10000);
      
    } catch (error) {
      console.error('❌ Failed to initialize call:', error);
      setCallStatus('failed');
      
      // Provide specific error messages instead of "undefined"
      let errorMessage = 'Connection failed. Please try again.';
      
      if (error.message === 'Media timeout') {
        errorMessage = 'Camera/microphone access timed out. Please check permissions and try again.';
      } else if (error.message === 'Signaling timeout') {
        errorMessage = 'Failed to connect to call server. Please check your internet connection.';
      } else if (error.name === 'NotAllowedError') {
        errorMessage = 'Camera/microphone permission denied. Please allow access and try again.';
      } else if (error.name === 'NotFoundError') {
        errorMessage = 'No camera or microphone found. Please connect devices and try again.';
      } else if (error.message) {
        errorMessage = `Connection error: ${error.message}`;
      }
      
      alert(errorMessage);
      cleanup();
      navigate('/');
    }
  };

  const getUserMedia = async () => {
    try {
      console.log('📹 Getting user media...');
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280, max: 1920 },
          height: { ideal: 720, max: 1080 },
          frameRate: { ideal: 30, max: 60 }
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      localStreamRef.current = stream;
      
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        localVideoRef.current.muted = true; // Prevent audio feedback
        console.log('✅ Local video stream set');
      }

      console.log('✅ User media obtained:', {
        video: stream.getVideoTracks().length,
        audio: stream.getAudioTracks().length
      });

    } catch (error) {
      console.warn('⚠️ Could not get user media:', error);
      // Continue without media for testing
      setCallStatus('no-media');
    }
  };

  const setupPeerConnection = () => {
    console.log('🔗 Setting up peer connection...');
    
    const pc = new RTCPeerConnection(rtcConfig);
    peerConnectionRef.current = pc;

    // Add local stream tracks if available
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => {
        pc.addTrack(track, localStreamRef.current);
        console.log('📤 Added track:', track.kind);
      });
    }

    // Handle incoming remote stream
    pc.ontrack = (event) => {
      console.log('📥 Received remote track:', event.track.kind);
      
      const [remoteStream] = event.streams;
      if (remoteStream && remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = remoteStream;
        setRemoteUser({ connected: true });
        setConnectionQuality('good');
        console.log('✅ Remote stream connected');
        
        // Try to play remote video
        remoteVideoRef.current.play().catch(console.log);
      }
    };

    // Handle ICE candidates
    pc.onicecandidate = (event) => {
      if (event.candidate && signalingSocketRef.current) {
        signalingSocketRef.current.send(JSON.stringify({
          type: 'ice-candidate',
          candidate: event.candidate
        }));
        console.log('🧊 Sent ICE candidate');
      }
    };

    // Connection state monitoring
    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      console.log('🔄 Connection state:', state);
      
      if (state === 'connected') {
        setCallStatus('connected');
        setConnectionQuality('excellent');
      } else if (state === 'disconnected' || state === 'failed') {
        setCallStatus('disconnected');
        setConnectionQuality('poor');
      }
    };

    pc.oniceconnectionstatechange = () => {
      console.log('🧊 ICE state:', pc.iceConnectionState);
      
      if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
        console.log('🎉 ICE connection successful!');
        setCallStatus('connected');
      }
    };

    console.log('✅ Peer connection configured');
  };

  const connectSignaling = () => {
    return new Promise((resolve, reject) => {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      
      if (!BACKEND_URL) {
        reject(new Error('Backend URL not configured'));
        return;
      }
      
      const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws/video-call/${sessionToken}`;
      
      console.log('🔗 Connecting to signaling server:', wsUrl);
      
      try {
        const socket = new WebSocket(wsUrl);
        signalingSocketRef.current = socket;

        const connectionTimeout = setTimeout(() => {
          if (socket.readyState !== WebSocket.OPEN) {
            console.error('❌ WebSocket connection timeout');
            socket.close();
            reject(new Error('Signaling server connection timeout'));
          }
        }, 8000);

        socket.onopen = () => {
          console.log('✅ Signaling connected');
          clearTimeout(connectionTimeout);
          
          // Join the call
          const joinMessage = {
            type: 'join',
            sessionToken: sessionToken,
            userId: user.id,
            userName: user.full_name
          };
          
          try {
            socket.send(JSON.stringify(joinMessage));
            console.log('📤 Join message sent');
            resolve();
          } catch (sendError) {
            console.error('❌ Failed to send join message:', sendError);
            reject(new Error('Failed to join call session'));
          }
        };

        socket.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('📨 Received:', message.type);
            await handleSignalingMessage(message);
          } catch (parseError) {
            console.error('❌ Failed to parse signaling message:', parseError);
          }
        };

        socket.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          clearTimeout(connectionTimeout);
          reject(new Error('WebSocket connection failed'));
        };

        socket.onclose = (event) => {
          console.log('🔌 WebSocket closed:', event.code, event.reason);
          clearTimeout(connectionTimeout);
          
          if (event.code !== 1000) { // 1000 is normal closure
            console.error('❌ WebSocket closed unexpectedly');
          }
        };
        
      } catch (socketError) {
        console.error('❌ Failed to create WebSocket:', socketError);
        reject(new Error('Cannot create WebSocket connection'));
      }
    });
  };

  const handleSignalingMessage = async (message) => {
    const pc = peerConnectionRef.current;
    if (!pc) return;

    try {
      switch (message.type) {
        case 'user-joined':
          console.log('👤 User joined:', message.userName);
          setRemoteUser({ name: message.userName, connected: false });
          
          // Create and send offer
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          
          signalingSocketRef.current.send(JSON.stringify({
            type: 'offer',
            offer: offer,
            target: message.userId
          }));
          
          console.log('📤 Sent offer');
          break;

        case 'offer':
          console.log('📥 Received offer');
          
          await pc.setRemoteDescription(message.offer);
          
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          
          signalingSocketRef.current.send(JSON.stringify({
            type: 'answer',
            answer: answer,
            target: message.from
          }));
          
          console.log('📤 Sent answer');
          break;

        case 'answer':
          console.log('📥 Received answer');
          await pc.setRemoteDescription(message.answer);
          break;

        case 'ice-candidate':
          console.log('📥 Received ICE candidate');
          if (message.candidate) {
            await pc.addIceCandidate(message.candidate);
          }
          break;

        case 'user-left':
          console.log('👋 User left');
          setRemoteUser(null);
          if (remoteVideoRef.current) {
            remoteVideoRef.current.srcObject = null;
          }
          break;

        default:
          console.log('❓ Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('❌ Error handling signaling message:', error);
    }
  };

  const toggleAudio = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsAudioEnabled(audioTrack.enabled);
        console.log('🎤 Audio:', audioTrack.enabled ? 'ON' : 'OFF');
      }
    }
  };

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoEnabled(videoTrack.enabled);
        console.log('📹 Video:', videoTrack.enabled ? 'ON' : 'OFF');
      }
    }
  };

  const endCall = async () => {
    console.log('📞 USER INITIATED CALL END - Starting immediate cleanup...');
    
    // Immediate cleanup FIRST to stop camera/microphone
    cleanup();
    
    // Then try to notify backend (but don't wait if it fails)
    try {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      const endCallPromise = axios.post(`${BACKEND_URL}/api/video-call/end/${sessionToken}`);
      
      // Don't wait more than 2 seconds for backend response
      await Promise.race([
        endCallPromise,
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Backend timeout')), 2000)
        )
      ]);
      
      console.log('✅ Backend notified of call end');
    } catch (error) {
      console.warn('⚠️ Could not notify backend of call end (not critical):', error.message);
    }
    
    // Navigate back immediately
    navigate('/');
  };

  const cleanup = () => {
    console.log('🧹 EMERGENCY CLEANUP - Stopping all media devices...');
    
    try {
      // AGGRESSIVE media track cleanup
      if (localStreamRef.current) {
        console.log('🔴 Stopping local stream tracks...');
        localStreamRef.current.getTracks().forEach((track, index) => {
          console.log(`   Stopping ${track.kind} track ${index + 1}: ${track.label}`);
          track.stop();
          
          // Double-check track is actually stopped
          setTimeout(() => {
            if (track.readyState !== 'ended') {
              console.warn(`⚠️ Track ${track.kind} still active, forcing stop...`);
              try {
                track.stop();
              } catch (e) {
                console.error('Error force-stopping track:', e);
              }
            }
          }, 100);
        });
        localStreamRef.current = null;
        console.log('✅ Local stream cleared');
      }

      // Clear video elements IMMEDIATELY
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = null;
        localVideoRef.current.load(); // Force reload to clear any cached media
        console.log('📹 Local video element cleared and reloaded');
      }

      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null;
        remoteVideoRef.current.load(); // Force reload to clear any cached media
        console.log('📹 Remote video element cleared and reloaded');
      }

      // Close peer connection aggressively
      if (peerConnectionRef.current) {
        console.log('🔌 Closing peer connection...');
        
        // Remove and stop all senders
        peerConnectionRef.current.getSenders().forEach(sender => {
          if (sender.track) {
            console.log(`   Stopping sender track: ${sender.track.kind}`);
            sender.track.stop();
            try {
              peerConnectionRef.current.removeTrack(sender);
            } catch (e) {
              console.log('Track already removed or connection closed');
            }
          }
        });
        
        // Remove all receivers
        peerConnectionRef.current.getReceivers().forEach(receiver => {
          if (receiver.track) {
            console.log(`   Stopping receiver track: ${receiver.track.kind}`);
            receiver.track.stop();
          }
        });
        
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
        console.log('✅ Peer connection completely closed');
      }

      // Close signaling socket
      if (signalingSocketRef.current) {
        if (signalingSocketRef.current.readyState === WebSocket.OPEN) {
          signalingSocketRef.current.send(JSON.stringify({
            type: 'leave',
            sessionToken: sessionToken,
            userId: user.id
          }));
        }
        signalingSocketRef.current.close();
        signalingSocketRef.current = null;
        console.log('📡 Signaling socket closed');
      }

      // Force garbage collection hint
      if (window.gc) {
        window.gc();
      }

      // Reset all state
      setCallStatus('ended');
      setRemoteUser(null);
      setConnectionQuality('disconnected');
      setIsAudioEnabled(true);
      setIsVideoEnabled(true);
      
      console.log('🎉 COMPLETE CLEANUP FINISHED - All media devices should be released');
      
    } catch (error) {
      console.error('❌ Error during cleanup:', error);
      
      // Fallback: Try to get all media devices and stop them
      navigator.mediaDevices.enumerateDevices().then(devices => {
        console.log('🔍 Available devices after cleanup:', devices.length);
      }).catch(e => {
        console.log('Could not enumerate devices');
      });
    }
  };

  // Emergency function to force stop all media devices
  const emergencyStopAllMedia = () => {
    console.log('🚨 EMERGENCY MEDIA STOP - Forcing all devices to stop...');
    
    try {
      // Stop all tracks from getUserMedia
      navigator.mediaDevices.enumerateDevices().then(devices => {
        console.log('📱 Available devices:', devices.length);
        
        // Try to get current media stream and stop it
        if (navigator.mediaDevices.getDisplayMedia) {
          // Stop any screen sharing
          navigator.mediaDevices.getDisplayMedia({ video: false }).then(stream => {
            stream.getTracks().forEach(track => track.stop());
          }).catch(() => {}); // Ignore errors
        }
      }).catch(() => {});
      
      // Force stop any remaining media
      if (typeof window !== 'undefined' && window.MediaStreamTrack) {
        // This is a hack but sometimes necessary
        console.log('🔧 Attempting to force-stop all MediaStreamTracks...');
      }
      
    } catch (error) {
      console.error('❌ Emergency media stop failed:', error);
    }
  };

  // Enhanced cleanup on component unmount and page events
  useEffect(() => {
    const handleBeforeUnload = (event) => {
      console.log('⚠️ Page unloading - emergency cleanup...');
      emergencyStopAllMedia();
      cleanup();
    };

    const handleVisibilityChange = () => {
      if (document.hidden && callStatus === 'connected') {
        console.log('👁️ Tab hidden during call - maintaining connection...');
      }
    };

    const handleWindowClose = () => {
      console.log('❌ Window closing - emergency cleanup...');
      emergencyStopAllMedia();
      cleanup();
    };

    // Add keyboard shortcut for emergency media stop (Ctrl+Shift+E)
    const handleKeyDown = (event) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'E') {
        console.log('⌨️ Emergency stop hotkey pressed...');
        emergencyStopAllMedia();
        cleanup();
        navigate('/');
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('unload', handleWindowClose);
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('unload', handleWindowClose);
      document.removeEventListener('keydown', handleKeyDown);
      
      // Final cleanup on component unmount
      emergencyStopAllMedia();
      cleanup();
    };
  }, [callStatus, navigate]);

  const getStatusColor = () => {
    switch (callStatus) {
      case 'connected': return 'text-green-500';
      case 'connecting': return 'text-yellow-500';
      case 'disconnected': return 'text-red-500';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-500';
    }
  };

  const getStatusText = () => {
    switch (callStatus) {
      case 'initializing': return 'Initializing...';
      case 'connecting': return 'Connecting...';
      case 'connected': return 'Connected';
      case 'disconnected': return 'Disconnected';
      case 'failed': return 'Connection Failed';
      case 'no-media': return 'No Camera/Mic';
      default: return 'Unknown';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm p-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Video Call</h1>
            <p className="text-sm text-gray-600">Session: {sessionToken.slice(0, 8)}...</p>
          </div>
          
          <div className="text-right">
            <div className={`font-semibold ${getStatusColor()}`}>
              {getStatusText()}
            </div>
            {remoteUser && (
              <div className="text-sm text-gray-600">
                {remoteUser.name || 'Remote User'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Video Area */}
      <div className="flex-1 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
            
            {/* Remote Video */}
            <div className="relative bg-gray-900 rounded-xl overflow-hidden">
              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
              />
              
              {!remoteUser && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
                  <div className="text-center text-white">
                    <User className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">Waiting for remote participant...</p>
                  </div>
                </div>
              )}
              
              <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded-full text-sm">
                {remoteUser?.name || 'Remote User'}
              </div>
            </div>

            {/* Local Video */}
            <div className="relative bg-gray-900 rounded-xl overflow-hidden">
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
              
              <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded-full text-sm">
                You ({user.full_name})
              </div>
              
              {!isVideoEnabled && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
                  <VideoOff className="w-16 h-16 text-gray-400" />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2">
        <div className="flex items-center space-x-4 bg-white shadow-xl rounded-full p-4">
          
          {/* Audio Toggle */}
          <button
            onClick={toggleAudio}
            className={`p-4 rounded-full transition-colors ${
              isAudioEnabled 
                ? 'bg-gray-100 hover:bg-gray-200 text-gray-700' 
                : 'bg-red-500 hover:bg-red-600 text-white'
            }`}
            title={isAudioEnabled ? 'Mute Microphone' : 'Unmute Microphone'}
          >
            {isAudioEnabled ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
          </button>

          {/* Video Toggle */}
          <button
            onClick={toggleVideo}
            className={`p-4 rounded-full transition-colors ${
              isVideoEnabled 
                ? 'bg-gray-100 hover:bg-gray-200 text-gray-700' 
                : 'bg-red-500 hover:bg-red-600 text-white'
            }`}
            title={isVideoEnabled ? 'Turn Off Camera' : 'Turn On Camera'}
          >
            {isVideoEnabled ? <Video className="w-6 h-6" /> : <VideoOff className="w-6 h-6" />}
          </button>

          {/* End Call */}
          <button
            onClick={endCall}
            className="p-4 rounded-full bg-red-500 hover:bg-red-600 text-white transition-colors"
            title="End Call"
          >
            <PhoneOff className="w-6 h-6" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoCall;