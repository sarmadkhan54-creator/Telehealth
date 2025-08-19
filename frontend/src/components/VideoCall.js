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
      
      // Step 1: Get user media
      await getUserMedia();
      
      // Step 2: Setup WebRTC peer connection
      setupPeerConnection();
      
      // Step 3: Connect to signaling server
      await connectSignaling();
      
      setCallStatus('connecting');
      
    } catch (error) {
      console.error('❌ Failed to initialize call:', error);
      setCallStatus('failed');
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

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsVideoEnabled(videoTrack.enabled);
      }
    }
  };

  const toggleAudio = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsAudioEnabled(audioTrack.enabled);
      }
    }
  };

  const toggleScreenShare = async () => {
    try {
      if (!isScreenSharing) {
        // Start screen sharing
        const screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true
        });

        // Replace video track in peer connection
        if (peerConnectionRef.current && localStreamRef.current) {
          const sender = peerConnectionRef.current.getSenders().find(s => 
            s.track && s.track.kind === 'video'
          );
          if (sender) {
            await sender.replaceTrack(screenStream.getVideoTracks()[0]);
          }
        }

        // Update local video display
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = screenStream;
        }

        setIsScreenSharing(true);

        // Handle screen share end
        screenStream.getVideoTracks()[0].addEventListener('ended', () => {
          stopScreenShare();
        });
      } else {
        stopScreenShare();
      }
    } catch (error) {
      console.error('Error toggling screen share:', error);
    }
  };

  const stopScreenShare = async () => {
    try {
      // Get camera stream back
      const cameraStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });

      // Replace track back to camera
      if (peerConnectionRef.current) {
        const sender = peerConnectionRef.current.getSenders().find(s => 
          s.track && s.track.kind === 'video'
        );
        if (sender) {
          await sender.replaceTrack(cameraStream.getVideoTracks()[0]);
        }
      }

      // Update local stream reference
      localStreamRef.current = cameraStream;

      // Update local video display
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = cameraStream;
      }

      setIsScreenSharing(false);
    } catch (error) {
      console.error('Error stopping screen share:', error);
    }
  };

  const endCall = async () => {
    try {
      // End the video call session on the backend
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      await axios.post(`${BACKEND_URL}/api/video-call/end/${sessionToken}`);
      console.log('✅ Video call session ended on backend');
    } catch (error) {
      console.error('❌ Error ending video call session:', error);
    }
    
    cleanupCall();
    navigate('/');
  };

  const cleanupCall = () => {
    console.log('🧹 Cleaning up video call...');
    
    // Stop all local tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => {
        track.stop();
        console.log(`Stopped ${track.kind} track`);
      });
      localStreamRef.current = null;
    }
    
    if (remoteStreamRef.current) {
      remoteStreamRef.current.getTracks().forEach(track => track.stop());
      remoteStreamRef.current = null;
    }

    // Close peer connection
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
      console.log('WebRTC peer connection closed');
    }

    // Close signaling socket
    if (signalingSocket) {
      if (signalingSocket.readyState === WebSocket.OPEN) {
        signalingSocket.send(JSON.stringify({
          type: 'leave',
          sessionToken: sessionToken
        }));
      }
      signalingSocket.close();
      setSignalingSocket(null);
      console.log('WebSocket signaling connection closed');
    }

    // Clear video elements
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
    if (remoteVideoRef.current) {
      remoteVideoRef.current.srcObject = null;
    }

    setCallStatus('ended');
    setRemoteUser(null);
    console.log('✅ Video call cleanup complete');
  };

  // Cleanup on component unmount or page refresh
  useEffect(() => {
    const handleBeforeUnload = () => {
      cleanupCall();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      cleanupCall();
    };
  }, [sessionToken]);

  return (
    <div className="video-container">
      {/* Call Status Indicator */}
      <div className="absolute top-4 left-4 z-10">
        <div className="glass-card p-3">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${
              callStatus === 'connected' ? 'bg-green-500' : 
              callStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' : 
              'bg-red-500'
            }`}></div>
            <span className="text-white font-medium capitalize">
              {callStatus}
            </span>
            {callStatus === 'connected' && (
              <span className="text-gray-300 text-sm ml-2">
                Session: {sessionToken?.slice(-8)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* User Info */}
      <div className="absolute top-4 right-4 z-10">
        <div className="glass-card p-3">
          <div className="text-right">
            <p className="text-white font-medium">{user.full_name}</p>
            <p className="text-gray-300 text-sm">
              {user.role === 'doctor' ? 'Doctor' : 'Provider'}
            </p>
          </div>
        </div>
      </div>

      {/* Remote Video (Main) */}
      <div className="relative w-full h-full">
        {remoteUser ? (
          <video
            ref={remoteVideoRef}
            autoPlay
            playsInline
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full bg-gray-800">
            <div className="text-center">
              <div className="w-24 h-24 bg-gray-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Video className="w-12 h-12 text-gray-400" />
              </div>
              <p className="text-white text-xl mb-2">Waiting for remote participant...</p>
              <p className="text-gray-300">They will appear here once connected</p>
            </div>
          </div>
        )}

        {/* Local Video (Picture in Picture) */}
        <div className="absolute bottom-20 right-4 w-64 h-48 bg-gray-900 rounded-lg overflow-hidden border-2 border-white/20">
          <video
            ref={localVideoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
          {!isVideoEnabled && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
              <VideoOff className="w-8 h-8 text-gray-400" />
            </div>
          )}
          <div className="absolute bottom-2 left-2">
            <span className="text-white text-sm font-medium">You</span>
          </div>
        </div>
      </div>

      {/* Call Controls */}
      <div className="video-controls">
        <div className="flex items-center space-x-4">
          {/* Audio Toggle */}
          <button
            onClick={toggleAudio}
            className={`control-btn ${isAudioEnabled ? 'mute' : 'bg-red-500'}`}
            title={isAudioEnabled ? 'Mute' : 'Unmute'}
          >
            {isAudioEnabled ? <Mic /> : <MicOff />}
          </button>

          {/* Video Toggle */}
          <button
            onClick={toggleVideo}
            className={`control-btn ${isVideoEnabled ? 'mute' : 'bg-red-500'}`}
            title={isVideoEnabled ? 'Turn off camera' : 'Turn on camera'}
          >
            {isVideoEnabled ? <Video /> : <VideoOff />}
          </button>

          {/* Screen Share */}
          <button
            onClick={toggleScreenShare}
            className={`control-btn ${isScreenSharing ? 'bg-blue-500' : 'mute'}`}
            title={isScreenSharing ? 'Stop sharing' : 'Share screen'}
          >
            {isScreenSharing ? <MonitorOff /> : <Monitor />}
          </button>

          {/* Chat (Future feature) */}
          <button
            className="control-btn mute"
            title="Chat (Coming soon)"
            disabled
          >
            <MessageCircle />
          </button>

          {/* Settings (Future feature) */}
          <button
            className="control-btn mute"
            title="Settings (Coming soon)"
            disabled
          >
            <Settings />
          </button>

          {/* End Call */}
          <button
            onClick={endCall}
            className="control-btn end-call"
            title="End call"
          >
            <PhoneOff />
          </button>
        </div>
      </div>

      {/* Connection Quality Indicator */}
      <div className="absolute bottom-4 left-4 z-10">
        <div className="glass-card p-2">
          <div className="flex items-center space-x-2">
            <div className="flex space-x-1">
              <div className="w-1 h-4 bg-green-500 rounded"></div>
              <div className="w-1 h-3 bg-green-500 rounded"></div>
              <div className="w-1 h-2 bg-green-500 rounded"></div>
              <div className="w-1 h-3 bg-green-500 rounded"></div>
            </div>
            <span className="text-white text-sm">Good connection</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoCall;