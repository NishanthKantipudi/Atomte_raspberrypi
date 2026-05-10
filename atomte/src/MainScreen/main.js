/**
 * ATOMTE Kiosk Interface — Complete Single-File Redesign
 * Tailwind CSS · Firebase · localStorage fallback · Responsive (landscape + portrait)
 * NOW WITH SUNLIGHT-READABLE HIGH-CONTRAST TEXT (both orientations)
 *
 * Drop this file in place of your MainScreen component.
 * Make sure Tailwind is configured in your project and the Google Font
 * "Sora" is linked in your public/index.html:
 *   <link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&display=swap" rel="stylesheet">
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { signInWithEmailAndPassword, getAuth } from "firebase/auth";
import { getDatabase, ref, onValue, get } from "firebase/database";
import QRCode from "qrcode.react";
import app from "../firebase/firebase"; // adjust path if needed

// ─── helpers ────────────────────────────────────────────────────────────────

const db = getDatabase(app);

const ls = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
};

function calcProgress(fileData) {
  const raw = fileData?.printprogress;
  if (!raw && raw !== 0) return 0;
  return Math.min(100, Math.max(0, Number(raw)));
}

function calcPrintRatio(fileData) {
  if (!fileData) return { done: 0, total: 1, pct: 0 };
  const pagecount = Number(fileData.pagecount ?? 1);
  const count     = Number(fileData.count     ?? 1);
  const total     = Math.max(1, pagecount * count);
  const raw       = fileData.printed ?? "";
  const done      = raw ? (parseInt(raw.split("/")[0]) || 0) : 0;
  return { done, total, pct: Math.min(100, (done / total) * 100) };
}

// ─── sub-components ─────────────────────────────────────────────────────────

const Bar = ({ pct, className = "" }) => (
  <div className={`relative h-[3px] w-full rounded-full bg-white/8 overflow-hidden ${className}`}>
    <div
      className="absolute inset-y-0 left-0 rounded-full bg-teal-400 transition-all duration-700 ease-out"
      style={{ width: `${pct}%` }}
    />
  </div>
);

const Ad = ({ src, className = "" }) => {
  const vRef = useRef(null);
  return (
    <video
      ref={vRef}
      key={src}
      src={`${src}?nocache=${Math.floor(Date.now() / 60000)}`}
      className={`w-full h-full object-cover ${className}`}
      muted
      loop
      autoPlay
      playsInline
      preload="auto"
    />
  );
};

/** Status pill – now accepts brightMode for high contrast */
const Pill = ({ active, label, brightMode }) => (
  <span
    className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold tracking-[0.12em] uppercase
      ${active
        ? "bg-teal-500/10 text-teal-300 border border-teal-500/30"
        : "bg-red-500/10 text-red-300 border border-red-500/30"}
      ${brightMode ? "!px-5 !py-2 !text-sm !font-extrabold" : ""}`}
  >
    <span
      className={`w-2 h-2 rounded-full ${active ? "bg-teal-400 animate-pulse" : "bg-red-400"}`}
    />
    {label}
  </span>
);

const IdleView = ({ offline, brightMode }) => {
  const text = brightMode ? "text-white/90" : "text-white/60";
  const sub = brightMode ? "text-white/60" : "text-white/25";
  const titleClass = brightMode ? "text-white/95 text-base font-semibold" : "text-white/80 text-sm font-medium";
  const stepClass = brightMode ? "px-6 py-5" : "px-4 py-3.5";
  const numClass = brightMode ? "text-sm font-bold text-teal-300/90" : "text-[11px] font-semibold text-teal-500/60";

  if (offline) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
        <div className="w-14 h-14 rounded-full border border-red-500/30 bg-red-500/8 flex items-center justify-center">
          <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3 3l18 18M8.111 8.111A7.5 7.5 0 0118.874 18M1.5 8.25A15 15 0 0118 4.5M22.5 15.75a15 15 0 01-1.653 1.715M9 18a6 6 0 018.235-5.602" />
          </svg>
        </div>
        <div>
          <p className={`${text} text-sm font-bold`}>No Internet</p>
          <p className={`${sub} text-xs mt-1`}>Check your network connection</p>
        </div>
      </div>
    );
  }

  const steps = [
    { n: "01", title: "Scan the QR code", sub: "Located on the left panel" },
    { n: "02", title: "Upload your files", sub: "PDF, DOCX, JPG and more" },
    { n: "03", title: "Complete payment", sub: "UPI, card or cash accepted" },
    { n: "04", title: "Collect your prints", sub: "Ready in minutes" },
  ];

  return (
    <div className="flex flex-col gap-2 py-2">
      {steps.map((s, i) => (
        <div
          key={s.n}
          className={`flex items-start gap-4 rounded-xl border border-white/5 bg-white/[0.025]
            hover:bg-white/[0.04] transition-colors duration-200 ${stepClass}`}
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <span className={`tabular-nums mt-0.5 w-6 flex-shrink-0 ${numClass}`}>{s.n}</span>
          <div>
            <p className={`leading-snug ${titleClass}`}>{s.title}</p>
            <p className={`text-xs mt-0.5 ${sub}`}>{s.sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

const FileBlock = ({ num, status, dlPct, prtPct, pgDone, pgTotal, compact, brightMode }) => {
  const pct =
    status === "downloading" ? dlPct
    : status === "printing"  ? prtPct
    : status === "printed"   ? 100 : 0;

  const T = {
    printed:     { border: "border-teal-500/20",    bg: "bg-teal-500/[0.06]",    num: "text-teal-400",   sub: "text-teal-500/45",   bar: "bg-teal-400/70" },
    printing:    { border: "border-violet-400/30",  bg: "bg-violet-500/[0.06]",  num: "text-violet-300", sub: "text-violet-400/50", bar: "bg-violet-400"  },
    downloading: { border: "border-amber-400/30",   bg: "bg-amber-500/[0.06]",   num: "text-amber-300",  sub: "text-amber-400/50",  bar: "bg-amber-400"   },
    ready:       { border: "border-white/[0.08]",   bg: "bg-white/[0.025]",      num: "text-white/45",   sub: "text-white/20",      bar: ""               },
    pending:     { border: "border-white/[0.05]",   bg: "bg-transparent",         num: "text-white/18",   sub: "text-white/10",      bar: ""               },
  };

  const t = T[status] || T.pending;
  const isActive = status === "downloading" || status === "printing";

  const StatusIcon = () => {
    if (status === "printed")
      return (
        <svg className="w-3 h-3 text-teal-400/60 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      );
    if (status === "printing")
      return (
        <svg className="w-3 h-3 text-violet-400/70 animate-pulse flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0021 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 00-1.913-.247M6.34 18H5.25A2.25 2.25 0 013 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.056 48.056 0 011.913-.247m10.5 0a48.536 48.536 0 00-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5zm-3 0h.008v.008H15V10.5z" />
        </svg>
      );
    if (status === "downloading")
      return (
        <svg className="w-3 h-3 text-amber-400/70 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
      );
    return null;
  };

  if (compact) {
    return (
      <div
        className={`relative rounded-lg border ${t.border} ${t.bg} overflow-hidden flex flex-col items-center justify-center gap-0.5`}
        style={{ height: "52px" }}
      >
        <span className={`text-sm font-medium tabular-nums leading-none ${t.num} ${brightMode ? "!text-lg !font-bold !text-white/90" : ""}`}>{num}</span>
        {status === "printing"    && <span className={`text-[8px] tabular-nums ${t.sub} ${brightMode ? "!text-white/60 !text-[10px]" : ""}`}>{pgDone}/{pgTotal}</span>}
        {status === "downloading" && <span className={`text-[8px] tabular-nums ${t.sub} ${brightMode ? "!text-white/60 !text-[10px]" : ""}`}>{Math.round(pct)}%</span>}
        {status === "printed"     && <svg className="w-2.5 h-2.5 text-teal-400/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>}
        {(isActive || status === "printed") && (
          <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/5 overflow-hidden">
            <div className={`h-full ${t.bar} transition-all duration-700`} style={{ width: `${pct}%` }} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`relative rounded-xl border ${t.border} ${t.bg} p-2.5 overflow-hidden flex flex-col`}
      style={{ height: "68px" }}
    >
      <div className="flex items-start justify-between">
        <span className={`text-[1.35rem] font-extralight tabular-nums leading-none ${t.num} ${brightMode ? "!text-2xl !font-bold !text-white/90" : ""}`}>{num}</span>
        <StatusIcon />
      </div>
      <div className="mt-auto">
        {status === "printing"    && <span className={`text-[10px] tabular-nums ${t.sub} ${brightMode ? "!text-white/60 !text-xs !font-semibold" : ""}`}>{pgDone} / {pgTotal} pages</span>}
        {status === "downloading" && <span className={`text-[10px] tabular-nums ${t.sub} ${brightMode ? "!text-white/60 !text-xs !font-semibold" : ""}`}>{Math.round(pct)}%</span>}
        {status === "printed"     && <span className={`text-[10px] ${t.sub} ${brightMode ? "!text-white/60 !text-xs !font-bold" : ""}`}>Printed</span>}
        {status === "ready"       && <span className={`text-[10px] ${t.sub} ${brightMode ? "!text-white/60 !text-xs !font-bold" : ""}`}>Downloaded</span>}
        {status === "pending"     && <span className={`text-[10px] ${t.sub} ${brightMode ? "!text-white/60 !text-xs !font-bold" : ""}`}>Waiting</span>}
      </div>
      {(isActive || status === "printed") && (
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/8 overflow-hidden">
          <div className={`h-full ${t.bar} transition-all duration-700`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
};

const PrintFlow = ({ queueCount, userData, fileData, fileData1, prtFileIdx, brightMode }) => {
  const activeScrollRef = useRef(null);

  const n = userData?.totalfiles ?? 1;
  const dlIdx = (userData?.filesArr && fileData?._key)
    ? Math.max(0, userData.filesArr.indexOf(fileData._key))
    : userData?.totaldone ?? 0;

  const prtIdx = (userData?.filesArr && fileData1?._key)
    ? Math.max(0, userData.filesArr.indexOf(fileData1._key))
    : prtFileIdx ?? 0;

  const dlPct = calcProgress(fileData);
  const { done: pgDone, total: pgTotal, pct: prtPct } = calcPrintRatio(fileData1);

  useEffect(() => {
    if (activeScrollRef.current) {
      activeScrollRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [prtIdx, dlIdx]);

  if (!userData) return null;

  const getStatus = (i) => {
    if (i < prtIdx)                        return "printed";
    if (i === prtIdx && fileData1)         return "printing";
    if (i > prtIdx && i < dlIdx)           return "ready";
    if (i === dlIdx && fileData)           return "downloading";
    return "pending";
  };

  const compact = n > 12;
  const cols    = n <= 4  ? 4
                : n <= 8  ? 4
                : n <= 12 ? 4
                : n <= 20 ? 5
                : n <= 30 ? 6
                : 8;

  const doneCount = prtIdx;

  // bright-mode helper classes
  const chipPad = brightMode ? "px-5 py-4" : "px-3.5 py-2.5";
  const avatarClass = brightMode ? "text-white/80 text-sm" : "text-white/50 text-[11px]";
  const nameClass = brightMode ? "text-white/95 text-base font-semibold" : "text-white/70 text-xs font-medium";
  const idClass = brightMode ? "text-white/60 text-sm" : "text-white/25 text-[9px]";
  const queueLabelClass = brightMode ? "text-white/60 text-sm" : "text-white/18 text-[9px]";
  const queueNumClass = brightMode ? "text-white/90 text-base font-semibold" : "text-white/50 text-xs";
  const secPad = brightMode ? "p-5" : "p-2.5";
  const secLabel = brightMode ? "text-white/60 text-sm" : "text-white/25 text-[10px]";
  const secBig = brightMode ? "text-amber-200 text-2xl font-semibold" : "text-amber-300 text-lg font-light";
  const secSmall = brightMode ? "text-white/50 text-sm" : "text-white/18 text-[10px]";
  const secProgressLabel = brightMode ? "text-white/70 text-xs" : "text-white/50 text-[9px]";
  const secProgressVal = brightMode ? "text-amber-300 text-xs font-semibold" : "text-amber-400/60 text-[9px]";
  const headerClass = brightMode ? "text-white/80 text-sm" : "text-white/50 text-[9px]";
  const legendClass = brightMode ? "text-xs text-white/70" : "text-[9px] text-white/45";

  return (
    <div className="space-y-4">
      {/* ── User chip ── */}
      <div className={`flex items-center gap-3 rounded-xl border border-white/[0.07] bg-white/[0.025] ${chipPad}`}>
        <div className="w-7 h-7 rounded-full bg-white/8 border border-white/12 flex items-center justify-center flex-shrink-0">
          <span className={`font-semibold ${avatarClass}`}>
            {(userData.username?.[0] ?? "?").toUpperCase()}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className={`truncate ${nameClass}`}>{userData.username}</p>
          <p className={`font-mono tracking-wider ${idClass}`}>{userData.id}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className={`uppercase tracking-widest ${queueLabelClass}`}>Queue</p>
          <p className={`tabular-nums ${queueNumClass}`}>{queueCount} {queueCount === 1 ? "job" : "jobs"}</p>
        </div>
      </div>

      {/* ── Active operations ── */}
      <div className="grid grid-cols-2 gap-2">
        {/* Downloading */}
        <div className={`rounded-xl border border-amber-500/20 bg-amber-500/[0.05] ${secPad}`}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className="w-4 h-4 rounded-full bg-amber-500/15 border border-amber-400/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-2 h-2 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
            </div>
            {fileData?.name && (
              <p className={`text-[10px] text-amber-300/50 mb-1.5 truncate ${brightMode ? "!text-sm !text-amber-200/70" : ""}`} title={fileData.name}>
                {fileData.name}
              </p>
            )}
          </div>
          {fileData ? (
            <>
              <div className="flex items-baseline gap-1 mb-1.5">
                <span className={secLabel}>File</span>
                <span className={`tabular-nums leading-none ${secBig}`}>{dlIdx + 1}</span>
                <span className={secSmall}>/ {n}</span>
              </div>
              <div className="space-y-1">
                <div className="h-[2px] rounded-full bg-white/8 overflow-hidden">
                  <div className="h-full bg-amber-400 rounded-full transition-all duration-700" style={{ width: `${dlPct}%` }} />
                </div>
                <div className="flex justify-between text-[9px]">
                  <span className={secProgressLabel}>Transferring…</span>
                  <span className={`tabular-nums font-medium ${secProgressVal}`}>{Math.round(dlPct)}%</span>
                </div>
              </div>
            </>
          ) : (
            <p className={brightMode ? "text-white/50 text-sm" : "text-white/15 text-[10px]"}>Idle</p>
          )}
        </div>

        {/* Printing */}
        <div className={`rounded-xl border border-violet-400/20 bg-violet-500/[0.05] ${secPad}`}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className="w-4 h-4 rounded-full bg-violet-500/15 border border-violet-400/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-2 h-2 text-violet-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0021 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 00-1.913-.247M6.34 18H5.25A2.25 2.25 0 013 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.056 48.056 0 011.913-.247m10.5 0a48.536 48.536 0 00-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5zm-3 0h.008v.008H15V10.5z" />
              </svg>
            </div>
            {fileData1?.name && (
              <p className={`text-[10px] text-violet-300/50 mb-1.5 truncate ${brightMode ? "!text-sm !text-violet-200/70" : ""}`} title={fileData1.name}>
                {fileData1.name}
              </p>
            )}
          </div>
          {fileData1 ? (
            <>
              <div className="flex items-baseline gap-1 mb-1.5">
                <span className={secLabel}>File</span>
                <span className={`tabular-nums leading-none ${brightMode ? "text-violet-200 text-2xl font-semibold" : "text-violet-300 text-lg font-light"}`}>{prtIdx + 1}</span>
                <span className={secSmall}>/ {n}</span>
              </div>
              <div className="space-y-1">
                <div className="h-[2px] rounded-full bg-white/8 overflow-hidden">
                  <div className="h-full bg-violet-400 rounded-full transition-all duration-700" style={{ width: `${prtPct}%` }} />
                </div>
                <div className="flex justify-between text-[9px]">
                  <span className={secProgressLabel}>Page</span>
                  <span className={`tabular-nums font-medium ${brightMode ? "text-violet-300 text-xs font-semibold" : "text-violet-400/60 text-[9px]"}`}>{pgDone} / {pgTotal}</span>
                </div>
              </div>
            </>
          ) : (
            <p className={brightMode ? "text-white/50 text-sm" : "text-white/15 text-[10px]"}>Waiting…</p>
          )}
        </div>
      </div>

      {/* ── Files grid ── */}
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <p className={`uppercase tracking-[0.15em] ${headerClass}`}>
            All files — {doneCount} of {n} done
          </p>
          <div className="flex items-center gap-3">
            {[
              { dot: "bg-teal-400/70",   label: "Printed"    },
              { dot: "bg-violet-400",    label: "Printing"   },
              { dot: "bg-amber-400",     label: "Downloading"},
              { dot: "bg-white/20",      label: "Pending"    },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1">
                <div className={`w-1.5 h-1.5 rounded-full ${l.dot}`} />
                <span className={legendClass}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: n }, (_, i) => {
            const status = getStatus(i);
            const isActiveCell = status === "printing" || status === "downloading";
            return (
              <div key={i} ref={isActiveCell ? activeScrollRef : null}>
                <FileBlock
                  num={i + 1}
                  status={status}
                  dlPct={dlPct}
                  prtPct={prtPct}
                  pgDone={pgDone}
                  pgTotal={pgTotal}
                  compact={compact}
                  brightMode={brightMode}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const ErrorOverlay = ({ error, mobile, videoSrc }) => {
  if (!error) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/95 p-10">
      <div className="w-full h-full bg-zinc-900 border border-red-500/20 rounded-2xl overflow-hidden flex flex-col">
        <div className="px-8 py-6 text-center border-b border-white/5">
          <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
            <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <p className="text-white/30 text-[10px] uppercase tracking-[0.15em] mb-1">Printer Alert</p>
          <p className="text-white text-xl font-light">{error}</p>
        </div>
        <div className="px-8 py-5 text-center border-b border-white/5">
          <p className="text-white/25 text-[10px] uppercase tracking-widest mb-1">For assistance call</p>
          <p className="text-teal-400 text-3xl font-light tracking-wider">{mobile}</p>
          <p className="text-white/20 text-xs mt-1">Available 24 / 7</p>
        </div>
        {videoSrc && (
          <div className="flex-1">
            <Ad src={videoSrc} className="w-full h-full object-cover" />
          </div>
        )}
      </div>
    </div>
  );
};

// ─── main app ────────────────────────────────────────────────────────────────

export default function KioskApp() {
  const [code, setCode] = useState(null);
  const [loggedIn, setLoggedIn] = useState(false);
  const [mobile, setMobile] = useState(() => ls.get("atomte_mobile") ?? "");
  const [printer, setPrinter] = useState(null);
  const [queueCount, setQueueCount] = useState(0);
  const [userData, setUserData] = useState(null);
  const [fileData, setFileData] = useState(null);
  const [fileData1, setFileData1] = useState(null);
  const [printerError, setPrinterError] = useState(null);
  const [errVideo, setErrVideo] = useState("");
  const [offline, setOffline] = useState(false);
  const innerUnsubs = useRef([]);
  const [prtFileIdx, setPrtFileIdx] = useState(0);

  const [portrait, setPortrait] = useState(window.innerHeight > window.innerWidth);
  useEffect(() => {
    const check = () => setPortrait(window.innerHeight > window.innerWidth);
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    const check = async () => {
      if (!navigator.onLine) { setOffline(true); return; }
      try {
        await fetch("https://www.gstatic.com/generate_204", { method: "GET", mode: "no-cors" });
        setOffline(false);
      } catch { setOffline(true); }
    };
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const c = params.get("code");
    if (c) setCode(c);
  }, []);

  useEffect(() => {
    if (!code || loggedIn) return;
    signInWithEmailAndPassword(getAuth(app), `${code}@gmail.com`, code)
      .then(() => setLoggedIn(true))
      .catch(console.error);
  }, [code, loggedIn]);

  useEffect(() => {
    if (!code) return;
    return onValue(ref(db, `Printers/${code}/details`), (snap) => {
      if (snap.val()) setPrinter(snap.val());
    });
  }, [code]);

  useEffect(() => {
    if (!code) return;
    get(ref(db, `Printers/${code}/details/service_number`))
      .then((snap) => {
        if (snap.exists()) {
          const m = snap.val();
          setMobile(m);
          ls.set("atomte_mobile", m);
        }
      })
      .catch(console.error);
  }, [code]);

  useEffect(() => {
    if (!code) return;
    const outerUnsub = onValue(ref(db, `Printers/${code}/printstodo`), (snap) => {
      innerUnsubs.current.forEach(fn => fn());
      innerUnsubs.current = [];
      setFileData(null);
      setFileData1(null);
      setUserData(null);
      const data = snap.val();
      if (!data) { setQueueCount(0); return; }
      setQueueCount(Object.keys(data).length);
      const curr = Object.values(data)[0];
      const user = curr.user;
      if (!curr.files) return;
      const files  = curr.files.split(",");
      const dlIdx  = (curr.printing ?? 1) - 1;
      const prtIdx = (curr.done_printing ?? 0);
      setPrtFileIdx(prtIdx);
      get(ref(db, `users/${user}/details`)).then((snap) => {
        const u = snap.val();
        if (!u) return;
        setUserData({
          username:   u.name,
          id:         u.atomte_id,
          totalfiles: files.length,
          totaldone:  dlIdx,
          left:       files.length - dlIdx,
          filesArr:   files,
        });
      });
      if (files[dlIdx]) {
        const dlKey = files[dlIdx];
        const u1 = onValue(ref(db, `users/${user}/printsdetails/${dlKey}`), (s) => {
          if (s.val()) setFileData({ ...s.val(), _key: dlKey });
        });
        innerUnsubs.current.push(u1);
      }
      if (files[prtIdx]) {
        const prtKey = files[prtIdx];
        const u2 = onValue(ref(db, `users/${user}/printsdetails/${prtKey}`), (s) => {
          if (s.val()) setFileData1({ ...s.val(), _key: prtKey });
        });
        innerUnsubs.current.push(u2);
      }
    });
    return () => {
      outerUnsub();
      innerUnsubs.current.forEach(fn => fn());
      innerUnsubs.current = [];
    };
  }, [code]);

  useEffect(() => {
    if (!code) return;
    return onValue(ref(db, `Printers/${code}/details/status_message`), (snap) => {
      const msg = snap.val();
      if (msg && !msg.toLowerCase().includes("active")) {
        setPrinterError(msg);
        const m = msg.toLowerCase();
        if (m.includes("jammed"))      setErrVideo("http://localhost:7000/videos/jammed.mp4");
        else if (m.includes("empty"))  setErrVideo("http://localhost:7000/videos/empty.mp4");
        else if (m.includes("toner"))  setErrVideo("http://localhost:7000/videos/tonor.mp4");
        else if (m.includes("power"))  setErrVideo("http://localhost:7000/videos/power.mp4");
        else                           setErrVideo("http://localhost:7000/videos/error.mp4");
      } else {
        setPrinterError(null);
        setErrVideo("");
      }
    });
  }, [code]);

  const isActive = printer?.status?.toLowerCase() === "active";
  const printing = !!fileData;

  // Universal high‑contrast mode for both orientations
  const BRIGHT_MODE = true;

  const QRBlock = ({ size = 160 }) => (
    <div className="flex flex-col items-center gap-3">
      <div className="bg-white p-2.5 rounded-xl">
        {code ? (
          <QRCode
            value={`https://atomte.com/autoprint?code=${code}`}
            size={size}
            level="H"
            includeMargin={false}
            bgColor="#ffffff"
            fgColor="#000000"
          />
        ) : (
          <div style={{ width: size, height: size }} className="bg-white/10 animate-pulse rounded" />
        )}
      </div>
      <p className="text-white/70 text-sm uppercase tracking-[0.15em] font-semibold">Scan to Print</p>
    </div>
  );

  const PrinterCard = () => (
    <div className="space-y-2">
      <div>
        <p className="text-white/60 text-sm uppercase tracking-[0.15em] mb-1">Printer</p>
        <p className="text-white/95 text-1xl font-bold leading-tight">
          {printer?.name ?? code ?? "—"}
        </p>
        {code && (
          <p className="text-white/60 text-sm font-mono mt-0.5">#{code}</p>
        )}
        {printer?.description && (
          <p className="text-white/70 text-sm mt-1 leading-relaxed">{printer.description}</p>
        )}
      </div>
      <Pill active={isActive} label={printer?.status ?? "Loading…"} brightMode={BRIGHT_MODE} />
    </div>
  );

  const MobileBlock = ({ big = false }) => (
    <div className={big ? "text-right" : ""}>
      <p className="text-white/70 text-sm uppercase tracking-[0.15em] mb-1 font-semibold">
        Assistance 24 / 7
      </p>
      <p className={`text-teal-200 font-bold tracking-wider leading-none ${big ? "text-6xl" : "text-5xl"}`}>
        {mobile || "—"}
      </p>
    </div>
  );

  // ═══ PORTRAIT ═══
  if (portrait) {
    return (
      <div
        className="h-screen w-screen bg-[#09090b] text-white overflow-hidden flex flex-col"
        style={{ fontFamily: "'Sora', sans-serif" }}
      >
        <div className="flex items-start justify-between px-8 py-7 border-b border-white/[0.05]">
          <div>
            <h1 className="text-5xl font-bold tracking-tight text-white">ATOMTE</h1>
            <p className="text-white/70 text-sm tracking-[0.2em] uppercase mt-1">Automated Print Service</p>
          </div>
          <MobileBlock big={false} />
        </div>

        <div className="flex gap-7 px-8 py-6 border-b border-white/[0.05] items-stretch">
          <div className="flex flex-col justify-center gap-4">
            <QRBlock size={160} />
            <div className="h-px bg-white/[0.05] w-full" />
            <PrinterCard />
          </div>
          <div className="w-px bg-white/[0.05] self-stretch" />
          <div className="flex-1 overflow-y-auto max-h-[420px]">
            <p className="text-white/70 text-sm uppercase tracking-[0.15em] mb-3 font-semibold">Print Status</p>
            {printing ? (
              <PrintFlow
                queueCount={queueCount}
                userData={userData}
                fileData={fileData}
                fileData1={fileData1}
                prtFileIdx={prtFileIdx}
                brightMode={BRIGHT_MODE}
              />
            ) : (
              <IdleView offline={offline} brightMode={BRIGHT_MODE} />
            )}
          </div>
        </div>

        <div className="h-1/2 border-t border-white/[0.05] flex-shrink-0 flex flex-col">
          <div className="flex-1 border-b border-white/[0.05] overflow-hidden">
            <Ad src="http://localhost:7000/videos/ad1.mp4" />
          </div>
          <div className="flex-1 flex">
            <div className="flex-1 overflow-hidden">
              <Ad src="http://localhost:7000/videos/ad2.mp4" />
            </div>
            <div className="w-px bg-white/[0.05] flex-shrink-0" />
            <div className="flex-1 overflow-hidden">
              <Ad src="http://localhost:7000/videos/ad3.mp4" />
            </div>
          </div>
        </div>

        <ErrorOverlay error={printerError} mobile={mobile} videoSrc={errVideo} />
      </div>
    );
  }

  // ═══ LANDSCAPE ═══
  return (
    <div
      className="h-screen w-screen bg-[#09090b] text-white overflow-hidden flex flex-col"
      style={{ fontFamily: "'Sora', sans-serif" }}
    >
      <div className="flex flex-1 overflow-hidden">
        <div className="w-[260px] flex-shrink-0 border-r border-white/[0.05] flex flex-col">
          <div className="px-6 pt-4 pb-5 border-b border-white/[0.05]">
            <h1 className="text-3xl font-bold tracking-tight text-white">ATOMTE</h1>
            <p className="text-white/70 text-sm tracking-[0.2em] uppercase mt-1">Print Service</p>
          </div>
          <div className="px-6 py-6 border-b border-white/[0.05]">
            <QRBlock size={200} />
          </div>
          <div className="px-6 py-5 flex-1">
            <PrinterCard />
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-10 py-5 border-b border-white/[0.05] flex items-center justify-between flex-shrink-0">
            <div>
              {printing && queueCount > 0 && (
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-teal-400 animate-pulse" />
                  <span className="text-teal-300/90 text-xl font-semibold">
                    {queueCount} {queueCount === 1 ? "job" : "jobs"} in queue
                  </span>
                </div>
              )}
              {printing && (
                <p className="text-white/70 text-base uppercase tracking-[0.15em] mt-1.5 font-medium">Print Status</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-white/70 text-sm uppercase tracking-[0.15em] mb-2 font-semibold">Assistance 24 / 7</p>
              <p className="text-teal-200 font-bold tracking-wider leading-none text-3xl">
                {mobile || "—"}
              </p>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-10 py-6">
            {printing ? (
              <PrintFlow
                queueCount={queueCount}
                userData={userData}
                fileData={fileData}
                fileData1={fileData1}
                prtFileIdx={prtFileIdx}
                brightMode={BRIGHT_MODE}
              />
            ) : (
              <IdleView offline={offline} brightMode={BRIGHT_MODE} />
            )}
          </div>
        </div>
      </div>

      <div className="h-44 flex-shrink-0 border-t border-white/[0.05] flex">
        <div className="flex-1 overflow-hidden">
          <Ad src="http://localhost:7000/videos/ad2.mp4" />
        </div>
        <div className="w-px bg-white/[0.05] flex-shrink-0" />
        <div className="flex-1 overflow-hidden">
          <Ad src="http://localhost:7000/videos/ad3.mp4" />
        </div>
      </div>

      <ErrorOverlay error={printerError} mobile={mobile} videoSrc={errVideo} />
    </div>
  );
}