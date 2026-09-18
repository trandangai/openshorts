import React, { useState, useEffect, useRef } from 'react';
import {
  Scissors,
  Upload,
  Link2,
  Play,
  Download,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Zap,
  Film,
  Subtitles,
  FileText,
  Clock,
  RotateCcw,
  Mic,
  Volume2,
  VolumeX,
  Check,
  Search,
  Globe,
} from 'lucide-react';
import { getApiUrl } from '../config';

export default function ShortsCutterTab({ geminiApiKey = '', elevenLabsApiKey = '' }) {
  const [inputType, setInputType] = useState('url'); // 'url' | 'file'
  const [url, setUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Settings
  const [coverageMode, setCoverageMode] = useState('part'); // 'part' | 'full'
  const [reframingMode, setReframingMode] = useState('pillar_blur');
  const [maxClips, setMaxClips] = useState(3);
  const [minDuration, setMinDuration] = useState(15);
  const [maxDuration, setMaxDuration] = useState(60);
  const [burnSubtitles, setBurnSubtitles] = useState(true);
  const [whisperModel, setWhisperModel] = useState('base');
  const [language, setLanguage] = useState('auto'); // 'auto' | 'en' | 'es' | 'fr' | etc.
  const [translateToEnglish, setTranslateToEnglish] = useState(false);
  const [kidsStorytellingMode, setKidsStorytellingMode] = useState(false);
  const [customGeminiKey, setCustomGeminiKey] = useState(geminiApiKey || '');

  // ElevenLabs Voiceover Settings
  const [enableVoiceover, setEnableVoiceover] = useState(false);
  const [selectedVoiceId, setSelectedVoiceId] = useState('21m00Tcm4TlvDq8ikWAM'); // Rachel default
  const [customElevenLabsKey, setCustomElevenLabsKey] = useState(
    () => elevenLabsApiKey || localStorage.getItem('elevenLabsKey_v1') || ''
  );
  const [voiceCategoryFilter, setVoiceCategoryFilter] = useState('all'); // 'all' | 'female' | 'male' | 'custom'
  const [voiceSearchQuery, setVoiceSearchQuery] = useState('');
  const [voices, setVoices] = useState([
    {
      voice_id: '21m00Tcm4TlvDq8ikWAM',
      name: 'Rachel',
      category: 'premade',
      labels: { gender: 'female', accent: 'american', description: 'calm & natural' },
      preview_url: 'https://storage.googleapis.com/eleven-public-prod/premade/voices/21m00Tcm4TlvDq8ikWAM/df6788f9-1965-4d70-b790-b33f395f6f3d.mp3',
    },
    {
      voice_id: '29vD33N1CtxCmqQRPOHJ',
      name: 'Drew',
      category: 'premade',
      labels: { gender: 'male', accent: 'american', description: 'confident & energetic' },
      preview_url: 'https://storage.googleapis.com/eleven-public-prod/premade/voices/29vD33N1CtxCmqQRPOHJ/e8b52a3f-9732-440f-b78a-16d5d1e8f829.mp3',
    },
    {
      voice_id: 'EXAVITQu4vr4xnSDxMaL',
      name: 'Bella',
      category: 'premade',
      labels: { gender: 'female', accent: 'american', description: 'soft & expressive' },
      preview_url: 'https://storage.googleapis.com/eleven-public-prod/premade/voices/EXAVITQu4vr4xnSDxMaL/04365860-244e-4f51-a9f8-7448d7c86510.mp3',
    },
    {
      voice_id: 'ErXwobaYiN019PkySvjV',
      name: 'Antoni',
      category: 'premade',
      labels: { gender: 'male', accent: 'american', description: 'warm storyteller' },
      preview_url: 'https://storage.googleapis.com/eleven-public-prod/premade/voices/ErXwobaYiN019PkySvjV/38d8f367-73e0-4729-844c-1aa16bc60fb7.mp3',
    },
    {
      voice_id: 'TxGEqnHWrfWFTfGW9XjX',
      name: 'Josh',
      category: 'premade',
      labels: { gender: 'male', accent: 'american', description: 'deep & authoritative' },
      preview_url: 'https://storage.googleapis.com/eleven-public-prod/premade/voices/TxGEqnHWrfWFTfGW9XjX/4859a857-7977-4b78-b118-8be06c7104b2.mp3',
    },
    {
      voice_id: 'yoZ06aMxZJJ28mfd3POQ',
      name: 'Sam',
      category: 'premade',
      labels: { gender: 'male', accent: 'american', description: 'dynamic & raspy' },
      preview_url: 'https://storage.googleapis.com/eleven-public-prod/premade/voices/yoZ06aMxZJJ28mfd3POQ/1c4d417c-3411-426f-8d62-0e5503295013.mp3',
    },
  ]);
  const [playingPreview, setPlayingPreview] = useState(null);
  const audioPreviewRef = useRef(null);

  // Sync elevenLabsApiKey from props if changed
  useEffect(() => {
    if (elevenLabsApiKey && !customElevenLabsKey) {
      setCustomElevenLabsKey(elevenLabsApiKey);
    }
  }, [elevenLabsApiKey]);

  // Job Execution State
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null); // 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  const [jobData, setJobData] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const timerRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fetch available ElevenLabs voices on mount or key change
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const headers = {};
        if (customElevenLabsKey.trim()) {
          headers['X-ElevenLabs-Key'] = customElevenLabsKey.trim();
        }
        const res = await fetch(getApiUrl('/api/shorts-cutter/voices'), { headers });
        if (res.ok) {
          const data = await res.json();
          if (data.voices && data.voices.length > 0) {
            setVoices(data.voices);
          }
        }
      } catch (err) {
        console.warn('Failed to load ElevenLabs voices:', err);
      }
    };
    fetchVoices();
  }, [customElevenLabsKey]);

  // Audio preview toggle
  const handleTogglePreview = (previewUrl) => {
    if (!previewUrl) return;
    if (playingPreview === previewUrl) {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause();
      }
      setPlayingPreview(null);
    } else {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause();
      }
      const audio = new Audio(previewUrl);
      audio.onended = () => setPlayingPreview(null);
      audio.onerror = () => setPlayingPreview(null);
      audio.play().catch(() => setPlayingPreview(null));
      audioPreviewRef.current = audio;
      setPlayingPreview(previewUrl);
    }
  };

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus === 'COMPLETED' || jobStatus === 'FAILED') {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(async () => {
      setElapsed((prev) => prev + 1);
      try {
        const res = await fetch(getApiUrl(`/api/shorts-cutter/jobs/${jobId}`));
        if (!res.ok) return;
        const data = await res.json();
        setJobStatus(data.status);
        setJobData(data);

        if (data.status === 'FAILED') {
          setErrorMsg(data.error || 'Processing failed');
        }
      } catch (err) {
        console.error('Failed to poll status', err);
      }
    }, 2000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [jobId, jobStatus]);

  const handleStartProcess = async () => {
    setErrorMsg(null);
    setJobData(null);
    setElapsed(0);

    let sourcePath = '';

    if (inputType === 'file') {
      if (!selectedFile) {
        setErrorMsg('Please select a video file to upload.');
        return;
      }
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append('file', selectedFile);
        const uploadRes = await fetch(getApiUrl('/api/shorts-cutter/upload'), {
          method: 'POST',
          body: formData,
        });
        if (!uploadRes.ok) {
          const errData = await uploadRes.json().catch(() => ({}));
          throw new Error(errData.detail || 'File upload failed');
        }
        const uploadData = await uploadRes.json();
        sourcePath = uploadData.file_path;
      } catch (err) {
        setUploading(false);
        setErrorMsg(err.message || 'File upload failed');
        return;
      } finally {
        setUploading(false);
      }
    } else {
      if (!url.trim()) {
        setErrorMsg('Please enter a YouTube video URL.');
        return;
      }
      sourcePath = url.trim();
    }

    // Submit processing job
    try {
      setJobStatus('QUEUED');
      const headers = { 'Content-Type': 'application/json' };
      if (customGeminiKey.trim()) {
        headers['X-Gemini-Key'] = customGeminiKey.trim();
      }
      if (enableVoiceover && customElevenLabsKey.trim()) {
        headers['X-ElevenLabs-Key'] = customElevenLabsKey.trim();
      }

      const res = await fetch(getApiUrl('/api/shorts-cutter/process'), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          input_source: sourcePath,
          coverage_mode: coverageMode,
          max_clips: parseInt(maxClips, 10),
          min_clip_duration: parseFloat(minDuration),
          max_clip_duration: parseFloat(maxDuration),
          reframing_mode: reframingMode,
          burn_subtitles: burnSubtitles,
          whisper_model_size: whisperModel,
          language: language !== 'auto' ? language : null,
          translate_to_english: translateToEnglish,
          kids_storytelling_mode: kidsStorytellingMode,
          elevenlabs_voice_id: enableVoiceover ? selectedVoiceId : null,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to queue shorts job');
      }

      const result = await res.json();
      setJobId(result.job_id);
    } catch (err) {
      setJobStatus(null);
      setErrorMsg(err.message || 'Failed to submit job');
    }
  };

  const handleReset = () => {
    setJobId(null);
    setJobStatus(null);
    setJobData(null);
    setErrorMsg(null);
    setElapsed(0);
    setUrl('');
    setSelectedFile(null);
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-4 sm:p-6 md:p-10 animate-fade">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header Banner */}
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="eyebrow flex items-center gap-2 text-accent">
              <Scissors size={14} /> 02B · ZERO-COST VERTICAL SHORTS ENGINE
            </p>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono bg-ok/10 text-ok border border-ok/20">
              <Zap size={11} /> 100% Local / Free API ($0)
            </span>
          </div>

          <h1 className="font-display lowercase text-3xl md:text-4xl text-ink">
            Shorts Cutter v2
          </h1>
          <p className="text-muted text-base leading-relaxed max-w-2xl">
            A standalone, ultra-fast video clipping pipeline. Downloads YouTube videos or accepts local uploads, transcribes with local Whisper, detects viral moments, and renders 1080x1920 vertical shorts with karaoke subtitles.
          </p>
        </div>

        {/* Pipeline In Progress View */}
        {jobStatus && jobStatus !== 'FAILED' && (
          <div className="p-6 rounded-card bg-paper2 border border-rule2 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {jobStatus === 'COMPLETED' ? (
                  <CheckCircle2 size={24} className="text-ok" />
                ) : (
                  <Loader2 size={24} className="text-accent animate-spin" />
                )}
                <div>
                  <h3 className="text-lg font-medium text-ink">
                    {jobStatus === 'COMPLETED' ? 'Shorts Processing Completed!' : 'Generating Your Shorts...'}
                  </h3>
                  <p className="text-xs font-mono text-muted">
                    Job ID: {jobId} · Elapsed: {elapsed}s · Status: {jobStatus}
                  </p>
                </div>
              </div>

              {jobStatus === 'COMPLETED' && (
                <button
                  onClick={handleReset}
                  className="px-3 py-1.5 text-xs rounded-input border border-rule hover:bg-paper3 text-ink2 transition-colors flex items-center gap-1.5"
                >
                  <RotateCcw size={13} /> Process Another
                </button>
              )}
            </div>

            {/* Stages indicator */}
            <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono">
              <div className={`p-2.5 rounded-input border ${elapsed >= 2 ? 'border-ok/30 bg-ok/5 text-ok' : 'border-rule bg-paper text-muted'}`}>
                1. Ingest
              </div>
              <div className={`p-2.5 rounded-input border ${elapsed >= 8 ? 'border-ok/30 bg-ok/5 text-ok' : elapsed >= 2 ? 'border-accent/40 bg-accent/5 text-accent animate-pulse' : 'border-rule bg-paper text-muted'}`}>
                2. Transcribe
              </div>
              <div className={`p-2.5 rounded-input border ${elapsed >= 15 ? 'border-ok/30 bg-ok/5 text-ok' : elapsed >= 8 ? 'border-accent/40 bg-accent/5 text-accent animate-pulse' : 'border-rule bg-paper text-muted'}`}>
                3. AI Moments
              </div>
              <div className={`p-2.5 rounded-input border ${jobStatus === 'COMPLETED' ? 'border-ok/30 bg-ok/5 text-ok' : elapsed >= 15 ? 'border-accent/40 bg-accent/5 text-accent animate-pulse' : 'border-rule bg-paper text-muted'}`}>
                4. 9:16 Render
              </div>
            </div>

            {/* Generated Clips Grid */}
            {jobStatus === 'COMPLETED' && jobData?.clips && (
              <div className="space-y-4 pt-4 border-t border-rule">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-sm font-mono uppercase tracking-wider text-muted flex items-center gap-2">
                    <Film size={14} className="text-accent" /> Generated Vertical Clips ({jobData.clips.length})
                  </h4>
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-paper border border-rule text-ink2 font-mono">
                    Mode: {jobData.coverage_mode === 'full' || coverageMode === 'full' ? '🎬 Full Video Series' : '⚡ Viral Highlights'}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {jobData.clips.map((clip) => {
                    const videoFilename = clip.video_filename || clip.video_path.split('/').pop();
                    const srtFilename = clip.srt_filename || (clip.srt_path ? clip.srt_path.split('/').pop() : null);
                    const videoUrl = clip.download_url
                      ? getApiUrl(clip.download_url)
                      : getApiUrl(`/api/shorts-cutter/jobs/${jobId}/files/${videoFilename}`);
                    const srtUrl = clip.srt_url
                      ? getApiUrl(clip.srt_url)
                      : (srtFilename ? getApiUrl(`/api/shorts-cutter/jobs/${jobId}/files/${srtFilename}`) : null);

                    const isPart = clip.title && clip.title.toLowerCase().startsWith('part ');

                    return (
                      <div key={clip.id} className="p-4 rounded-card bg-paper border border-rule space-y-3">
                        <div className="aspect-[9/16] w-full max-w-[260px] mx-auto bg-black rounded-input overflow-hidden shadow-lg border border-rule relative">
                          <video
                            key={videoUrl}
                            src={videoUrl}
                            controls
                            preload="metadata"
                            playsInline
                            className="w-full h-full object-contain"
                          />
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center justify-between gap-2">
                            <h5 className="text-sm font-medium text-ink truncate flex items-center gap-1.5">
                              {isPart && (
                                <span className="shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent/20 text-accent font-bold">
                                  PART {clip.id}
                                </span>
                              )}
                              <span className="truncate">{clip.title}</span>
                            </h5>
                            <div className="flex items-center gap-1.5 shrink-0">
                              {clip.voice_id && (
                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ok/15 text-ok border border-ok/20 font-medium flex items-center gap-1">
                                  <Mic size={10} /> AI Voice
                                </span>
                              )}
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                                {clip.virality_score}%
                              </span>
                            </div>
                          </div>
                          {clip.hook && (
                            <p className="text-xs text-muted italic line-clamp-2">
                              "{clip.hook}"
                            </p>
                          )}
                          <p className="text-[11px] font-mono text-muted flex items-center gap-2 pt-1">
                            <Clock size={11} /> {clip.duration}s · {clip.size_mb} MB
                          </p>
                        </div>

                        <div className="flex items-center gap-2 pt-2 border-t border-rule/50">
                          <a
                            href={videoUrl}
                            download={videoFilename}
                            className="flex-1 py-2 px-3 text-xs font-medium rounded-input bg-accent text-accent-ink hover:opacity-90 transition-opacity text-center flex items-center justify-center gap-1.5"
                          >
                            <Download size={13} /> Download MP4
                          </a>
                          {srtUrl && (
                            <a
                              href={srtUrl}
                              download={srtFilename}
                              className="py-2 px-3 text-xs font-medium rounded-input border border-rule hover:bg-paper3 text-ink2 transition-colors flex items-center gap-1"
                              title="Download SRT Subtitles"
                            >
                              <Subtitles size={13} /> SRT
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Input & Configuration Card (When not processing or on error) */}
        {(!jobStatus || jobStatus === 'FAILED') && (
          <div className="p-6 rounded-card bg-paper2 border border-rule space-y-6">
            {errorMsg && (
              <div className="p-3.5 rounded-input bg-danger/10 border border-danger/20 text-danger text-xs flex items-center gap-2">
                <AlertCircle size={16} className="shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Input Selection Tabs */}
            <div className="flex border-b border-rule pb-3 gap-4">
              <button
                type="button"
                onClick={() => setInputType('url')}
                className={`flex items-center gap-2 pb-1 text-sm font-medium transition-colors border-b-2 ${
                  inputType === 'url' ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink2'
                }`}
              >
                <Link2 size={15} /> YouTube / Video URL
              </button>
              <button
                type="button"
                onClick={() => setInputType('file')}
                className={`flex items-center gap-2 pb-1 text-sm font-medium transition-colors border-b-2 ${
                  inputType === 'file' ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink2'
                }`}
              >
                <Upload size={15} /> Upload Local Video File
              </button>
            </div>

            {/* URL Input */}
            {inputType === 'url' ? (
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Video URL
                </label>
                <input
                  type="url"
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-input bg-paper border border-rule text-ink placeholder:text-muted/60 text-sm focus:outline-none focus:border-accent transition-colors"
                />
                <p className="text-[11px] text-muted">
                  Downloads video stream using yt-dlp at up to 1080p for optimal vertical rendering.
                </p>
              </div>
            ) : (
              /* File Upload */
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Select Video File (.mp4, .mov, .mkv, .webm)
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-rule hover:border-accent/60 rounded-card p-8 text-center cursor-pointer transition-colors bg-paper/40 hover:bg-paper/70 space-y-2"
                >
                  <Upload size={28} className="mx-auto text-muted" />
                  <p className="text-sm font-medium text-ink">
                    {selectedFile ? selectedFile.name : 'Click or drop video file here'}
                  </p>
                  <p className="text-xs text-muted">
                    {selectedFile ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB` : 'Supports up to 2GB files'}
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>
            )}

            {/* Video Coverage Mode Selector: Full Series vs Part Highlights */}
            <div className="space-y-2.5 pt-2 border-t border-rule">
              <label className="text-xs font-mono uppercase tracking-wider text-muted flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Sparkles size={13} className="text-accent" /> Video Coverage Mode
                </span>
                <span className="text-[11px] text-muted lowercase font-mono">
                  {coverageMode === 'full' ? 'continuous full-length series' : 'selective viral hooks'}
                </span>
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Part (Highlights) Option */}
                <div
                  onClick={() => {
                    setCoverageMode('part');
                    if (maxClips > 5) setMaxClips(3);
                  }}
                  className={`p-3.5 rounded-input border cursor-pointer transition-all space-y-1 ${
                    coverageMode === 'part'
                      ? 'border-accent bg-accent/10 shadow-sm'
                      : 'border-rule bg-paper hover:bg-paper3 opacity-80 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink flex items-center gap-1.5">
                      <Zap size={14} className={coverageMode === 'part' ? 'text-accent' : 'text-muted'} />
                      Part / Viral Highlights
                    </span>
                    {coverageMode === 'part' && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent text-accent-ink font-bold">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted leading-relaxed">
                    Extracts the top 1–5 standalone viral moments and highest-energy hooks.
                  </p>
                </div>

                {/* Full Series Option */}
                <div
                  onClick={() => {
                    setCoverageMode('full');
                    if (maxClips < 10) setMaxClips(10);
                  }}
                  className={`p-3.5 rounded-input border cursor-pointer transition-all space-y-1 ${
                    coverageMode === 'full'
                      ? 'border-accent bg-accent/10 shadow-sm'
                      : 'border-rule bg-paper hover:bg-paper3 opacity-80 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink flex items-center gap-1.5">
                      <Film size={14} className={coverageMode === 'full' ? 'text-accent' : 'text-muted'} />
                      Full Video Series (Part 1, 2, 3...)
                    </span>
                    {coverageMode === 'full' && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent text-accent-ink font-bold">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted leading-relaxed">
                    Covers 100% of the video sequentially without gaps, numbered chapter by chapter.
                  </p>
                </div>
              </div>
            </div>

            {/* Controls & Pipeline Options */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-2 border-t border-rule">
              {/* Reframing Mode */}
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Vertical 9:16 Reframing Mode
                </label>
                <select
                  value={reframingMode}
                  onChange={(e) => setReframingMode(e.target.value)}
                  className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm focus:outline-none focus:border-accent"
                >
                  <option value="pillar_blur">Pillar Blur (Clean 16:9 on blurred 9:16 background)</option>
                  <option value="smart_crop">Smart Speaker Crop (Face-centered 9:16 slice)</option>
                </select>
                <p className="text-[11px] text-muted">
                  {reframingMode === 'pillar_blur'
                    ? 'Recommended: keeps the complete landscape video frame visible with zero cut-off.'
                    : 'Centers crop box dynamically on detected face.'}
                </p>
              </div>

              {/* Number of Clips / Parts */}
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  {coverageMode === 'full' ? 'Max Series Parts to Extract' : 'Max Viral Clips to Extract'}
                </label>
                {coverageMode === 'full' ? (
                  <select
                    value={maxClips}
                    onChange={(e) => setMaxClips(e.target.value)}
                    className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm focus:outline-none focus:border-accent"
                  >
                    <option value="5">Up to 5 Parts (~2-4 min video)</option>
                    <option value="10">Up to 10 Parts (~5-8 min video)</option>
                    <option value="15">Up to 15 Parts (~8-12 min video)</option>
                    <option value="20">Up to 20 Parts (~12-18 min video)</option>
                    <option value="30">Up to 30 Parts (Long-form / 20+ min)</option>
                  </select>
                ) : (
                  <select
                    value={maxClips}
                    onChange={(e) => setMaxClips(e.target.value)}
                    className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm focus:outline-none focus:border-accent"
                  >
                    <option value="1">1 Short</option>
                    <option value="2">2 Shorts</option>
                    <option value="3">3 Shorts (Recommended)</option>
                    <option value="5">5 Shorts</option>
                  </select>
                )}
                <p className="text-[11px] text-muted">
                  {coverageMode === 'full'
                    ? 'Will partition the timeline sequentially until the whole video is covered.'
                    : 'Ranks clips by virality score and outputs the top picks.'}
                </p>
              </div>

              {/* Duration Range */}
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Clip Duration Limits
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="10"
                    max="60"
                    value={minDuration}
                    onChange={(e) => setMinDuration(e.target.value)}
                    className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm"
                    placeholder="Min (15s)"
                  />
                  <span className="text-muted text-xs">to</span>
                  <input
                    type="number"
                    min="20"
                    max="120"
                    value={maxDuration}
                    onChange={(e) => setMaxDuration(e.target.value)}
                    className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm"
                    placeholder="Max (60s)"
                  />
                  <span className="text-muted text-xs">sec</span>
                </div>
              </div>

              {/* Transcription Model Speed */}
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Whisper Speed & Accuracy
                </label>
                <select
                  value={whisperModel}
                  onChange={(e) => setWhisperModel(e.target.value)}
                  className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm focus:outline-none focus:border-accent"
                >
                  <option value="tiny">Tiny (Fastest, ~3-5s transcription)</option>
                  <option value="base">Base (Balanced, recommended)</option>
                  <option value="small">Small (Higher accuracy for accents)</option>
                </select>
              </div>

              {/* Spoken Video Language */}
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Globe size={13} className="text-accent" /> Original Video Language
                  </span>
                  <span className="text-[10px] font-mono text-accent">Source Audio</span>
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm focus:outline-none focus:border-accent"
                >
                  <option value="auto">🌐 Auto-Detect Language (Default)</option>
                  <option value="en">English (en)</option>
                  <option value="es">Spanish / Español (es)</option>
                  <option value="fr">French / Français (fr)</option>
                  <option value="de">German / Deutsch (de)</option>
                  <option value="it">Italian / Italiano (it)</option>
                  <option value="pt">Portuguese / Português (pt)</option>
                  <option value="vi">Vietnamese / Tiếng Việt (vi)</option>
                  <option value="ja">Japanese / 日本語 (ja)</option>
                  <option value="zh">Chinese / 中文 (zh)</option>
                  <option value="ko">Korean / 한국어 (ko)</option>
                  <option value="hi">Hindi / हिन्दी (hi)</option>
                  <option value="ru">Russian / Русский (ru)</option>
                  <option value="ar">Arabic / العربية (ar)</option>
                  <option value="nl">Dutch / Nederlands (nl)</option>
                  <option value="tr">Turkish / Türkçe (tr)</option>
                  <option value="id">Indonesian / Bahasa (id)</option>
                  <option value="pl">Polish / Polski (pl)</option>
                </select>
              </div>
            </div>

            {/* Subtitles, Translation & Gemini Key */}
            <div className="space-y-4 pt-2 border-t border-rule">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={burnSubtitles}
                  onChange={(e) => setBurnSubtitles(e.target.checked)}
                  className="w-4 h-4 rounded text-accent focus:ring-accent accent-[#e5a93c]"
                />
                <span className="text-sm font-medium text-ink flex items-center gap-1.5">
                  <Subtitles size={14} className="text-accent" /> Burn Dynamic Karaoke Subtitles (Word Highlight)
                </span>
              </label>

              {/* Translate & Dub into English Toggle */}
              <label className="flex items-center justify-between p-3 rounded-input bg-paper border border-rule cursor-pointer hover:border-accent/40 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="text-base">🌐 ➔ 🇬🇧</span>
                  <div>
                    <span className="text-sm font-medium text-ink block">
                      Translate & Dub into English (AI Translation)
                    </span>
                    <span className="text-xs text-muted block">
                      Translates foreign speech (e.g. Vietnamese, Spanish) into English subtitles & English ElevenLabs voice.
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={translateToEnglish}
                  onChange={(e) => setTranslateToEnglish(e.target.checked)}
                  className="w-4 h-4 rounded text-accent focus:ring-accent accent-[#e5a93c]"
                />
              </label>

              {/* Kids Story Scriptwriter Adaptation Toggle */}
              <label className="flex items-center justify-between p-3 rounded-input bg-paper border border-rule cursor-pointer hover:border-accent/40 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="text-base">✨ 📖</span>
                  <div>
                    <span className="text-sm font-medium text-ink flex items-center gap-2">
                      Kids Animated Story Scriptwriter
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent/20 text-accent font-semibold">
                        ±5 WORDS RULE
                      </span>
                    </span>
                    <span className="text-xs text-muted block">
                      Adapts raw transcript into a whimsical, engaging story script (Disney/Pixar style) strictly rhythm-synchronized to animation cuts.
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={kidsStorytellingMode}
                  onChange={(e) => setKidsStorytellingMode(e.target.checked)}
                  className="w-4 h-4 rounded text-accent focus:ring-accent accent-[#e5a93c]"
                />
              </label>

              <div className="space-y-1.5">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Google Gemini API Key (Optional — Leave empty for $0 offline heuristic)
                </label>
                <input
                  type="password"
                  placeholder="AIzaSy... (optional, uses free tier for viral scoring)"
                  value={customGeminiKey}
                  onChange={(e) => setCustomGeminiKey(e.target.value)}
                  className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink placeholder:text-muted/50 text-sm focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            {/* AI Voice Changing / Voiceover (ElevenLabs) */}
            <div className="space-y-3 pt-4 border-t border-rule">
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-sm font-medium text-ink flex items-center gap-2">
                  <Mic size={15} className="text-accent" /> Replace Original Speaker Voice with ElevenLabs AI
                </span>
                <input
                  type="checkbox"
                  checked={enableVoiceover}
                  onChange={(e) => setEnableVoiceover(e.target.checked)}
                  className="w-4 h-4 rounded text-accent focus:ring-accent accent-[#e5a93c]"
                />
              </label>

              {enableVoiceover && (
                <div className="p-4 rounded-input bg-paper border border-rule space-y-4 animate-fade">
                  {/* Multilingual / Translation Engine Notice */}
                  <div className="p-3 rounded-input bg-paper2 border border-rule flex items-start gap-3">
                    <Globe size={16} className="text-accent shrink-0 mt-0.5" />
                    <div className="text-xs text-ink leading-relaxed">
                      <div className="font-medium text-accent flex items-center gap-1.5 mb-0.5">
                        {kidsStorytellingMode
                          ? '✨ Kids Animated Story Scriptwriter Active (±5 Words Rule)'
                          : translateToEnglish
                          ? '🇬🇧 English Translation & Dubbing Active'
                          : '🌐 Multilingual AI Voice Model (32 Languages)'}
                      </div>
                      <p className="text-muted text-[11px]">
                        {kidsStorytellingMode ? (
                          <>
                            The transcript is adapted into an enchanting children's story script (Disney/Pixar style) strictly adhering to the <strong className="text-ink">±5 words rule</strong>. The chosen voice will narrate the story script with perfect animated cadence.
                          </>
                        ) : translateToEnglish ? (
                          <>
                            Whisper will automatically translate foreign speech into <strong className="text-ink">English text & subtitles</strong>. Your selected ElevenLabs voice will speak the <strong className="text-ink">English translation</strong> with natural pronunciation.
                          </>
                        ) : (
                          <>
                            Demo sample buttons (<Volume2 size={11} className="inline text-accent" />) play English voice previews. The AI model (<code className="font-mono text-[10px] text-accent">eleven_flash_v2_5</code>) automatically speaks in{' '}
                            <strong className="text-ink">
                              {language === 'auto' ? "your video's detected language" : `your selected language (${language.toUpperCase()})`}
                            </strong>{' '}
                            with the chosen actor's pitch and style.
                          </>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Voice Selector Header + Filter Controls */}
                  {(() => {
                    const filteredVoices = voices.filter((v) => {
                      const gender = (v.labels?.gender || '').toLowerCase();
                      const category = (v.category || '').toLowerCase();
                      if (voiceCategoryFilter === 'female' && gender !== 'female') return false;
                      if (voiceCategoryFilter === 'male' && gender !== 'male') return false;
                      if (voiceCategoryFilter === 'custom' && category === 'premade') return false;
                      if (voiceSearchQuery.trim()) {
                        const q = voiceSearchQuery.toLowerCase();
                        const matchName = v.name?.toLowerCase().includes(q);
                        const matchAccent = v.labels?.accent?.toLowerCase().includes(q);
                        const matchDesc = v.labels?.description?.toLowerCase().includes(q);
                        if (!matchName && !matchAccent && !matchDesc) return false;
                      }
                      return true;
                    });

                    return (
                      <div className="space-y-2.5">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-mono uppercase tracking-wider text-muted">
                            Select Voice Model ({voices.length} available)
                          </label>
                          <span className="text-[11px] font-mono text-muted">
                            {filteredVoices.length} shown
                          </span>
                        </div>

                        {/* Filter Tabs & Search */}
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="flex items-center bg-paper2 rounded-input border border-rule p-0.5">
                            {['all', 'female', 'male', 'custom'].map((cat) => (
                              <button
                                key={cat}
                                type="button"
                                onClick={() => setVoiceCategoryFilter(cat)}
                                className={`px-2.5 py-1 text-xs rounded-sm capitalize transition-colors ${
                                  voiceCategoryFilter === cat
                                    ? 'bg-paper3 text-accent font-medium shadow-sm'
                                    : 'text-muted hover:text-ink'
                                }`}
                              >
                                {cat}
                              </button>
                            ))}
                          </div>

                          <div className="relative flex-1 min-w-[140px]">
                            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
                            <input
                              type="text"
                              placeholder="Search voice..."
                              value={voiceSearchQuery}
                              onChange={(e) => setVoiceSearchQuery(e.target.value)}
                              className="w-full pl-8 pr-2.5 py-1 text-xs rounded-input bg-paper2 border border-rule text-ink placeholder:text-muted/50 focus:outline-none focus:border-accent"
                            />
                          </div>
                        </div>

                        {/* Interactive Voice Cards List */}
                        <div className="space-y-1.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
                          {filteredVoices.length === 0 ? (
                            <div className="py-6 text-center text-xs text-muted border border-dashed border-rule rounded-input">
                              No voices found matching "{voiceSearchQuery || voiceCategoryFilter}"
                            </div>
                          ) : (
                            filteredVoices.map((v) => {
                              const isSelected = selectedVoiceId === v.voice_id;
                              const isPlaying = playingPreview === v.preview_url;
                              return (
                                <button
                                  key={v.voice_id}
                                  type="button"
                                  onClick={() => setSelectedVoiceId(v.voice_id)}
                                  className={`w-full flex items-center gap-3 p-2.5 rounded-input border text-left transition-colors duration-200 ${
                                    isSelected
                                      ? 'border-accent bg-paper3'
                                      : 'border-rule bg-paper hover:bg-paper3'
                                  }`}
                                >
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className={`text-sm truncate font-medium ${isSelected ? 'text-ink' : 'text-ink2'}`}>
                                        {v.name}
                                      </span>
                                      {v.category && v.category !== 'premade' && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/15 text-accent font-mono">
                                          {v.category}
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-[11px] text-muted mt-0.5 capitalize">
                                      {v.labels?.accent || 'natural'} {v.labels?.gender ? `· ${v.labels.gender}` : ''}{' '}
                                      {v.labels?.description ? `· ${v.labels.description}` : ''}
                                    </div>
                                  </div>

                                  {/* Preview Button */}
                                  {v.preview_url && (
                                    <button
                                      type="button"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleTogglePreview(v.preview_url);
                                      }}
                                      className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
                                        isPlaying
                                          ? 'bg-accent text-paper animate-pulse'
                                          : 'bg-paper2 text-muted hover:text-accent hover:bg-paper3'
                                      }`}
                                      title={isPlaying ? 'Pause preview' : 'Play voice sample'}
                                    >
                                      {isPlaying ? <VolumeX size={12} /> : <Volume2 size={12} />}
                                    </button>
                                  )}

                                  {/* Selected Checkmark */}
                                  {isSelected && <Check size={15} className="text-accent shrink-0" />}
                                </button>
                              );
                            })
                          )}
                        </div>

                        <p className="text-[11px] text-muted">
                          Whisper transcribes words in {language === 'auto' ? 'auto-detected language' : language.toUpperCase()}; ElevenLabs re-voices each short in that language with natural pacing.
                        </p>
                      </div>
                    );
                  })()}

                  {/* ElevenLabs API Key */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-mono uppercase tracking-wider text-muted">
                      ElevenLabs API Key
                    </label>
                    <input
                      type="password"
                      placeholder="sk_... (or xi-api-key)"
                      value={customElevenLabsKey}
                      onChange={(e) => {
                        setCustomElevenLabsKey(e.target.value);
                        localStorage.setItem('elevenLabsKey_v1', e.target.value);
                      }}
                      className="w-full px-3 py-2 rounded-input bg-paper2 border border-rule text-ink placeholder:text-muted/50 text-sm focus:outline-none focus:border-accent"
                    />
                    <p className="text-[11px] text-muted">
                      Saved locally in your browser. Get your free API key at{' '}
                      <a
                        href="https://elevenlabs.io"
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent underline hover:opacity-80"
                      >
                        elevenlabs.io
                      </a>
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <div className="pt-3">
              <button
                type="button"
                onClick={handleStartProcess}
                disabled={uploading}
                className="w-full py-3 px-5 rounded-input bg-accent text-accent-ink font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2 text-base shadow-sm disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" /> Uploading Video File...
                  </>
                ) : coverageMode === 'full' ? (
                  <>
                    <Film size={18} /> Cut Full Video Series (Part 1, 2, ...) · $0 Cost
                  </>
                ) : (
                  <>
                    <Scissors size={18} /> Cut Viral Shorts Highlights ($0 Cost)
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
