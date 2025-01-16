import React, { useEffect, useRef, useState } from 'react';
import { Box, Typography, Button, Paper, CircularProgress } from '@mui/material';
import axios from 'axios';

function StreamVideo() {
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const [streaming, setStreaming] = useState(false);
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);
    const recordingIntervalRef = useRef(null);
    const [currentVideoId, setCurrentVideoId] = useState(null);

    const startStream = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                streamRef.current = stream;
                setStreaming(true);
                startRecordingCycle();
            }
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    };

    const stopStream = () => {
        if (recordingIntervalRef.current) {
            clearInterval(recordingIntervalRef.current);
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        setStreaming(false);
        setLogs([]);
        setCurrentVideoId(null);
    };

    const startRecordingCycle = () => {
        recordingIntervalRef.current = setInterval(async () => {
            if (!streamRef.current) return;

            try {
                const videoBlob = await recordVideoChunk();
                await processVideoChunk(videoBlob);
            } catch (error) {
                console.error('Error in recording cycle:', error);
            }
        }, 10000); // Record every 10 seconds
    };

    const recordVideoChunk = () => {
        return new Promise((resolve, reject) => {
            const mediaRecorder = new MediaRecorder(streamRef.current);
            const chunks = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunks.push(e.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, { type: 'video/webm' });
                resolve(blob);
            };

            mediaRecorder.onerror = (error) => {
                reject(error);
            };

            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 10000);
        });
    };

    const processVideoChunk = async (videoBlob) => {
        setLoading(true);
        try {
            // Create FormData and upload video
            const formData = new FormData();
            formData.append('video', videoBlob, 'stream.webm');
            formData.append('title', 'stream_title');
            formData.append('description', 'stream_description');

            // Upload video
            const uploadResponse = await axios.post(
                'http://localhost:8000/api/videos/',
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                }
            );

            const videoId = uploadResponse.data.id;
            setCurrentVideoId(videoId);

            // Analyze the uploaded video
            const analysisResponse = await axios.post(
                `http://localhost:8000/api/videos/${videoId}/analyze_stream/`
            );

            // Add new log
            setLogs(prevLogs => [...prevLogs, analysisResponse.data]);

        } catch (error) {
            console.error('Error processing video chunk:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        return () => {
            stopStream();
        };
    }, []);

    return (
        <Box sx={{ mt: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
                <Typography variant="h4" gutterBottom>
                    Live Stream
                </Typography>
                <video
                    ref={videoRef}
                    autoPlay
                    style={{
                        maxWidth: '100%',
                        marginBottom: '1rem',
                        border: '1px solid #ccc',
                        borderRadius: '4px'
                    }}
                />
                <Box sx={{ mt: 2 }}>
                    <Button
                        variant="contained"
                        onClick={streaming ? stopStream : startStream}
                        sx={{ mr: 2 }}
                        disabled={loading}
                    >
                        {streaming ? 'Stop Stream' : 'Start Stream'}
                    </Button>
                    {loading && (
                        <CircularProgress
                            size={24}
                            sx={{ ml: 2, verticalAlign: 'middle' }}
                        />
                    )}
                </Box>
            </Box>

            {/* Analysis Logs */}
            <Box sx={{ mt: 4 }}>
                <Typography variant="h5" gutterBottom>
                    Stream Analysis Logs
                </Typography>
                <Box
                    sx={{
                        maxHeight: '400px',
                        overflow: 'auto',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        p: 2
                    }}
                >
                    {logs.map((log, index) => (
                        <Paper
                            key={index}
                            sx={{
                                p: 2,
                                mb: 1,
                                backgroundColor: '#f5f5f5',
                                '&:hover': { backgroundColor: '#e0e0e0' }
                            }}
                        >
                            <Typography variant="body2" color="textSecondary">
                                {new Date(log.timestamp).toLocaleString()}
                            </Typography>
                            <Typography variant="body1">
                                {log.analysis?.choices?.[0]?.message?.content || 'No content'}
                            </Typography>
                        </Paper>
                    ))}
                    {logs.length === 0 && (
                        <Typography variant="body2" color="textSecondary" textAlign="center">
                            No analysis logs yet. Start streaming to see analysis results.
                        </Typography>
                    )}
                </Box>
            </Box>
        </Box>
    );
}

export default StreamVideo;