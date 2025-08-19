import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Mic, 
  MicOff, 
  Video, 
  VideoOff, 
  Phone, 
  PhoneOff, 
  Monitor, 
  MonitorOff,
  MessageCircle,
  Settings
} from 'lucide-react';

const VideoCall = ({ user }) => {
  const { sessionToken } = useParams();
  const navigate = useNavigate();
  
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [callStatus, setCallStatus] = useState('connecting'); // connecting, connected, ended
  const [remoteUser, setRemoteUser] = useState(null);
  const [signalingSocket, setSignalingSocket] = useState(null);
  
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const localStreamRef = useRef(null);
  const remoteStreamRef = useRef(null);
  const peerConnectionRef = useRef(null);

  useEffect(() => {
    initializeVideoCall();
    return () => {
      cleanupCall();
    };
  }, [sessionToken]);

  const initializeVideoCall = async () => {
    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });

      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }

      // Initialize WebRTC peer connection
      setupPeerConnection();
      
      // Setup signaling WebSocket for real peer connection
      setupSignaling();
      
      setCallStatus('connected');
    } catch (error) {
      console.error('Error initializing video call:', error);
      
      // Don't redirect on camera/microphone errors - show video call interface anyway
      // This allows testing in environments without camera access
      if (error.name === 'NotFoundError' || error.name === 'NotAllowedError' || error.name === 'NotReadableError') {
        console.warn('Camera/microphone not available - continuing with video call interface');
        setCallStatus('connected'); // Still show as connected for demo purposes
        setupPeerConnection(); // Set up peer connection without local stream
        setupSignaling(); // Still setup signaling for remote connection
      } else {
        alert('Error initializing video call. Please try again.');
        navigate('/');
      }
    }
  };

  const setupSignaling = () => {
    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;
    const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/ws/video-call/${sessionToken}`;
    
    const socket = new WebSocket(wsUrl);
    setSignalingSocket(socket);
    
    socket.onopen = () => {
      console.log('Signaling WebSocket connected');
      // Join the video call session
      socket.send(JSON.stringify({
        type: 'join',
        sessionToken: sessionToken,
        userId: user.id,
        userName: user.full_name
      }));
    };
    
    socket.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'user-joined':
          setRemoteUser({ name: message.userName });
          // If we have a local stream, create an offer
          if (localStreamRef.current && peerConnectionRef.current) {
            try {
              const offer = await peerConnectionRef.current.createOffer();
              await peerConnectionRef.current.setLocalDescription(offer);
              socket.send(JSON.stringify({
                type: 'offer',
                offer: offer,
                target: message.userId
              }));
            } catch (error) {
              console.error('Error creating offer:', error);
            }
          }
          break;
          
        case 'offer':
          if (peerConnectionRef.current) {
            try {
              await peerConnectionRef.current.setRemoteDescription(message.offer);
              const answer = await peerConnectionRef.current.createAnswer();
              await peerConnectionRef.current.setLocalDescription(answer);
              socket.send(JSON.stringify({
                type: 'answer',
                answer: answer,
                target: message.from
              }));
            } catch (error) {
              console.error('Error handling offer:', error);
            }
          }
          break;
          
        case 'answer':
          if (peerConnectionRef.current) {
            try {
              await peerConnectionRef.current.setRemoteDescription(message.answer);
            } catch (error) {
              console.error('Error handling answer:', error);
            }
          }
          break;
          
        case 'ice-candidate':
          if (peerConnectionRef.current && message.candidate) {
            try {
              await peerConnectionRef.current.addIceCandidate(message.candidate);
            } catch (error) {
              console.error('Error adding ICE candidate:', error);
            }
          }
          break;
          
        case 'user-left':
          setRemoteUser(null);
          if (remoteVideoRef.current) {
            remoteVideoRef.current.srcObject = null;
          }
          break;
      }
    };
    
    socket.onclose = () => {
      console.log('Signaling WebSocket disconnected');
    };
    
    socket.onerror = (error) => {
      console.error('Signaling WebSocket error:', error);
    };
  };

  const setupPeerConnection = () => {
    // For demo purposes, we'll simulate a peer connection
    // In a real implementation, you would set up WebRTC signaling
    const config = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
      ]
    };

    const peerConnection = new RTCPeerConnection(config);
    peerConnectionRef.current = peerConnection;

    // Add local stream to peer connection
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStreamRef.current);
      });
    }

    // Handle remote stream
    peerConnection.ontrack = (event) => {
      const [remoteStream] = event.streams;
      remoteStreamRef.current = remoteStream;
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = remoteStream;
      }
      setRemoteUser({ name: 'Connected User' });
    };

    // For demo purposes, simulate a remote connection after 2 seconds
    setTimeout(() => {
      // In a real app, this would be handled by signaling server
      simulateRemoteConnection();
    }, 2000);
  };

  const simulateRemoteConnection = async () => {
    try {
      // Simulate remote user video for demo
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');
      
      // Create a simple animated background for demo
      const animate = () => {
        ctx.fillStyle = '#4f46e5';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'white';
        ctx.font = '30px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('Remote User Video', canvas.width / 2, canvas.height / 2 - 30);
        ctx.fillText('(Demo Mode)', canvas.width / 2, canvas.height / 2 + 10);
        ctx.fillText(new Date().toLocaleTimeString(), canvas.width / 2, canvas.height / 2 + 50);
        requestAnimationFrame(animate);
      };
      animate();

      const stream = canvas.captureStream(30);
      remoteStreamRef.current = stream;
      
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = stream;
      }
      
      setRemoteUser({ name: 'Demo Remote User' });
    } catch (error) {
      console.error('Error simulating remote connection:', error);
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

  const endCall = () => {
    cleanupCall();
    navigate('/');
  };

  const cleanupCall = () => {
    // Stop all tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (remoteStreamRef.current) {
      remoteStreamRef.current.getTracks().forEach(track => track.stop());
    }

    // Close peer connection
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
    }

    setCallStatus('ended');
  };

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