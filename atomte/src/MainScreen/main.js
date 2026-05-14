/**
 * ATOMTE Kiosk Interface — Complete Single-File Redesign
 * Tailwind CSS · Firebase · localStorage fallback · Responsive (landscape + portrait)
 *
 * Theme is driven by Firebase at Printers/{code}/details/theme_type:
 *   0 → always dark
 *   1 → always light
 *   2 → light from 05:00–19:00, dark otherwise (re-evaluated every minute)
 *
 * The fetched value is cached in localStorage under "atomte_theme_type".
 * Only colors change between themes — all layout, spacing and sizing is identical.
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

// ─── Theme ──────────────────────────────────────────────────────────────────

/**
 * Compute whether the UI should be dark given the raw theme_type value.
 *   0 → always dark
 *   1 → always light
 *   2 → dark outside 05:00–19:00
 */
function computeIsDark(themeType) {
  if (themeType === 1) return false;
  if (themeType === 0) return true;
  const h = new Date().getHours();
  return h < 5 || h >= 19;
}

/**
 * Returns a flat object of Tailwind class strings that components
 * consume via `tk.xxx`. Only colors/bg/border values differ between
 * dark and light — sizes, layout and spacing never appear here.
 */
function makeTheme(isDark) {
  if (isDark) {
    return {
      // ── page ──
      pageBg:         "bg-[#09090b]",
      pageText:       "text-white",

      // ── borders ──
      borderXFaint:   "border-white/[0.05]",
      borderFaint:    "border-white/[0.07]",
      borderSoft:     "border-white/[0.12]",

      // ── dividers (bg) ──
      divXFaint:      "bg-white/[0.05]",

      // ── card/surface backgrounds ──
      cardBg:         "bg-white/[0.025]",
      cardBgHover:    "hover:bg-white/[0.04]",
      subtleBg:       "bg-white/[0.08]",
      progTrack:      "bg-white/[0.08]",

      // ── text scale ──
      textBright:     "text-white/95",
      textStrong:     "text-white/80",
      textMed:        "text-white/70",
      textSoft:       "text-white/60",
      textMuted:      "text-white/50",
      textFaint:      "text-white/25",
      textVeryFaint:  "text-white/[0.18]",
      textGhost:      "text-white/10",

      // ── teal ──
      tealBright:     "text-teal-200",
      tealMed:        "text-teal-300",
      tealSoft:       "text-teal-400",
      tealFaint:      "text-teal-500/60",
      tealBg:         "bg-teal-500/10",
      tealBorder:     "border-teal-500/30",

      // ── violet ──
      violetText:     "text-violet-300",
      violetBig:      "text-violet-200",
      violetBg:       "bg-violet-500/[0.06]",
      violetBorder:   "border-violet-400/30",
      violetIconBg:   "bg-violet-500/[0.15]",
      violetIconBorder:"border-violet-400/20",
      violetIconColor:"text-violet-400",
      violetProgress: "text-violet-300",
      violetNameText: "text-violet-200/70",

      // ── amber ──
      amberBig:       "text-amber-200",
      amberMed:       "text-amber-300",
      amberBg:        "bg-amber-500/[0.06]",
      amberBorder:    "border-amber-500/20",
      amberIconBg:    "bg-amber-500/[0.15]",
      amberIconBorder:"border-amber-400/20",
      amberIconColor: "text-amber-400",
      amberNameText:  "text-amber-200/70",

      // ── red ──
      redText:        "text-red-400",
      redBg:          "bg-red-500/[0.08]",
      redBorder:      "border-red-500/30",
      redAlertBorder: "border-red-500/20",
      redIconColor:   "text-red-400",

      // ── pill ──
      pillActiveBg:     "bg-teal-500/10",
      pillActiveText:   "text-teal-300",
      pillActiveBorder: "border-teal-500/30",
      pillInactiveBg:   "bg-red-500/10",
      pillInactiveText: "text-red-300",
      pillInactiveBorder:"border-red-500/30",

      // ── avatar ──
      avatarBg:       "bg-white/[0.08]",
      avatarBorder:   "border-white/[0.12]",
      avatarText:     "text-white/80",

      // ── misc text labels (include size; used verbatim) ──
      stepNum:    "text-sm font-bold text-teal-300/90",
      stepTitle:  "text-white/95 text-base font-semibold",
      stepSub:    "text-white/60",
      stepBg:     "bg-white/[0.025]",
      stepBorder: "border-white/[0.05]",

      offlineText:"text-white/90",
      offlineSub: "text-white/60",

      headerText: "text-white/80",
      legendText: "text-white/70",

      // ── file block statuses ──
      fileStatus: {
        printed:     { border:"border-teal-500/20",   bg:"bg-teal-500/[0.06]",   num:"text-teal-400",   sub:"text-teal-500/45",   bar:"bg-teal-400/70"  },
        printing:    { border:"border-violet-400/30", bg:"bg-violet-500/[0.06]", num:"text-violet-300", sub:"text-violet-400/50", bar:"bg-violet-400"   },
        downloading: { border:"border-amber-400/30",  bg:"bg-amber-500/[0.06]",  num:"text-amber-300",  sub:"text-amber-400/50",  bar:"bg-amber-400"    },
        ready:       { border:"border-white/[0.08]",  bg:"bg-white/[0.025]",     num:"text-white/45",   sub:"text-white/20",      bar:""                },
        pending:     { border:"border-white/[0.05]",  bg:"bg-transparent",       num:"text-white/[0.18]",sub:"text-white/10",     bar:""                },
      },
    };
  }

  // ── LIGHT THEME ────────────────────────────────────────────────────────────
  return {
    // ── page ──
    pageBg:         "bg-zinc-100",
    pageText:       "text-zinc-900",

    // ── borders ──
    borderXFaint:   "border-zinc-200",
    borderFaint:    "border-zinc-200",
    borderSoft:     "border-zinc-300",

    // ── dividers (bg) ──
    divXFaint:      "bg-zinc-200",

    // ── card/surface backgrounds ──
    cardBg:         "bg-white",
    cardBgHover:    "hover:bg-zinc-50",
    subtleBg:       "bg-zinc-100",
    progTrack:      "bg-zinc-200",

    // ── text scale ──
    textBright:     "text-zinc-900",
    textStrong:     "text-zinc-800",
    textMed:        "text-zinc-500",
    textSoft:       "text-zinc-500",
    textMuted:      "text-zinc-400",
    textFaint:      "text-zinc-400",
    textVeryFaint:  "text-zinc-300",
    textGhost:      "text-zinc-200",

    // ── teal ──
    tealBright:     "text-teal-700",
    tealMed:        "text-teal-600",
    tealSoft:       "text-teal-500",
    tealFaint:      "text-teal-400",
    tealBg:         "bg-teal-50",
    tealBorder:     "border-teal-300",

    // ── violet ──
    violetText:     "text-violet-600",
    violetBig:      "text-violet-600",
    violetBg:       "bg-violet-50",
    violetBorder:   "border-violet-200",
    violetIconBg:   "bg-violet-100",
    violetIconBorder:"border-violet-200",
    violetIconColor:"text-violet-500",
    violetProgress: "text-violet-600",
    violetNameText: "text-violet-600/70",

    // ── amber ──
    amberBig:       "text-amber-700",
    amberMed:       "text-amber-600",
    amberBg:        "bg-amber-50",
    amberBorder:    "border-amber-200",
    amberIconBg:    "bg-amber-100",
    amberIconBorder:"border-amber-200",
    amberIconColor: "text-amber-500",
    amberNameText:  "text-amber-600/70",

    // ── red ──
    redText:        "text-red-500",
    redBg:          "bg-red-50",
    redBorder:      "border-red-200",
    redAlertBorder: "border-red-300",
    redIconColor:   "text-red-500",

    // ── pill ──
    pillActiveBg:     "bg-teal-50",
    pillActiveText:   "text-teal-700",
    pillActiveBorder: "border-teal-300",
    pillInactiveBg:   "bg-red-50",
    pillInactiveText: "text-red-600",
    pillInactiveBorder:"border-red-200",

    // ── avatar ──
    avatarBg:       "bg-zinc-100",
    avatarBorder:   "border-zinc-300",
    avatarText:     "text-zinc-600",

    // ── misc text labels ──
    stepNum:    "text-sm font-bold text-teal-500",
    stepTitle:  "text-zinc-900 text-base font-semibold",
    stepSub:    "text-zinc-400",
    stepBg:     "bg-white",
    stepBorder: "border-zinc-200",

    offlineText:"text-zinc-800",
    offlineSub: "text-zinc-500",

    headerText: "text-zinc-700",
    legendText: "text-zinc-500",

    // ── file block statuses ──
    fileStatus: {
      printed:     { border:"border-teal-200",   bg:"bg-teal-50",   num:"text-teal-600",   sub:"text-teal-500",   bar:"bg-teal-500"   },
      printing:    { border:"border-violet-200", bg:"bg-violet-50", num:"text-violet-600", sub:"text-violet-500", bar:"bg-violet-500" },
      downloading: { border:"border-amber-200",  bg:"bg-amber-50",  num:"text-amber-600",  sub:"text-amber-500",  bar:"bg-amber-500"  },
      ready:       { border:"border-zinc-200",   bg:"bg-white",     num:"text-zinc-400",   sub:"text-zinc-300",   bar:""              },
      pending:     { border:"border-zinc-100",   bg:"bg-zinc-50",   num:"text-zinc-300",   sub:"text-zinc-200",   bar:""              },
    },
  };
}

// ─── sub-components ─────────────────────────────────────────────────────────

const Bar = ({ pct, className = "", tk }) => (
  <div className={`relative h-[3px] w-full rounded-full overflow-hidden ${tk.progTrack} ${className}`}>
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

const Pill = ({ active, label, tk }) => (
  <span
    className={`inline-flex items-center gap-2 px-5 py-2 rounded-full text-sm font-extrabold tracking-[0.12em] uppercase border
      ${active
        ? `${tk.pillActiveBg} ${tk.pillActiveText} ${tk.pillActiveBorder}`
        : `${tk.pillInactiveBg} ${tk.pillInactiveText} ${tk.pillInactiveBorder}`}`}
  >
    <span className={`w-2 h-2 rounded-full ${active ? "bg-teal-400 animate-pulse" : "bg-red-400"}`} />
    {label}
  </span>
);

const IdleView = ({ offline, tk }) => {
  if (offline) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
        <div className={`w-14 h-14 rounded-full border ${tk.redBorder} ${tk.redBg} flex items-center justify-center`}>
          <svg className={`w-6 h-6 ${tk.redText}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M3 3l18 18M8.111 8.111A7.5 7.5 0 0118.874 18M1.5 8.25A15 15 0 0118 4.5M22.5 15.75a15 15 0 01-1.653 1.715M9 18a6 6 0 018.235-5.602" />
          </svg>
        </div>
        <div>
          <p className={`${tk.offlineText} text-sm font-bold`}>No Internet</p>
          <p className={`${tk.offlineSub} text-xs mt-1`}>Check your network connection</p>
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
          className={`flex items-start gap-4 rounded-xl border ${tk.stepBorder} ${tk.stepBg}
            ${tk.cardBgHover} transition-colors duration-200 px-6 py-5`}
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <span className={`tabular-nums mt-0.5 w-6 flex-shrink-0 ${tk.stepNum}`}>{s.n}</span>
          <div>
            <p className={`leading-snug ${tk.stepTitle}`}>{s.title}</p>
            <p className={`text-xs mt-0.5 ${tk.stepSub}`}>{s.sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

const FileBlock = ({ num, status, dlPct, prtPct, pgDone, pgTotal, compact, tk }) => {
  const pct =
    status === "downloading" ? dlPct
    : status === "printing"  ? prtPct
    : status === "printed"   ? 100 : 0;

  const t = tk.fileStatus[status] || tk.fileStatus.pending;
  const isActive = status === "downloading" || status === "printing";

  const StatusIcon = () => {
    if (status === "printed")
      return (
        <svg className={`w-3 h-3 ${t.sub} flex-shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      );
    if (status === "printing")
      return (
        <svg className={`w-3 h-3 ${t.sub} animate-pulse flex-shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0021 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 00-1.913-.247M6.34 18H5.25A2.25 2.25 0 013 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.056 48.056 0 011.913-.247m10.5 0a48.536 48.536 0 00-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5zm-3 0h.008v.008H15V10.5z" />
        </svg>
      );
    if (status === "downloading")
      return (
        <svg className={`w-3 h-3 ${t.sub} flex-shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
        <span className={`text-lg font-bold tabular-nums leading-none ${t.num}`}>{num}</span>
        {status === "printing"    && <span className={`text-[10px] tabular-nums ${t.sub}`}>{pgDone}/{pgTotal}</span>}
        {status === "downloading" && <span className={`text-[10px] tabular-nums ${t.sub}`}>{Math.round(pct)}%</span>}
        {status === "printed"     && <svg className={`w-2.5 h-2.5 ${t.sub}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>}
        {(isActive || status === "printed") && (
          <div className={`absolute bottom-0 left-0 right-0 h-[2px] ${tk.progTrack} overflow-hidden`}>
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
        <span className={`text-2xl font-bold tabular-nums leading-none ${t.num}`}>{num}</span>
        <StatusIcon />
      </div>
      <div className="mt-auto">
        {status === "printing"    && <span className={`text-xs font-semibold tabular-nums ${t.sub}`}>{pgDone} / {pgTotal} pages</span>}
        {status === "downloading" && <span className={`text-xs font-semibold tabular-nums ${t.sub}`}>{Math.round(pct)}%</span>}
        {status === "printed"     && <span className={`text-xs font-bold ${t.sub}`}>Printed</span>}
        {status === "ready"       && <span className={`text-xs font-bold ${t.sub}`}>Downloaded</span>}
        {status === "pending"     && <span className={`text-xs font-bold ${t.sub}`}>Waiting</span>}
      </div>
      {(isActive || status === "printed") && (
        <div className={`absolute bottom-0 left-0 right-0 h-[2px] ${tk.progTrack} overflow-hidden`}>
          <div className={`h-full ${t.bar} transition-all duration-700`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
};

const PrintFlow = ({ queueCount, userData, fileData, fileData1, prtFileIdx, tk }) => {
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

  return (
    <div className="space-y-4">
      {/* ── User chip ── */}
      <div className={`flex items-center gap-3 rounded-xl border ${tk.borderFaint} ${tk.cardBg} px-5 py-4`}>
        <div className={`w-7 h-7 rounded-full ${tk.avatarBg} border ${tk.avatarBorder} flex items-center justify-center flex-shrink-0`}>
          <span className={`font-semibold text-sm ${tk.avatarText}`}>
            {(userData.username?.[0] ?? "?").toUpperCase()}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className={`truncate text-base font-semibold ${tk.textBright}`}>{userData.username}</p>
          <p className={`font-mono tracking-wider text-sm ${tk.textSoft}`}>{userData.id}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className={`uppercase tracking-widest text-sm ${tk.textSoft}`}>Queue</p>
          <p className={`tabular-nums text-base font-semibold ${tk.textBright}`}>{queueCount} {queueCount === 1 ? "job" : "jobs"}</p>
        </div>
      </div>

      {/* ── Active operations ── */}
      <div className="grid grid-cols-2 gap-2">
        {/* Downloading */}
        <div className={`rounded-xl border ${tk.amberBorder} ${tk.amberBg} p-5`}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className={`w-4 h-4 rounded-full ${tk.amberIconBg} border ${tk.amberIconBorder} flex items-center justify-center flex-shrink-0`}>
              <svg className={`w-2 h-2 ${tk.amberIconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
            </div>
            {fileData?.name && (
              <p className={`text-sm mb-1.5 truncate ${tk.amberNameText}`} title={fileData.name}>
                {fileData.name}
              </p>
            )}
          </div>
          {fileData ? (
            <>
              <div className="flex items-baseline gap-1 mb-1.5">
                <span className={`text-sm ${tk.textSoft}`}>File</span>
                <span className={`tabular-nums leading-none text-2xl font-semibold ${tk.amberBig}`}>{dlIdx + 1}</span>
                <span className={`text-sm ${tk.textMuted}`}>/ {n}</span>
              </div>
              <div className="space-y-1">
                <div className={`h-[2px] rounded-full ${tk.progTrack} overflow-hidden`}>
                  <div className="h-full bg-amber-400 rounded-full transition-all duration-700" style={{ width: `${dlPct}%` }} />
                </div>
                <div className="flex justify-between">
                  <span className={`text-xs ${tk.textMed}`}>Transferring…</span>
                  <span className={`tabular-nums font-semibold text-xs ${tk.amberMed}`}>{Math.round(dlPct)}%</span>
                </div>
              </div>
            </>
          ) : (
            <p className={`text-sm ${tk.textMuted}`}>Idle</p>
          )}
        </div>

        {/* Printing */}
        <div className={`rounded-xl border ${tk.violetBorder} ${tk.violetBg} p-5`}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <div className={`w-4 h-4 rounded-full ${tk.violetIconBg} border ${tk.violetIconBorder} flex items-center justify-center flex-shrink-0`}>
              <svg className={`w-2 h-2 ${tk.violetIconColor} animate-pulse`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0021 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 00-1.913-.247M6.34 18H5.25A2.25 2.25 0 013 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.056 48.056 0 011.913-.247m10.5 0a48.536 48.536 0 00-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5zm-3 0h.008v.008H15V10.5z" />
              </svg>
            </div>
            {fileData1?.name && (
              <p className={`text-sm mb-1.5 truncate ${tk.violetNameText}`} title={fileData1.name}>
                {fileData1.name}
              </p>
            )}
          </div>
          {fileData1 ? (
            <>
              <div className="flex items-baseline gap-1 mb-1.5">
                <span className={`text-sm ${tk.textSoft}`}>File</span>
                <span className={`tabular-nums leading-none text-2xl font-semibold ${tk.violetBig}`}>{prtIdx + 1}</span>
                <span className={`text-sm ${tk.textMuted}`}>/ {n}</span>
              </div>
              <div className="space-y-1">
                <div className={`h-[2px] rounded-full ${tk.progTrack} overflow-hidden`}>
                  <div className="h-full bg-violet-400 rounded-full transition-all duration-700" style={{ width: `${prtPct}%` }} />
                </div>
                <div className="flex justify-between">
                  <span className={`text-xs ${tk.textMed}`}>Page</span>
                  <span className={`tabular-nums font-semibold text-xs ${tk.violetProgress}`}>{pgDone} / {pgTotal}</span>
                </div>
              </div>
            </>
          ) : (
            <p className={`text-sm ${tk.textMuted}`}>Waiting…</p>
          )}
        </div>
      </div>

      {/* ── Files grid ── */}
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <p className={`uppercase tracking-[0.15em] text-sm ${tk.headerText}`}>
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
                <span className={`text-xs ${tk.legendText}`}>{l.label}</span>
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
                  tk={tk}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// ErrorOverlay is intentionally kept dark in both themes — it's a full-screen
// alert that must be readable regardless of the ambient theme.
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
  // ── core state ──
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

  // ── theme state ──
  // Initialise from localStorage so the correct theme shows on first paint,
  // before the Firebase value arrives.
  const [themeType, setThemeType] = useState(() => {
    const saved = ls.get("atomte_theme_type");
    return saved !== null ? Number(saved) : 0;
  });
  const [isDark, setIsDark] = useState(() => {
    const saved = ls.get("atomte_theme_type");
    return computeIsDark(saved !== null ? Number(saved) : 0);
  });

  // Derive theme object from isDark (recomputed on every render, very cheap).
  const tk = makeTheme(isDark);

  // ── orientation ──
  const [portrait, setPortrait] = useState(window.innerHeight > window.innerWidth);
  useEffect(() => {
    const check = () => setPortrait(window.innerHeight > window.innerWidth);
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // ── connectivity ──
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

  // ── ?code= param ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const c = params.get("code");
    if (c) setCode(c);
  }, []);

  // ── Firebase auth ──
  useEffect(() => {
    if (!code || loggedIn) return;
    signInWithEmailAndPassword(getAuth(app), `${code}@gmail.com`, code)
      .then(() => setLoggedIn(true))
      .catch(console.error);
  }, [code, loggedIn]);

  // ── Firebase: printer details ──
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

  // ── Firebase: theme_type ──
  // Listens in real-time so changes in the dashboard are reflected instantly.
  useEffect(() => {
    if (!code) return;
    return onValue(ref(db, `Printers/${code}/details/theme_type`), (snap) => {
      if (snap.exists()) {
        const val = Number(snap.val());
        setThemeType(val);
        ls.set("atomte_theme_type", String(val));   // persist for fast rehydration
        setIsDark(computeIsDark(val));
      }
    });
  }, [code]);

  // ── Auto-update isDark for time-based mode (type 2) every 60 s ──
  useEffect(() => {
    if (themeType !== 2) return;
    const id = setInterval(() => setIsDark(computeIsDark(2)), 60_000);
    return () => clearInterval(id);
  }, [themeType]);

  // ── Firebase: print queue ──
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

  // ── Firebase: printer error ──
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

  // ── derived values ──
  const isActive = printer?.status?.toLowerCase() === "active";
  const printing = !!fileData;

  // ── inner render helpers (closures over tk) ──

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
      <p className={`text-sm uppercase tracking-[0.15em] font-semibold ${tk.textMed}`}>Scan to Print</p>
    </div>
  );

  const PrinterCard = () => (
    <div className="space-y-2">
      <div>
        <p className={`text-sm uppercase tracking-[0.15em] mb-1 ${tk.textMed}`}>Printer</p>
        <p className={`text-xl font-bold leading-tight ${tk.textBright}`}>
          {printer?.name ?? code ?? "—"}
        </p>
        {code && (
          <p className={`text-sm font-mono mt-0.5 ${tk.textSoft}`}>#{code}</p>
        )}
        {printer?.description && (
          <p className={`text-sm mt-1 leading-relaxed ${tk.textMed}`}>{printer.description}</p>
        )}
      </div>
      <Pill active={isActive} label={printer?.status ?? "Loading…"} tk={tk} />
    </div>
  );

  const MobileBlock = ({ big = false }) => (
    <div className={big ? "text-right" : ""}>
      <p className={`text-sm uppercase tracking-[0.15em] mb-1 font-semibold ${tk.textMed}`}>
        Assistance 24 / 7
      </p>
      <p className={`font-bold tracking-wider leading-none ${big ? "text-6xl" : "text-5xl"} ${tk.tealBright}`}>
        {mobile || "—"}
      </p>
    </div>
  );

  // ═══ PORTRAIT ═══
  if (portrait) {
    return (
      <div
        className={`h-screen w-screen ${tk.pageBg} ${tk.pageText} overflow-hidden flex flex-col`}
        style={{ fontFamily: "'Sora', sans-serif" }}
      >
        <div className={`flex items-start justify-between px-8 py-7 border-b ${tk.borderXFaint}`}>
          <div>
            <h1 className="text-5xl font-bold tracking-tight">ATOMTE</h1>
            <p className={`text-sm tracking-[0.2em] uppercase mt-1 ${tk.textMed}`}>Automated Print Service</p>
          </div>
          <MobileBlock big={false} />
        </div>

        <div className={`flex gap-7 px-8 py-6 border-b ${tk.borderXFaint} items-stretch`}>
          <div className="flex flex-col justify-center gap-4">
            <QRBlock size={160} />
            <div className={`h-px w-full ${tk.divXFaint}`} />
            <PrinterCard />
          </div>
          <div className={`w-px ${tk.divXFaint} self-stretch`} />
          <div className="flex-1 overflow-y-auto max-h-[420px]">
            <p className={`text-sm uppercase tracking-[0.15em] mb-3 font-semibold ${tk.textMed}`}>Print Status</p>
            {printing ? (
              <PrintFlow
                queueCount={queueCount}
                userData={userData}
                fileData={fileData}
                fileData1={fileData1}
                prtFileIdx={prtFileIdx}
                tk={tk}
              />
            ) : (
              <IdleView offline={offline} tk={tk} />
            )}
          </div>
        </div>

        <div className={`h-1/2 border-t ${tk.borderXFaint} flex-shrink-0 flex flex-col`}>
          <div className={`flex-1 border-b ${tk.borderXFaint} overflow-hidden`}>
            <Ad src="http://localhost:7000/videos/ad1.mp4" />
          </div>
          <div className="flex-1 flex">
            <div className="flex-1 overflow-hidden">
              <Ad src="http://localhost:7000/videos/ad2.mp4" />
            </div>
            <div className={`w-px ${tk.divXFaint} flex-shrink-0`} />
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
      className={`h-screen w-screen ${tk.pageBg} ${tk.pageText} overflow-hidden flex flex-col`}
      style={{ fontFamily: "'Sora', sans-serif" }}
    >
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left sidebar ── */}
        <div className={`w-[260px] flex-shrink-0 border-r ${tk.borderXFaint} flex flex-col`}>
          <div className={`px-6 pt-4 pb-5 border-b ${tk.borderXFaint}`}>
            <h1 className="text-3xl font-bold tracking-tight">ATOMTE</h1>
            <p className={`text-sm tracking-[0.2em] uppercase mt-1 ${tk.textMed}`}>Print Service</p>
          </div>
          <div className={`px-6 py-6 border-b ${tk.borderXFaint}`}>
            <QRBlock size={200} />
          </div>
          <div className="px-6 py-5 flex-1">
            <PrinterCard />
          </div>
        </div>

        {/* ── Main content ── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className={`px-10 py-5 border-b ${tk.borderXFaint} flex items-center justify-between flex-shrink-0`}>
            <div>
              {printing && queueCount > 0 && (
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-teal-400 animate-pulse" />
                  <span className={`text-xl font-semibold ${tk.tealMed}`}>
                    {queueCount} {queueCount === 1 ? "job" : "jobs"} in queue
                  </span>
                </div>
              )}
              {printing && (
                <p className={`text-base uppercase tracking-[0.15em] mt-1.5 font-medium ${tk.textMed}`}>Print Status</p>
              )}
            </div>
            <div className="text-right">
              <p className={`text-sm uppercase tracking-[0.15em] mb-2 font-semibold ${tk.textMed}`}>Assistance 24 / 7</p>
              <p className={`font-bold tracking-wider leading-none text-3xl ${tk.tealBright}`}>
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
                tk={tk}
              />
            ) : (
              <IdleView offline={offline} tk={tk} />
            )}
          </div>
        </div>
      </div>

      {/* ── Ad strip ── */}
      <div className={`h-44 flex-shrink-0 border-t ${tk.borderXFaint} flex`}>
        <div className="flex-1 overflow-hidden">
          <Ad src="http://localhost:7000/videos/ad2.mp4" />
        </div>
        <div className={`w-px ${tk.divXFaint} flex-shrink-0`} />
        <div className="flex-1 overflow-hidden">
          <Ad src="http://localhost:7000/videos/ad3.mp4" />
        </div>
      </div>

      <ErrorOverlay error={printerError} mobile={mobile} videoSrc={errVideo} />
    </div>
  );
}