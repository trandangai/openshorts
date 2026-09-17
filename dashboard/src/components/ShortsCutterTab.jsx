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
} from 'lucide-react';
import { getApiUrl } from '../config';

export default function ShortsCutterTab({ geminiApiKey = '' }) {
  const [inputType, setInputType] = useState('url'); // 'url' | 'file'
  const [url, setUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Settings
  const [reframingMode, setReframingMode] = useState('pillar_blur');
  const [maxClips, setMaxClips] = useState(3);
  const [minDuration, setMinDuration] = useState(15);
  const [maxDuration, setMaxDuration] = useState(60);
  const [burnSubtitles, setBurnSubtitles] = useState(true);
  const [whisperModel, setWhisperModel] = useState('base');
  const [customGeminiKey, setCustomGeminiKey] = useState(geminiApiKey || '');

  // Job Execution State
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null); // 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  const [jobData, setJobData] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const timerRef = useRef(null);
  const fileInputRef = useRef(null);

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

      const res = await fetch(getApiUrl('/api/shorts-cutter/process'), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          input_source: sourcePath,
          max_clips: parseInt(maxClips, 10),
          min_clip_duration: parseFloat(minDuration),
          max_clip_duration: parseFloat(maxDuration),
          reframing_mode: reframingMode,
          burn_subtitles: burnSubtitles,
          whisper_model_size: whisperModel,
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
                <h4 className="text-sm font-mono uppercase tracking-wider text-muted flex items-center gap-2">
                  <Film size={14} className="text-accent" /> Generated Vertical Clips ({jobData.clips.length})
                </h4>

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
                          <div className="flex items-center justify-between">
                            <h5 className="text-sm font-medium text-ink truncate">{clip.title}</h5>
                            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                              {clip.virality_score}% Viral
                            </span>
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

              {/* Number of Clips */}
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-muted">
                  Max Viral Clips to Extract
                </label>
                <select
                  value={maxClips}
                  onChange={(e) => setMaxClips(e.target.value)}
                  className="w-full px-3 py-2 rounded-input bg-paper border border-rule text-ink text-sm focus:outline-none focus:border-accent"
                >
                  <option value="1">1 Short</option>
                  <option value="2">2 Shorts</option>
                  <option value="3">3 Shorts</option>
                  <option value="5">5 Shorts</option>
                </select>
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
            </div>

            {/* Subtitles & Gemini Key */}
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
                ) : (
                  <>
                    <Scissors size={18} /> Cut Viral Shorts Now ($0 Cost)
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
