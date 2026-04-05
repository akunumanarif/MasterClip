"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { Play, Scissors, Video, Loader2, Link as LinkIcon, Clock, Plus, Trash2, CheckSquare, Square, Zap, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Toaster, toast } from "sonner";

interface ClipSegment {
  id: string;
  start: string;
  end: string;
}

interface ClipCandidate {
  index: number;
  start: number;
  end: number;
  duration: number;
  score: number;
  text_preview: string;
  word_count: number;
  speaker: string;
  speakers_in_clip: string[];
}

type AppStatus = "idle" | "analyzing" | "ready_for_review" | "generating" | "completed" | "error";

export default function Home() {
  const [url, setUrl] = useState("");
  const [segments, setSegments] = useState<ClipSegment[]>([
    { id: "1", start: "00:00:10", end: "00:00:30" }
  ]);
  const [clipMode, setClipMode] = useState<"auto" | "manual">("auto");
  const [inputMode, setInputMode] = useState<"manual" | "bulk">("manual");
  const [bulkText, setBulkText] = useState("");

  const [isProcessing, setIsProcessing] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  interface CaptionData { hook: string; caption: string; hashtags: string[]; }
  const [outputFiles, setOutputFiles] = useState<Array<{ filename: string; url: string; text_preview?: string; caption?: CaptionData }>>([]);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const [resolution, setResolution] = useState("1080p");
  const [colorGrading, setColorGrading] = useState("none");
  const [aspectRatio, setAspectRatio] = useState("9:16");

  // Phase 1 results
  const [clipCandidates, setClipCandidates] = useState<ClipCandidate[]>([]);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());

  // Quote generator state
  const [quoteUrl, setQuoteUrl] = useState<string | null>(null);
  const [isQuoteLoading, setIsQuoteLoading] = useState(false);
  const [quoteLang, setQuoteLang] = useState("en");
  const [quoteCategory, setQuoteCategory] = useState("life");
  const [quoteFormat, setQuoteFormat] = useState("image");

  const getYoutubeId = (url: string) => {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return match && match[2].length === 11 ? match[2] : null;
  };
  const videoId = getYoutubeId(url);

  // Poll status
  useEffect(() => {
    let interval: NodeJS.Timeout;

    const isPolling = projectId && (status === "analyzing" || status === "generating");
    if (isPolling) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`/api/status/${projectId}`);
          const data = res.data;

          if (!data.status) return;

          if (data.status === "ready_for_review") {
            setStatus("ready_for_review");
            setIsProcessing(false);
            const candidates: ClipCandidate[] = data.clip_candidates || [];
            setClipCandidates(candidates);
            // Select all by default
            setSelectedIndices(new Set(candidates.map((_: ClipCandidate, i: number) => i)));
            toast.success(`Found ${candidates.length} clip candidates! Review and select.`);
            clearInterval(interval);
          } else if (data.status === "completed") {
            setStatus("completed");
            setIsProcessing(false);
            setOutputFiles(data.outputs || []);
            setEmailSent(data.email_sent || false);
            const emailMsg = data.email_sent ? " Check your email for download links!" : "";
            toast.success(`All clips generated!${emailMsg}`);
            clearInterval(interval);
          } else if (data.status === "error") {
            setStatus("error");
            setIsProcessing(false);
            setStatusMessage(data.message || "An error occurred.");
            toast.error(`Error: ${data.message}`);
            clearInterval(interval);
          } else {
            if (data.message !== statusMessage) {
              setStatusMessage(data.message || "Processing...");
            }
          }
        } catch (error) {
          console.error("Polling error", error);
        }
      }, 2000);
    }

    return () => clearInterval(interval);
  }, [projectId, status, statusMessage]);

  const parseBulkTimestamps = (text: string): ClipSegment[] => {
    const lines = text.split("\n").filter((l) => l.trim());
    const parsed: ClipSegment[] = [];
    lines.forEach((line, index) => {
      const match = line.match(/(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})/);
      if (match) parsed.push({ id: `bulk_${index + 1}`, start: match[1], end: match[2] });
    });
    return parsed;
  };

  const applyBulkTimestamps = () => {
    const parsed = parseBulkTimestamps(bulkText);
    if (parsed.length > 0) {
      setSegments(parsed);
      toast.success(`Parsed ${parsed.length} timestamp(s)`);
    } else {
      toast.error("No valid timestamps found. Use format: 00:01:02 - 00:10:00");
    }
  };

  const addSegment = () => setSegments([...segments, { id: Date.now().toString(), start: "00:00:00", end: "00:00:10" }]);
  const removeSegment = (i: number) => { if (segments.length > 1) { const s = [...segments]; s.splice(i, 1); setSegments(s); } };
  const updateSegment = (i: number, field: "start" | "end", value: string) => {
    const s = [...segments]; s[i][field] = value; setSegments(s);
  };

  const handleAnalyze = async () => {
    if (!url) { toast.error("Please enter a YouTube URL"); return; }

    setIsProcessing(true);
    setStatus("analyzing");
    setStatusMessage("Starting analysis...");
    setProjectId(null);
    setOutputFiles([]);
    setClipCandidates([]);
    setSelectedIndices(new Set());
    setEmailSent(false);

    try {
      const response = await axios.post("/api/analyze", {
        youtube_url: url,
        resolution,
        color_grading: colorGrading,
        aspect_ratio: aspectRatio,
      });
      if (response.data.project_id) {
        setProjectId(response.data.project_id);
        toast.success("Analysis started! Transcribing and scoring clips...");
      }
    } catch (error) {
      console.error(error);
      setIsProcessing(false);
      setStatus("idle");
      toast.error("Failed to start analysis.");
    }
  };

  const handleGenerateSelected = async () => {
    if (!projectId || selectedIndices.size === 0) {
      toast.error("Please select at least one clip.");
      return;
    }

    setIsProcessing(true);
    setStatus("generating");
    setStatusMessage("Starting render...");

    try {
      await axios.post("/api/generate", {
        project_id: projectId,
        selected_indices: Array.from(selectedIndices).sort((a, b) => a - b),
      });
      toast.success("Rendering started!");
    } catch (error) {
      console.error(error);
      setIsProcessing(false);
      setStatus("ready_for_review");
      toast.error("Failed to start rendering.");
    }
  };

  const toggleClip = (i: number) => {
    const next = new Set(selectedIndices);
    if (next.has(i)) next.delete(i); else next.add(i);
    setSelectedIndices(next);
  };

  const selectAll = () => setSelectedIndices(new Set(clipCandidates.map((_, i) => i)));
  const selectNone = () => setSelectedIndices(new Set());

  const formatTime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    return `${m}:${String(sec).padStart(2, "0")}`;
  };

  const handleGenerateQuote = async () => {
    setIsQuoteLoading(true);
    try {
      const res = await axios.post("/api/generate-quote", { language: quoteLang, category: quoteCategory, format: quoteFormat });
      if (res.data.url) { setQuoteUrl(res.data.url); toast.success("Quote generated!"); }
    } catch (e) {
      toast.error("Failed to generate quote");
    } finally {
      setIsQuoteLoading(false);
    }
  };

  const resetToIdle = () => { setStatus("idle"); setProjectId(null); setStatusMessage(""); setClipCandidates([]); setSelectedIndices(new Set()); };

  const copyCaption = (file: { caption?: CaptionData }, idx: number) => {
    if (!file.caption) return;
    const { hook, caption, hashtags } = file.caption;
    const hashtagStr = hashtags.map((h: string) => `#${h}`).join(" ");
    const text = `${hook}\n\n${caption}\n\n${hashtagStr}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 2000);
      toast.success("Caption copied!");
    });
  };

  return (
    <main className="min-h-screen bg-background text-foreground flex flex-col items-center py-20 px-4">
      <Toaster position="top-center" theme="dark" />

      <div className="max-w-3xl w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/20 text-primary mb-4">
            <Scissors className="w-8 h-8" />
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight">
            AI Video <span className="text-primary">Shorts</span> Generator
          </h1>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            Turn long YouTube videos into viral shorts with dynamic captions.
          </p>
        </div>

        {/* Input Card — only show when idle or in early phase */}
        {(status === "idle" || status === "analyzing") && (
          <div className="bg-card border border-border rounded-xl p-6 shadow-2xl shadow-primary/5 space-y-6">

            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">YouTube URL</label>
              <div className="relative">
                <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="w-full bg-secondary/50 border border-border rounded-lg py-3 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-mono"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={isProcessing}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium ml-1">Output Resolution</label>
                <div className="grid grid-cols-4 gap-2">
                  {["1080p", "720p", "480p", "360p"].map((res) => (
                    <button
                      key={res}
                      onClick={() => setResolution(res)}
                      disabled={isProcessing}
                      className={cn(
                        "py-2 rounded-lg text-sm font-medium border transition-all",
                        resolution === res
                          ? "bg-primary text-primary-foreground border-primary shadow-sm"
                          : "bg-secondary/30 border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                      )}
                    >
                      {res === "1080p" ? "FHD" : res}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium ml-1">Aspect Ratio</label>
                <div className="grid grid-cols-3 gap-2">
                  {["9:16", "1:1", "16:9"].map((ar) => (
                    <button
                      key={ar}
                      onClick={() => setAspectRatio(ar)}
                      disabled={isProcessing}
                      className={cn(
                        "py-2 rounded-lg text-sm font-medium border transition-all",
                        aspectRatio === ar
                          ? "bg-primary text-primary-foreground border-primary shadow-sm"
                          : "bg-secondary/30 border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                      )}
                    >
                      {ar}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">Color Grading</label>
              <select
                value={colorGrading}
                onChange={(e) => setColorGrading(e.target.value)}
                disabled={isProcessing}
                className="w-full bg-secondary/50 border border-border rounded-lg py-3 px-4 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              >
                <option value="none">None (Original)</option>
                <option value="cinematic_warm">Cinematic Warm</option>
                <option value="cool_modern">Cool & Modern</option>
                <option value="vibrant">Vibrant Pop</option>
                <option value="matte_film">Matte Film</option>
                <option value="bw_contrast">B&W High Contrast</option>
              </select>
            </div>

            {videoId && (
              <div className="relative aspect-video rounded-lg overflow-hidden border border-border bg-black/50 animate-in fade-in zoom-in duration-300">
                <iframe
                  width="100%" height="100%"
                  src={`https://www.youtube.com/embed/${videoId}`}
                  title="YouTube video player"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={isProcessing}
              className={cn(
                "w-full py-4 rounded-lg font-bold text-lg transition-all flex items-center justify-center gap-2",
                isProcessing
                  ? "bg-secondary text-muted-foreground cursor-not-allowed"
                  : "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/25"
              )}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {statusMessage || "Analyzing..."}
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5" />
                  Analyze & Find Best Clips
                </>
              )}
            </button>
          </div>
        )}

        {/* Phase 1 Result: Clip Review */}
        {status === "ready_for_review" && clipCandidates.length > 0 && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
            <div className="bg-card border border-border rounded-xl p-6 shadow-2xl shadow-primary/5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Review Clip Candidates</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {clipCandidates.length} clips detected. Select which to generate.
                  </p>
                </div>
                <div className="flex gap-2">
                  <button onClick={selectAll} className="text-xs px-3 py-1.5 rounded-md bg-secondary/50 border border-border hover:bg-secondary transition-colors">
                    All
                  </button>
                  <button onClick={selectNone} className="text-xs px-3 py-1.5 rounded-md bg-secondary/50 border border-border hover:bg-secondary transition-colors">
                    None
                  </button>
                </div>
              </div>

              <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                {clipCandidates.map((clip, i) => {
                  const selected = selectedIndices.has(i);
                  return (
                    <button
                      key={i}
                      onClick={() => toggleClip(i)}
                      className={cn(
                        "w-full text-left p-4 rounded-lg border transition-all",
                        selected
                          ? "bg-primary/10 border-primary/40 ring-1 ring-primary/30"
                          : "bg-secondary/20 border-border hover:bg-secondary/40"
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex-shrink-0">
                          {selected
                            ? <CheckSquare className="w-5 h-5 text-primary" />
                            : <Square className="w-5 h-5 text-muted-foreground" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-1">
                            <span className="text-sm font-semibold">Clip {i + 1}</span>
                            <span className="text-xs text-muted-foreground font-mono">
                              {formatTime(clip.start)} – {formatTime(clip.end)}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {clip.duration.toFixed(0)}s
                            </span>
                            <span className={cn(
                              "ml-auto text-xs font-medium px-2 py-0.5 rounded-full",
                              clip.score >= 0.7 ? "bg-green-500/20 text-green-400" :
                              clip.score >= 0.4 ? "bg-yellow-500/20 text-yellow-400" :
                              "bg-secondary text-muted-foreground"
                            )}>
                              {(clip.score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                            {clip.text_preview}
                          </p>
                          {clip.speakers_in_clip?.length > 0 && (
                            <p className="text-xs text-muted-foreground/60 mt-1">
                              {clip.speakers_in_clip.join(", ")} · {clip.word_count} words
                            </p>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={resetToIdle}
                  className="px-4 py-3 rounded-lg border border-border text-sm font-medium hover:bg-secondary/50 transition-colors"
                >
                  Start Over
                </button>
                <button
                  onClick={handleGenerateSelected}
                  disabled={selectedIndices.size === 0}
                  className={cn(
                    "flex-1 py-3 rounded-lg font-bold text-base transition-all flex items-center justify-center gap-2",
                    selectedIndices.size === 0
                      ? "bg-secondary text-muted-foreground cursor-not-allowed"
                      : "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg shadow-primary/25"
                  )}
                >
                  <Play className="w-5 h-5 fill-current" />
                  Generate {selectedIndices.size} Clip{selectedIndices.size !== 1 ? "s" : ""}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Generating progress */}
        {status === "generating" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-card/50 border border-border rounded-xl p-10 flex flex-col items-center justify-center space-y-6 text-center">
              <div className="w-20 h-20 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
              <div className="space-y-2 max-w-sm">
                <p className="font-medium text-xl animate-pulse">{statusMessage || "Rendering..."}</p>
                <p className="text-sm text-muted-foreground">
                  AI is rendering and adding subtitles to your clips. This may take a few minutes.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Completed */}
        {status === "completed" && outputFiles.length > 0 && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
            <div className="bg-card border border-border rounded-xl p-6 shadow-2xl shadow-primary/5">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <div className="px-3 py-1 inline-block rounded-full bg-green-500/10 text-green-500 text-sm font-medium mb-2 border border-green-500/20">
                    Completed
                  </div>
                  <h2 className="text-2xl font-bold">Your Shorts are Ready!</h2>
                  {emailSent && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Download links sent to your email.
                    </p>
                  )}
                </div>
                <button
                  onClick={resetToIdle}
                  className="px-4 py-2 rounded-lg border border-border text-sm font-medium hover:bg-secondary/50 transition-colors"
                >
                  New Video
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {outputFiles.map((file, idx) => (
                  <div key={idx} className="space-y-3">
                    {/* Video */}
                    <div className="space-y-2 bg-black/20 p-3 rounded-xl border border-border/50">
                      <p className="font-medium text-sm text-center">Clip {idx + 1}</p>
                      <div className="relative w-full aspect-[9/16] bg-black rounded-lg overflow-hidden border border-border shadow-lg ring-1 ring-white/10">
                        <video src={file.url} controls className="w-full h-full object-cover" />
                      </div>
                      <a
                        href={file.url}
                        download
                        className="flex items-center justify-center gap-2 w-full py-2 rounded-lg bg-foreground text-background text-sm font-semibold hover:bg-foreground/90 transition-colors"
                      >
                        <Video className="w-3 h-3" />
                        Download
                      </a>
                    </div>

                    {/* Caption card */}
                    {file.caption ? (
                      <div className="bg-card border border-border rounded-xl p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Social Media Caption</span>
                          <button
                            onClick={() => copyCaption(file, idx)}
                            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors"
                          >
                            {copiedIdx === idx ? <><Check className="w-3 h-3" />Copied!</> : <><Copy className="w-3 h-3" />Copy</>}
                          </button>
                        </div>
                        <p className="font-semibold text-sm leading-snug">{file.caption.hook}</p>
                        <p className="text-sm text-muted-foreground leading-relaxed">{file.caption.caption}</p>
                        {file.caption.hashtags?.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {file.caption.hashtags.map((tag: string, ti: number) => (
                              <span key={ti} className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                                #{tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-card/50 border border-border rounded-xl p-4">
                        <p className="text-xs text-muted-foreground text-center">Caption not available</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Error state */}
        {status === "error" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-card/50 border border-border rounded-xl p-10 flex flex-col items-center justify-center space-y-6 text-center">
              <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                <span className="text-3xl">✕</span>
              </div>
              <div className="space-y-2 max-w-sm">
                <p className="font-semibold text-xl text-red-400">Processing Failed</p>
                <p className="text-sm text-muted-foreground">{statusMessage || "An unexpected error occurred."}</p>
              </div>
              <button
                onClick={resetToIdle}
                className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Quote Generator Card */}
        <div className="bg-card border border-border rounded-xl p-6 shadow-2xl shadow-primary/5 space-y-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <span>✨</span> Motivational Quote Card
          </h2>
          <p className="text-sm text-muted-foreground">
            Generate a random motivational quote with a beautiful background for your social media.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">Format</label>
              <div className="flex bg-secondary/50 p-1 rounded-lg border border-border">
                {["image", "video"].map((f) => (
                  <button key={f} onClick={() => setQuoteFormat(f)}
                    className={cn("flex-1 py-1.5 text-sm font-medium rounded-md transition-all capitalize",
                      quoteFormat === f ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}>
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">Language</label>
              <select value={quoteLang} onChange={(e) => setQuoteLang(e.target.value)}
                className="w-full bg-secondary/50 border border-border rounded-lg py-2 px-3 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm">
                <option value="en">English</option>
                <option value="id">Bahasa Indonesia</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">Category</label>
              <select value={quoteCategory} onChange={(e) => setQuoteCategory(e.target.value)}
                className="w-full bg-secondary/50 border border-border rounded-lg py-2 px-3 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm">
                <option value="life">Life / Motivation</option>
                <option value="islamic">Islamic</option>
                <option value="finance">Finance / Business</option>
                <option value="others">Success / Others</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col md:flex-row gap-6 items-start">
            <button
              onClick={handleGenerateQuote}
              disabled={isQuoteLoading}
              className={cn(
                "md:w-1/3 w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 border",
                isQuoteLoading
                  ? "bg-secondary text-muted-foreground cursor-not-allowed"
                  : "bg-secondary/30 hover:bg-secondary text-foreground border-border hover:border-primary/50"
              )}
            >
              {isQuoteLoading ? <><Loader2 className="w-4 h-4 animate-spin" />Generating...</> : <><Plus className="w-4 h-4" />Generate Quote {quoteFormat === "video" ? "Video" : "Image"}</>}
            </button>

            {quoteUrl && (
              <div className="md:w-2/3 w-full animate-in fade-in slide-in-from-right-4 duration-500">
                <div className="relative aspect-[9/16] md:aspect-square rounded-lg overflow-hidden border border-border bg-black/50 shadow-lg max-h-[400px] flex items-center justify-center">
                  {quoteUrl.endsWith(".mp4")
                    ? <video src={quoteUrl} controls autoPlay loop className="max-h-full max-w-full object-contain" />
                    : <img src={quoteUrl} alt="Generated Quote" className="w-full h-full object-cover" />}
                </div>
                <a href={quoteUrl} download className="mt-2 text-sm text-primary hover:underline flex items-center gap-1 justify-end">
                  <Video className="w-3 h-3" /> Download {quoteFormat === "video" ? "Video" : "Image"}
                </a>
              </div>
            )}
          </div>
        </div>

      </div>
    </main>
  );
}
