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
    initializeVideoCall();
    return () => {
      cleanupCall();
    };
  }, [sessionToken]);

  const initializeVideoCall = async () => {
    try {
      console.log('🎤📹 Starting video call initialization...');
      
      // STEP 1: Get user media FIRST
      let mediaStream = null;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 }
          },
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });

        console.log('✅ User media obtained successfully');
        console.log('   Video tracks:', mediaStream.getVideoTracks().length);
        console.log('   Audio tracks:', mediaStream.getAudioTracks().length);

        localStreamRef.current = mediaStream;
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = mediaStream;
          localVideoRef.current.muted = true; // Prevent echo
        }

      } catch (mediaError) {
        console.warn('⚠️ Could not get user media:', mediaError.message);
        // Continue without media - still allow joining calls
      }

      // STEP 2: Setup peer connection WITH media stream
      await setupPeerConnection(mediaStream);
      
      // STEP 3: Setup signaling AFTER peer connection is ready
      await setupSignaling();
      
      setCallStatus('connected');
      console.log('✅ Video call initialization complete');
      
    } catch (error) {
      console.error('❌ Error initializing video call:', error);
      alert('Error initializing video call. Please try again.');
      navigate('/');
    }
  };

  const setupSignaling = async () => {
    return new Promise((resolve, reject) => {
      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws/video-call/${sessionToken}`;
      
      console.log('🔗 Connecting to video call WebSocket:', wsUrl);
      const socket = new WebSocket(wsUrl);
      setSignalingSocket(socket);
      
      socket.onopen = () => {
        console.log('✅ Signaling WebSocket connected');
        
        // Enable ICE processing now that signaling is ready
        if (peerConnectionRef.current && peerConnectionRef.current.enableIceProcessing) {
          peerConnectionRef.current.enableIceProcessing();
        }
        
        // Join the video call session
        const joinMessage = {
          type: 'join',
          sessionToken: sessionToken,
          userId: user.id,
          userName: user.full_name
        };
        console.log('📤 Sending join message:', joinMessage);
        socket.send(JSON.stringify(joinMessage));
        
        resolve(socket);
      };
      
      socket.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        console.log('📥 Received signaling message:', message.type);
        
        if (!peerConnectionRef.current) {
          console.error('❌ No peer connection available for signaling');
          return;
        }
        
        switch (message.type) {
          case 'joined':
            console.log('✅ Successfully joined video call session');
            break;
            
          case 'user-joined':
            console.log('👤 Remote user joined:', message.userName);
            setRemoteUser({ name: message.userName });
            
            // Create offer with media tracks
            if (localStreamRef.current && localStreamRef.current.getTracks().length > 0) {
              try {
                console.log('📞 Creating offer with media tracks...');
                const offer = await peerConnectionRef.current.createOffer({
                  offerToReceiveAudio: true,
                  offerToReceiveVideo: true
                });
                
                await peerConnectionRef.current.setLocalDescription(offer);
                console.log('📤 Sending offer to remote user');
                
                socket.send(JSON.stringify({
                  type: 'offer',
                  offer: offer,
                  target: message.userId
                }));
              } catch (error) {
                console.error('❌ Error creating offer:', error);
              }
            } else {
              console.warn('⚠️ No local media tracks available for offer');
            }
            break;
            
          case 'offer':
            console.log('📞 Received offer from remote user');
            try {
              await peerConnectionRef.current.setRemoteDescription(message.offer);
              console.log('✅ Remote description set from offer');
              
              const answer = await peerConnectionRef.current.createAnswer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: true
              });
              
              await peerConnectionRef.current.setLocalDescription(answer);
              console.log('📤 Sending answer to remote user');
              
              socket.send(JSON.stringify({
                type: 'answer',
                answer: answer,
                target: message.from
              }));
            } catch (error) {
              console.error('❌ Error handling offer:', error);
            }
            break;
            
          case 'answer':
            console.log('📞 Received answer from remote user');
            try {
              await peerConnectionRef.current.setRemoteDescription(message.answer);
              console.log('✅ Remote description set from answer');
            } catch (error) {
              console.error('❌ Error handling answer:', error);
            }
            break;
            
          case 'ice-candidate':
            console.log('🧊 Received ICE candidate');
            if (message.candidate) {
              try {
                await peerConnectionRef.current.addIceCandidate(message.candidate);
                console.log('✅ ICE candidate added successfully');
              } catch (error) {
                console.error('❌ Error adding ICE candidate:', error);
              }
            }
            break;
            
          case 'user-left':
            console.log('👋 Remote user left the call');
            setRemoteUser(null);
            if (remoteVideoRef.current) {
              remoteVideoRef.current.srcObject = null;
            }
            break;
        }
      };
      
      socket.onclose = () => {
        console.log('🔌 Signaling WebSocket disconnected');
      };
      
      socket.onerror = (error) => {
        console.error('❌ Signaling WebSocket error:', error);
        reject(error);
      };
      
      // Timeout after 10 seconds
      setTimeout(() => {
        if (socket.readyState !== WebSocket.OPEN) {
          reject(new Error('WebSocket connection timeout'));
        }
      }, 10000);
    });
  };

  const setupPeerConnection = async (mediaStream) => {
    console.log('🔗 Setting up WebRTC peer connection...');
    
    const config = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'stun:stun2.l.google.com:19302' },
        { urls: 'stun:stun3.l.google.com:19302' },
        { urls: 'stun:stun4.l.google.com:19302' }
      ],
      iceCandidatePoolSize: 10,
      bundlePolicy: 'max-bundle',
      rtcpMuxPolicy: 'require'
    };

    const peerConnection = new RTCPeerConnection(config);
    peerConnectionRef.current = peerConnection;

    // Add media tracks FIRST - this is critical for proper media exchange
    if (mediaStream) {
      const audioTracks = mediaStream.getAudioTracks();
      const videoTracks = mediaStream.getVideoTracks();
      
      console.log(`📹 Adding ${videoTracks.length} video tracks and ${audioTracks.length} audio tracks`);
      
      // Add each track individually with proper labeling
      audioTracks.forEach((track, index) => {
        console.log(`🎤 Adding audio track ${index + 1}: ${track.label}`);
        const sender = peerConnection.addTrack(track, mediaStream);
        console.log(`✅ Audio sender added:`, sender);
      });
      
      videoTracks.forEach((track, index) => {
        console.log(`📹 Adding video track ${index + 1}: ${track.label}`);
        const sender = peerConnection.addTrack(track, mediaStream);
        console.log(`✅ Video sender added:`, sender);
      });
      
      console.log('✅ All local media tracks added to peer connection');
    } else {
      console.warn('⚠️ No media stream available - peer connection created without local media');
    }

    // Enhanced remote stream handling
    peerConnection.ontrack = (event) => {
      console.log('🎥 RECEIVED REMOTE TRACK:', event.track.kind, event.track.label);
      console.log('   Track enabled:', event.track.enabled);
      console.log('   Track muted:', event.track.muted);
      console.log('   Track ready state:', event.track.readyState);
      console.log('   Number of streams:', event.streams.length);
      
      if (event.streams && event.streams[0]) {
        const remoteStream = event.streams[0];
        console.log('✅ Remote stream received with', remoteStream.getTracks().length, 'tracks');
        
        // Log each track in the remote stream
        remoteStream.getTracks().forEach((track, index) => {
          console.log(`   Remote ${track.kind} track ${index + 1}:`, track.label, 'enabled:', track.enabled);
        });
        
        // Set remote stream to video element
        if (remoteVideoRef.current) {
          remoteVideoRef.current.srcObject = remoteStream;
          remoteStreamRef.current = remoteStream;
          
          // Force play the remote video
          remoteVideoRef.current.play().then(() => {
            console.log('✅ Remote video playing successfully');
          }).catch(error => {
            console.log('⚠️ Remote video autoplay blocked:', error.message);
          });
          
          setRemoteUser({ name: 'Connected User' });
          console.log('🎉 REMOTE MEDIA STREAM CONNECTED SUCCESSFULLY!');
        }
      } else {
        console.error('❌ No remote stream in track event');
      }
    };

    // Store ICE candidates until both sides are ready
    const iceQueue = [];
    let canProcessIce = false;
    
    peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('🧊 Generated ICE candidate:', event.candidate.type);
        
        if (canProcessIce && signalingSocket && signalingSocket.readyState === WebSocket.OPEN) {
          console.log('📤 Sending ICE candidate immediately');
          signalingSocket.send(JSON.stringify({
            type: 'ice-candidate',
            candidate: event.candidate
          }));
        } else {
          console.log('📦 Queuing ICE candidate');
          iceQueue.push(event.candidate);
        }
      } else {
        console.log('🧊 ICE gathering complete');
      }
    };

    // Function to enable ICE processing and send queued candidates
    peerConnection.enableIceProcessing = () => {
      canProcessIce = true;
      console.log(`📤 Processing ${iceQueue.length} queued ICE candidates`);
      while (iceQueue.length > 0) {
        const candidate = iceQueue.shift();
        if (signalingSocket && signalingSocket.readyState === WebSocket.OPEN) {
          signalingSocket.send(JSON.stringify({
            type: 'ice-candidate',
            candidate: candidate
          }));
        }
      }
    };

    // Enhanced connection monitoring
    peerConnection.onconnectionstatechange = () => {
      const state = peerConnection.connectionState;
      console.log('🔄 WebRTC connection state:', state);
      
      switch (state) {
        case 'connected':
          console.log('🎉 WebRTC PEER CONNECTION ESTABLISHED - MEDIA SHOULD FLOW!');
          setCallStatus('connected');
          break;
        case 'connecting':
          console.log('🔄 WebRTC establishing connection...');
          setCallStatus('connecting');
          break;
        case 'disconnected':
          console.log('⚠️ WebRTC connection lost');
          setCallStatus('connecting');
          break;
        case 'failed':
          console.log('❌ WebRTC connection failed');
          setCallStatus('connecting');
          break;
        case 'closed':
          console.log('🔒 WebRTC connection closed');
          break;
      }
    };

    // ICE connection monitoring
    peerConnection.oniceconnectionstatechange = () => {
      const iceState = peerConnection.iceConnectionState;
      console.log('🧊 ICE connection state:', iceState);
      
      switch (iceState) {
        case 'connected':
        case 'completed':
          console.log('🎉 ICE CONNECTION SUCCESS - AUDIO/VIDEO SHOULD WORK NOW!');
          break;
        case 'checking':
          console.log('🔍 ICE checking connectivity...');
          break;
        case 'disconnected':
          console.log('⚠️ ICE connection disconnected');
          break;
        case 'failed':
          console.log('❌ ICE connection failed');
          break;
      }
    };

    console.log('✅ WebRTC peer connection fully configured');
    return peerConnection;
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