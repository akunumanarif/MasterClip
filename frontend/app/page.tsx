"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { Play, Scissors, Video, Loader2, Link as LinkIcon, Clock, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Toaster, toast } from "sonner";

interface ClipSegment {
  id: string;
  start: string;
  end: string;
}

export default function Home() {
  const [url, setUrl] = useState("");
  // Segments state
  const [segments, setSegments] = useState<ClipSegment[]>([
    { id: "1", start: "00:00:10", end: "00:00:30" }
  ]);

  // Input mode: 'manual' or 'bulk'
  const [inputMode, setInputMode] = useState<'manual' | 'bulk'>('manual');
  const [bulkText, setBulkText] = useState("");

  const [isProcessing, setIsProcessing] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [outputFiles, setOutputFiles] = useState<Array<{ filename: string; url: string }>>([]);
  const [emailSent, setEmailSent] = useState<boolean>(false);
  const [resolution, setResolution] = useState<string>("1080p");
  const [colorGrading, setColorGrading] = useState<string>("none");
  const [quoteUrl, setQuoteUrl] = useState<string | null>(null);
  const [isQuoteLoading, setIsQuoteLoading] = useState(false);
  const [quoteLang, setQuoteLang] = useState<string>("en");
  const [quoteCategory, setQuoteCategory] = useState<string>("life");
  const [quoteFormat, setQuoteFormat] = useState<string>("image");

  // Extract YouTube ID for preview
  const getYoutubeId = (url: string) => {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
  };

  const videoId = getYoutubeId(url);

  // Poll status
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (projectId && status === "processing") {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`/api/status/${projectId}`);
          const data = res.data;
          if (data.status) {
            if (data.status === "completed") {
              setStatus("completed");
              setIsProcessing(false);
              setOutputFiles(data.outputs || []); // Get list of files with URLs
              setEmailSent(data.email_sent || false);
              const emailMsg = data.email_sent ? " Check your email for download links!" : "";
              toast.success(`All videos generated successfully!${emailMsg}`);
              clearInterval(interval);
            } else if (data.status === "error") {
              setStatus("error");
              setIsProcessing(false);
              toast.error(`Error: ${data.message}`);
              clearInterval(interval);
            } else {
              if (data.message !== statusMessage) {
                setStatusMessage(data.message || "Processing...");
              }
            }
          }
        } catch (error) {
          console.error("Polling error", error);
        }
      }, 2000);
    }

    return () => clearInterval(interval);
  }, [projectId, status, statusMessage]);

  // Parse bulk timestamp text into segments
  const parseBulkTimestamps = (text: string): ClipSegment[] => {
    const lines = text.split('\n').filter(line => line.trim());
    const parsed: ClipSegment[] = [];

    lines.forEach((line, index) => {
      // Match format: "00:01:02 - 00:10:00" or "00:01:02-00:10:00"
      const match = line.match(/(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})/);
      if (match) {
        parsed.push({
          id: `bulk_${index + 1}`,
          start: match[1],
          end: match[2]
        });
      }
    });

    return parsed;
  };

  // Apply bulk timestamps
  const applyBulkTimestamps = () => {
    const parsed = parseBulkTimestamps(bulkText);
    if (parsed.length > 0) {
      setSegments(parsed);
      toast.success(`Parsed ${parsed.length} timestamp(s)`);
    } else {
      toast.error("No valid timestamps found. Use format: 00:01:02 - 00:10:00");
    }
  };

  const addSegment = () => {
    setSegments([...segments, { id: Date.now().toString(), start: "00:00:00", end: "00:00:10" }]);
  };

  const removeSegment = (index: number) => {
    if (segments.length > 1) {
      const newSegments = [...segments];
      newSegments.splice(index, 1);
      setSegments(newSegments);
    }
  };

  const updateSegment = (index: number, field: 'start' | 'end', value: string) => {
    const newSegments = [...segments];
    newSegments[index][field] = value;
    setSegments(newSegments);
  };

  const handleGenerate = async () => {
    if (!url) {
      toast.error("Please enter a YouTube URL");
      return;
    }

    setIsProcessing(true);
    setStatus("processing");
    setStatusMessage("Starting...");
    setProjectId(null);
    setOutputFiles([]);
    setEmailSent(false);

    try {
      // Map segments to backend format
      const payloadSegments = segments.map(s => ({
        start_time: s.start,
        end_time: s.end
      }));

      const response = await axios.post("/api/process", {
        youtube_url: url,
        segments: payloadSegments,
        project_name: "My Short",
        resolution: resolution,
        color_grading: colorGrading,
      });

      if (response.data.project_id) {
        setProjectId(response.data.project_id);
        toast.success("Processing started! This may take a few minutes.");
      }
    } catch (error) {
      console.error(error);
      setIsProcessing(false);
      setStatus("idle");
      toast.error("Failed to start processing.");
    }
  };

  const handleGenerateQuote = async () => {
    setIsQuoteLoading(true);
    try {
      const res = await axios.post("/api/generate-quote", {
        language: quoteLang,
        category: quoteCategory,
        format: quoteFormat
      });
      if (res.data.url) {
        setQuoteUrl(res.data.url);
        toast.success("Quote generated!");
      }
    } catch (e) {
      toast.error("Failed to generate quote");
      console.error(e);
    } finally {
      setIsQuoteLoading(false);
    }
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

        {/* Input Card */}
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
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium ml-1">Output Resolution</label>
            <div className="grid grid-cols-4 gap-2">
              {["1080p", "720p", "480p", "360p"].map((res) => (
                <button
                  key={res}
                  onClick={() => setResolution(res)}
                  className={cn(
                    "py-2 rounded-lg text-sm font-medium border transition-all",
                    resolution === res
                      ? "bg-primary text-primary-foreground border-primary shadow-sm"
                      : "bg-secondary/30 border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  {res === "1080p" ? "Full HD" : res}
                </button>
              ))
              }
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium ml-1">🎨 Color Grading</label>
            <select
              value={colorGrading}
              onChange={(e) => setColorGrading(e.target.value)}
              className="w-full bg-secondary/50 border border-border rounded-lg py-3 px-4 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
            >
              <option value="none">None (Original)</option>
              <option value="cinematic_warm">🔥 Cinematic Warm</option>
              <option value="cool_modern">❄️ Cool & Modern</option>
              <option value="vibrant">✨ Vibrant Pop</option>
              <option value="matte_film">🎬 Matte Film</option>
              <option value="bw_contrast">⚫ B&W High Contrast</option>
            </select>
          </div>


          {videoId && (
            <div className="relative aspect-video rounded-lg overflow-hidden border border-border bg-black/50 animate-in fade-in zoom-in duration-300">
              <iframe
                width="100%"
                height="100%"
                src={`https://www.youtube.com/embed/${videoId}`}
                title="YouTube video player"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              ></iframe>
            </div>
          )}

          <div className="space-y-4">
            {/* Mode Toggle */}
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium ml-1">Clips to Generate</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setInputMode('manual')}
                  className={cn(
                    "px-3 py-1 text-xs rounded-md transition-all",
                    inputMode === 'manual'
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary/30 text-muted-foreground hover:bg-secondary"
                  )}
                >
                  Manual
                </button>
                <button
                  onClick={() => setInputMode('bulk')}
                  className={cn(
                    "px-3 py-1 text-xs rounded-md transition-all",
                    inputMode === 'bulk'
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary/30 text-muted-foreground hover:bg-secondary"
                  )}
                >
                  Bulk Input
                </button>
              </div>
            </div>

            {/* Manual Input Mode */}
            {inputMode === 'manual' && (
              <>
                <div className="flex items-center justify-end">
                  <button onClick={addSegment} className="text-xs text-primary hover:underline flex items-center gap-1">
                    <Plus className="w-3 h-3" /> Add Segment
                  </button>
                </div>

                {segments.map((segment, index) => (
                  <div key={segment.id} className="grid grid-cols-[1fr_1fr_auto] gap-4 items-end animate-in slide-in-from-left-2 duration-300">
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground ml-1">Start {index + 1}</label>
                      <div className="relative">
                        <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="00:00:00"
                          className="w-full bg-secondary/50 border border-border rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-mono text-sm"
                          value={segment.start}
                          onChange={(e) => updateSegment(index, 'start', e.target.value)}
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground ml-1">End {index + 1}</label>
                      <div className="relative">
                        <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="00:00:30"
                          className="w-full bg-secondary/50 border border-border rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-mono text-sm"
                          value={segment.end}
                          onChange={(e) => updateSegment(index, 'end', e.target.value)}
                        />
                      </div>
                    </div>
                    <button
                      onClick={() => removeSegment(index)}
                      disabled={segments.length === 1}
                      className="h-[42px] w-[42px] flex items-center justify-center rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-30 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </>
            )}

            {/* Bulk Input Mode */}
            {inputMode === 'bulk' && (
              <div className="space-y-3">
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs text-blue-400">
                  <strong>Format:</strong> One timestamp per line<br />
                  Example: <code className="bg-black/30 px-1.5 py-0.5 rounded">00:01:02 - 00:10:00</code>
                </div>

                <textarea
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  placeholder={"00:01:02 - 00:10:00\n00:20:02 - 00:30:00\n00:45:00 - 00:55:00"}
                  className="w-full bg-secondary/50 border border-border rounded-lg py-3 px-4 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-mono text-sm min-h-[120px]"
                  rows={5}
                />

                <button
                  onClick={applyBulkTimestamps}
                  className="w-full py-2.5 rounded-lg bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-all text-sm font-medium"
                >
                  Parse Timestamps ({parseBulkTimestamps(bulkText).length} clips detected)
                </button>

                {/* Show parsed segments preview */}
                {segments.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">Current segments ({segments.length}):</p>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {segments.map((seg, idx) => (
                        <div key={seg.id} className="flex items-center gap-2 text-xs bg-secondary/30 rounded px-2 py-1 font-mono">
                          <span className="text-muted-foreground">#{idx + 1}</span>
                          <span>{seg.start}</span>
                          <span className="text-muted-foreground">→</span>
                          <span>{seg.end}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={handleGenerate}
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
                {statusMessage || "Processing..."}
              </>
            ) : (
              <>
                <Play className="w-5 h-5 fill-current" />
                Generate {segments.length > 1 ? `${segments.length} Shorts` : 'Short'}
              </>
            )}
          </button>
        </div>

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
                <button
                  onClick={() => setQuoteFormat("image")}
                  className={cn(
                    "flex-1 py-1.5 text-sm font-medium rounded-md transition-all",
                    quoteFormat === "image" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  Image
                </button>
                <button
                  onClick={() => setQuoteFormat("video")}
                  className={cn(
                    "flex-1 py-1.5 text-sm font-medium rounded-md transition-all",
                    quoteFormat === "video" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  Video
                </button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">Language</label>
              <select
                value={quoteLang}
                onChange={(e) => setQuoteLang(e.target.value)}
                className="w-full bg-secondary/50 border border-border rounded-lg py-2 px-3 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
              >
                <option value="en">English</option>
                <option value="id">Bahasa Indonesia</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium ml-1">Category</label>
              <select
                value={quoteCategory}
                onChange={(e) => setQuoteCategory(e.target.value)}
                className="w-full bg-secondary/50 border border-border rounded-lg py-2 px-3 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
              >
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
              {isQuoteLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Generate Quote {quoteFormat === "video" ? "Video" : "Image"}
                </>
              )}
            </button>

            {quoteUrl && (
              <div className="md:w-2/3 w-full animate-in fade-in slide-in-from-right-4 duration-500">
                <div className="relative aspect-[9/16] md:aspect-square rounded-lg overflow-hidden border border-border bg-black/50 shadow-lg max-h-[400px] flex items-center justify-center">
                  {quoteUrl.endsWith(".mp4") ? (
                    <video src={quoteUrl} controls autoPlay loop className="max-h-full max-w-full object-contain" />
                  ) : (
                    <img src={quoteUrl} alt="Generated Quote" className="w-full h-full object-cover" />
                  )}
                </div>
                <a
                  href={quoteUrl}
                  download
                  className="mt-2 text-sm text-primary hover:underline flex items-center gap-1 justify-end"
                >
                  <Video className="w-3 h-3" /> Download {quoteFormat === "video" ? "Video" : "Image"}
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Results Area */}
        <div className="space-y-4">
          {projectId && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-xl font-semibold mb-4 text-center md:text-left">Current Project</h2>
              <div className="bg-card/50 border border-border rounded-xl p-6">

                {status === 'completed' && outputFiles.length > 0 ? (
                  <div className="space-y-8">
                    <div className="text-center md:text-left">
                      <div className="px-3 py-1 inline-block rounded-full bg-green-500/10 text-green-500 text-sm font-medium mb-2 border border-green-500/20">
                        Completed
                      </div>
                      <h3 className="text-2xl font-bold">Your Shorts are Ready!</h3>
                      {emailSent && (
                        <p className="text-sm text-muted-foreground mt-2 flex items-center justify-center md:justify-start gap-2">
                          <span>📧</span>
                          Download links have been sent to your email!
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        Project ID: <code className="bg-secondary/50 px-2 py-0.5 rounded font-mono">{projectId}</code>
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {outputFiles.map((file, idx) => (
                        <div key={idx} className="space-y-3 bg-black/20 p-3 rounded-xl border border-border/50">
                          <p className="font-medium text-sm text-center">Clip {idx + 1}</p>
                          <div className="relative w-full aspect-[9/16] bg-black rounded-lg overflow-hidden border border-border shadow-lg ring-1 ring-white/10">
                            <video
                              src={file.url}
                              controls
                              className="w-full h-full object-cover"
                              poster="/placeholder-video.png"
                            />
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
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 space-y-6 text-center">
                    <div className="relative">
                      <div className="w-20 h-20 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xs font-bold text-primary">{Math.round((Date.now() % 3000) / 30)}%</span>
                      </div>
                    </div>
                    <div className="space-y-2 max-w-sm mx-auto">
                      <p className="font-medium text-xl animate-pulse">{statusMessage || "Initializing..."}</p>
                      <p className="text-sm text-muted-foreground">
                        AI is processing your clips sequentially. Please wait...
                      </p>
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}
        </div>
      </div>
    </main >
  );
}
