import React, { useState, useRef } from 'react';
import { Upload, X, FileAudio, FileText, CheckCircle, Loader2 } from 'lucide-react';
import axios from 'axios';

interface UploadModalProps {
  onClose: () => void;
  onUploadComplete: (meetingId: string) => void;
}

const UploadModal: React.FC<UploadModalProps> = ({ onClose, onUploadComplete }) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState<'upload' | 'processing' | 'done'>('upload');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setStep('upload');

    // Simulate upload progress
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setStep('processing');
          return 100;
        }
        return prev + 10;
      });
    }, 300);

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Call actual backend
      const response = await axios.post('http://localhost:8000/api/meetings/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // Simulate some processing time for transcription/agent
      setTimeout(() => {
        setStep('done');
        setIsUploading(false);
        setTimeout(() => {
          onUploadComplete(response.data.meeting_id);
        }, 1500);
      }, 3000);

    } catch (error) {
      console.error('Upload failed:', error);
      setIsUploading(false);
      clearInterval(interval);
      alert('Upload failed. Is the backend running?');
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(8px)'
    }}>
      <div className="glass card animate-fade-in" style={{ width: '500px', padding: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h2>Upload Meeting</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={24} />
          </button>
        </div>

        {step === 'upload' && !isUploading && (
          <div 
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '2px dashed var(--border)',
              borderRadius: '16px',
              padding: '3rem 2rem',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              background: 'rgba(255, 255, 255, 0.02)'
            }}
            onMouseOver={(e) => e.currentTarget.style.borderColor = 'var(--primary)'}
            onMouseOut={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileChange}
              accept="audio/*,video/*,.pdf"
            />
            <Upload size={48} color="var(--primary)" style={{ marginBottom: '1rem' }} />
            <p style={{ fontWeight: 500, marginBottom: '0.5rem' }}>
              {file ? file.name : "Click or drag files to upload"}
            </p>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Supports Audio, Video, and PDFs
            </p>
          </div>
        )}

        {(isUploading || step === 'processing') && (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <div style={{ position: 'relative', display: 'inline-block', marginBottom: '1.5rem' }}>
              <Loader2 size={64} color="var(--primary)" className="animate-spin" style={{ animation: 'spin 2s linear infinite' }} />
              <div style={{ 
                position: 'absolute', 
                top: '50%', 
                left: '50%', 
                transform: 'translate(-50%, -50%)',
                fontSize: '0.75rem',
                fontWeight: 700
              }}>
                {progress}%
              </div>
            </div>
            <h3>{step === 'upload' ? 'Uploading files...' : 'ActionPilot is analyzing...'}</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
              {step === 'upload' ? "Sending meeting context to Vultr..." : "Extracting decisions and action items with Gemini..."}
            </p>
          </div>
        )}

        {step === 'done' && (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <CheckCircle size={64} color="var(--success)" style={{ marginBottom: '1.5rem' }} />
            <h3>Processing Complete</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.5rem' }}>
              Redirecting to workspace...
            </p>
          </div>
        )}

        <div style={{ display: 'flex', gap: '1rem', marginTop: '2.5rem' }}>
          <button 
            className="btn" 
            style={{ flex: 1, background: 'var(--surface-light)' }}
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            className="btn btn-primary" 
            style={{ flex: 2 }}
            disabled={!file || isUploading}
            onClick={handleUpload}
          >
            {isUploading ? "Processing..." : "Start Agent Analysis"}
          </button>
        </div>
      </div>
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin {
          animation: spin 1.5s linear infinite;
        }
      `}</style>
    </div>
  );
};

export default UploadModal;
