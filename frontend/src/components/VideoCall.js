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
      alert(`Connection failed: ${error.message}. Please try again.`);
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
      const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws/video-call/${sessionToken}`;
      
      console.log('🔗 Connecting to signaling server...');
      const socket = new WebSocket(wsUrl);
      signalingSocketRef.current = socket;

      socket.onopen = () => {
        console.log('✅ Signaling connected');
        
        // Join the call
        socket.send(JSON.stringify({
          type: 'join',
          sessionToken: sessionToken,
          userId: user.id,
          userName: user.full_name
        }));
        
        resolve();
      };

      socket.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        console.log('📨 Received:', message.type);
        
        await handleSignalingMessage(message);
      };

      socket.onerror = (error) => {
        console.error('❌ Signaling error:', error);
        reject(error);
      };

      socket.onclose = () => {
        console.log('🔌 Signaling disconnected');
      };
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
    console.log('📞 Ending call...');
    cleanup();
    
    try {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      await axios.post(`${BACKEND_URL}/api/video-call/end/${sessionToken}`);
    } catch (error) {
      console.error('Error ending call:', error);
    }
    
    navigate('/');
  };

  const cleanup = () => {
    console.log('🧹 Cleaning up call...');
    
    try {
      // Stop ALL local media tracks immediately
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach(track => {
          console.log(`🔴 Stopping ${track.kind} track: ${track.label}`);
          track.stop();
        });
        localStreamRef.current = null;
      }

      // Clear local video element
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = null;
        console.log('📹 Local video cleared');
      }

      // Clear remote video element
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null;
        console.log('📹 Remote video cleared');
      }

      // Close peer connection
      if (peerConnectionRef.current) {
        // Remove all tracks from peer connection first
        peerConnectionRef.current.getSenders().forEach(sender => {
          if (sender.track) {
            sender.track.stop();
          }
        });
        
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
        console.log('🔌 Peer connection closed');
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

      // Reset state
      setCallStatus('ended');
      setRemoteUser(null);
      setConnectionQuality('disconnected');
      
      console.log('✅ Cleanup completed - camera and microphone released');
      
    } catch (error) {
      console.error('❌ Error during cleanup:', error);
    }
  };

  // Enhanced cleanup on component unmount and page events
  useEffect(() => {
    const handleBeforeUnload = (event) => {
      cleanup();
    };

    const handleVisibilityChange = () => {
      if (document.hidden && callStatus === 'connected') {
        console.log('⚠️ Tab hidden during call - maintaining connection');
      }
    };

    const handleWindowClose = () => {
      cleanup();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('unload', handleWindowClose);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('unload', handleWindowClose);
      cleanup();
    };
  }, [callStatus]);

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