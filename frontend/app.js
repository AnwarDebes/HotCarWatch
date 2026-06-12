// HotCarWatch frontend.  Mirrors the Python hotcarwatch library.

"use strict";

// ---------- vehicle archetypes ----------

const VEHICLES = {
  compact_sedan_light:   { label: "Compact sedan light",
    glass_area: 2.2, body_area: 8.5, thermal_mass: 70000,
    glass_t: 0.80, abs_ext: 0.35, U: 6.5 },
  compact_sedan_dark:    { label: "Compact sedan dark",
    glass_area: 2.2, body_area: 8.5, thermal_mass: 70000,
    glass_t: 0.80, abs_ext: 0.85, U: 6.5 },
  midsize_sedan_light:   { label: "Midsize sedan light",
    glass_area: 2.6, body_area: 9.5, thermal_mass: 85000,
    glass_t: 0.80, abs_ext: 0.35, U: 6.5 },
  midsize_sedan_dark:    { label: "Midsize sedan dark",
    glass_area: 2.6, body_area: 9.5, thermal_mass: 85000,
    glass_t: 0.80, abs_ext: 0.85, U: 6.5 },
  suv_dark_tinted:       { label: "Large SUV dark tinted",
    glass_area: 3.0, body_area: 12.0, thermal_mass: 120000,
    glass_t: 0.65, abs_ext: 0.85, U: 6.5 },
  minivan_light:         { label: "Minivan light",
    glass_area: 3.2, body_area: 12.5, thermal_mass: 110000,
    glass_t: 0.80, abs_ext: 0.35, U: 6.5 },
};

const OCCUPANTS = {
  infant_6mo:    { label: "Infant ~6 mo (7.5 kg)",   class:"human",
    mass: 7.5,  area: 0.36, met: 20,  sweat: 15,
    Tn: 37.0, Tth: 40.0, Tcr: 42.0 },
  toddler_2y:    { label: "Toddler ~2 y (12 kg)",    class:"human",
    mass: 12.0, area: 0.55, met: 30,  sweat: 22,
    Tn: 37.0, Tth: 40.0, Tcr: 42.0 },
  child_5y:      { label: "Child ~5 y (18 kg)",      class:"human",
    mass: 18.0, area: 0.74, met: 45,  sweat: 35,
    Tn: 37.0, Tth: 40.0, Tcr: 42.0 },
  adult:         { label: "Adult (75 kg)",           class:"human",
    mass: 75.0, area: 1.85, met: 90,  sweat: 120,
    Tn: 37.0, Tth: 40.0, Tcr: 42.0 },
  small_dog_10kg: { label: "Small dog 10 kg",        class:"dog",
    mass: 10,   area: 0.5,  met: 30,  sweat: 0,
    Tn: 38.5, Tth: 40.5, Tcr: 42.0 },
  medium_dog_25kg: { label: "Medium dog 25 kg",      class:"dog",
    mass: 25,   area: 0.95, met: 70,  sweat: 0,
    Tn: 38.5, Tth: 40.5, Tcr: 42.0 },
  brachycephalic_dog_15kg: { label: "Bulldog 15 kg", class:"dog",
    mass: 15,   area: 0.65, met: 45,  sweat: 0,
    Tn: 38.5, Tth: 39.5, Tcr: 41.5 },
  cat_5kg:       { label: "Cat 5 kg",                class:"cat",
    mass: 5.0,  area: 0.32, met: 18,  sweat: 0,
    Tn: 38.6, Tth: 40.0, Tcr: 41.5 },
};

// ---------- thermal physics ----------

const C_BODY = 3470;
const H_EFF  = 8.0;
const INT_ABS = 0.75;
const SKIN_FRAC = 0.18;

function solarGain(v, S, sunshade) {
  const glass_t_eff = sunshade ? v.glass_t * 0.5 : v.glass_t;
  const direct = INT_ABS * glass_t_eff * v.glass_area * S;
  const indirect = SKIN_FRAC * v.abs_ext * v.body_area * S * 0.10;
  return direct + indirect;
}

function ventW(window_open, body_area) {
  const f = Math.max(0, Math.min(1, window_open));
  return f * 50 * (body_area / 10);
}

function simulateCabin(v, T_amb, S, hours, dt_h, window_open, sunshade) {
  const n = Math.max(2, Math.round(hours / dt_h));
  const times = new Array(n), T_cabin = new Array(n);
  for (let i = 0; i < n; i++) times[i] = i * dt_h;
  const L = v.U * v.body_area + ventW(window_open, v.body_area);
  const tau = v.thermal_mass / L / 3600;   // hours
  T_cabin[0] = T_amb;
  for (let k = 0; k < n - 1; k++) {
    const dt = times[k+1] - times[k];
    const Q = solarGain(v, S, sunshade);
    const T_eq = T_amb + Q / L;
    T_cabin[k+1] = T_eq + (T_cabin[k] - T_eq) * Math.exp(-dt / tau);
  }
  let peakIdx = 0;
  for (let i = 1; i < n; i++) if (T_cabin[i] > T_cabin[peakIdx]) peakIdx = i;
  const T_eq = T_amb + solarGain(v, S, sunshade) / L;
  return { times, T_cabin, peakT: T_cabin[peakIdx],
           T_amb, T_eq, tau_h: tau };
}

function pantingCooling(occ, T_cab, T_core) {
  if (occ.class !== "dog") return 0;
  if (T_cab >= T_core - 0.5) return 0;
  return Math.max(0, 1.0 * occ.mass * (1 - Math.max(0, T_cab - 32) / 8));
}

function hyperthermiaTimeline(occ, sim) {
  const n = sim.times.length;
  const T_core = new Array(n);
  T_core[0] = occ.Tn;
  const m_c = occ.mass * C_BODY;
  let t_thresh = -1, t40 = -1, t_crit = -1;
  for (let k = 0; k < n - 1; k++) {
    const dt_s = (sim.times[k+1] - sim.times[k]) * 3600;
    const T_cab = sim.T_cabin[k];
    const T_k = T_core[k];
    const Q_conv = H_EFF * occ.area * (T_cab - T_k);
    const Q_met = occ.met;
    let Q_evap = 0;
    if (T_cab > 31) {
      const eff = occ.sweat * Math.max(0, 1 - Math.max(0, T_cab - 38) / 6);
      Q_evap += eff;
    }
    Q_evap += pantingCooling(occ, T_cab, T_k);
    const Q_net = Q_conv + Q_met - Q_evap;
    T_core[k+1] = T_k + Q_net * dt_s / m_c;
    if (T_core[k+1] >= occ.Tth && t_thresh < 0)  t_thresh = k+1;
    if (T_core[k+1] >= 40 && t40 < 0)            t40 = k+1;
    if (T_core[k+1] >= occ.Tcr && t_crit < 0)    t_crit = k+1;
  }
  return {
    T_core,
    t_thresh_h: t_thresh >= 0 ? sim.times[t_thresh] : Infinity,
    t40_h:      t40 >= 0      ? sim.times[t40]      : Infinity,
    t_crit_h:   t_crit >= 0   ? sim.times[t_crit]   : Infinity,
    peakCore: Math.max(...T_core),
  };
}

// ---------- DOM ----------

const els = {
  outdoorC: document.getElementById("outdoorC"),
  sun: document.getElementById("sun"),
  vehicle: document.getElementById("vehicle"),
  window: document.getElementById("window"),
  sunshade: document.getElementById("sunshade"),
  occupant: document.getElementById("occupant"),
  planMin: document.getElementById("planMin"),
  recompute: document.getElementById("recompute"),
  saveProfile: document.getElementById("saveProfile"),
  statusHint: document.getElementById("statusHint"),
  chart: document.getElementById("chart"),
  returnCabin: document.getElementById("returnCabin"),
  returnImpact: document.getElementById("returnImpact"),
  t_thresh: document.getElementById("t_thresh"),
  t_40: document.getElementById("t_40"),
  t_crit: document.getElementById("t_crit"),
  recs: document.getElementById("recs"),
  nowBox: document.getElementById("nowBox"),
};

const PRESET_BUTTONS = document.querySelectorAll(".preset-btn");

function fmtMinutes(h) {
  if (!isFinite(h)) return "not within 2 h";
  if (h < 1) return (h * 60).toFixed(0) + " min";
  return h.toFixed(2) + " h";
}

function pillCategory(cabinC, occT) {
  if (cabinC < 30 && occT < 38.5) return "safe";
  if (cabinC < 40 && occT < 39.5) return "warn";
  return "danger";
}

function drawChart(times, T_outArr, T_cabArr, T_coreArr, planFracOfMax) {
  const c = els.chart;
  if (!c || typeof c.getContext !== "function") return;
  const dpr = window.devicePixelRatio || 1;
  const cssW = c.clientWidth || 800, cssH = c.clientHeight || 320;
  c.width = cssW * dpr; c.height = cssH * dpr;
  const ctx = c.getContext("2d"); if (!ctx) return;
  ctx.scale(dpr, dpr); ctx.clearRect(0, 0, cssW, cssH);
  const padL = 50, padR = 16, padT = 14, padB = 32;
  const W = cssW - padL - padR, H = cssH - padT - padB;
  const tmax = times[times.length - 1];
  const yMax = Math.max(60, ...T_cabArr) + 5;
  const yMin = Math.min(15, ...T_outArr, ...T_coreArr) - 5;
  const xOf = (t) => padL + (t / tmax) * W;
  const yOf = (T) => padT + (yMax - T) / (yMax - yMin) * H;
  // axes
  ctx.strokeStyle = "#999"; ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + H);
  ctx.lineTo(padL + W, padT + H); ctx.stroke();
  ctx.fillStyle = "#5b6566"; ctx.font = "11px -apple-system, sans-serif";
  ctx.textAlign = "right";
  for (let i = 0; i <= 6; i++) {
    const v = yMin + (yMax - yMin) * i / 6;
    const y = yOf(v);
    ctx.fillText(v.toFixed(0), padL - 4, y + 3);
    ctx.strokeStyle = i === 0 ? "#999" : "#e2e2dd";
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + W, y); ctx.stroke();
  }
  ctx.textAlign = "center";
  const xTicks = Math.min(6, Math.floor(tmax));
  for (let i = 0; i <= xTicks; i++) {
    const t = (tmax * i) / xTicks;
    const x = xOf(t);
    ctx.fillText(`${(t * 60).toFixed(0)} min`, x, padT + H + 16);
  }
  // 40 C threshold line
  ctx.strokeStyle = "#cc2222"; ctx.setLineDash([4, 4]);
  const yT = yOf(40); ctx.beginPath();
  ctx.moveTo(padL, yT); ctx.lineTo(padL + W, yT); ctx.stroke();
  ctx.setLineDash([]);
  // Planned return vertical
  if (planFracOfMax > 0 && planFracOfMax <= 1) {
    ctx.strokeStyle = "#6d4ec5"; ctx.lineWidth = 1.5; ctx.beginPath();
    const xP = padL + planFracOfMax * W;
    ctx.moveTo(xP, padT); ctx.lineTo(xP, padT + H); ctx.stroke();
    ctx.fillStyle = "#6d4ec5"; ctx.font = "10px -apple-system, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("planned return", xP + 4, padT + 12);
  }
  // series
  function drawSeries(arr, color, lw) {
    ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.beginPath();
    for (let i = 0; i < arr.length; i++) {
      const x = xOf(times[i]); const y = yOf(arr[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  drawSeries(T_outArr, "#d9b300", 2);   // outdoor
  drawSeries(T_cabArr, "#d24a14", 2.6); // cabin
  drawSeries(T_coreArr, "#6d4ec5", 2.3); // core
}

function computeAndRender() {
  const v = VEHICLES[els.vehicle.value];
  const occ = OCCUPANTS[els.occupant.value];
  const T_amb = parseFloat(els.outdoorC.value);
  const S = parseFloat(els.sun.value);
  const window_open = parseFloat(els.window.value);
  const sunshade = els.sunshade.value === "true";
  const planMin = Math.max(1, parseFloat(els.planMin.value));
  const planH = planMin / 60;
  const hours = Math.max(2.0, planH + 1.0);
  const sim = simulateCabin(v, T_amb, S, hours, 0.025, window_open, sunshade);
  const hot = hyperthermiaTimeline(occ, sim);

  // outdoor series (constant for now)
  const T_out = sim.times.map(() => T_amb);
  drawChart(sim.times, T_out, sim.T_cabin, hot.T_core, planH / hours);

  // At planned return:
  const iReturn = Math.min(sim.times.length - 1, Math.round(planH / 0.025));
  const cabAtReturn = sim.T_cabin[iReturn];
  const coreAtReturn = hot.T_core[iReturn];
  els.returnCabin.textContent = cabAtReturn.toFixed(1);
  els.returnImpact.textContent = `occupant core ${coreAtReturn.toFixed(1)} °C` +
                                    (coreAtReturn >= occ.Tth ? " - HEAT STROKE" :
                                     (coreAtReturn >= 38.5 ? " - fever" : ""));
  els.nowBox.className = "now-pill " + pillCategory(cabAtReturn, coreAtReturn);

  els.t_thresh.textContent = fmtMinutes(hot.t_thresh_h);
  els.t_40.textContent     = fmtMinutes(hot.t40_h);
  els.t_crit.textContent   = fmtMinutes(hot.t_crit_h);

  // Interventions
  const interventions = [
    { key: "do_not_leave", label: "DO NOT leave the occupant in the vehicle",
      desc: "The only intervention that prevents heat injury with certainty.",
      apply: () => null, guaranteed: true },
    { key: "park_in_shade", label: "Park in deep shade or covered garage",
      desc: "Reduces solar load to ~15% of full sun. Most effective non-trivial intervention.",
      apply: () => simulateCabin(v, T_amb, 150, hours, 0.025, window_open, sunshade) },
    { key: "sunshade", label: "Deploy reflective windshield sunshade",
      desc: "Blocks ~50% of windshield solar gain (Vanos 2018).",
      apply: () => simulateCabin(v, T_amb, S, hours, 0.025, window_open, true) },
    { key: "open_halfway", label: "Open windows halfway",
      desc: "Substantial ventilation, but still inadequate in direct sun.",
      apply: () => simulateCabin(v, T_amb, S, hours, 0.025, 0.45, sunshade) },
    { key: "crack", label: "Crack windows ~1.5 inches",
      desc: "Common myth. McLaren 2005 measured 0-3 °C reduction.",
      apply: () => simulateCabin(v, T_amb, S, hours, 0.025, 0.05, sunshade) },
  ];
  const baselinet40 = hot.t40_h;
  const recs = [];
  for (const intv of interventions) {
    if (intv.guaranteed) {
      recs.push({ ...intv, minutesBought: Infinity, peakC: null, guaranteed: true });
      continue;
    }
    const sim2 = intv.apply();
    const hot2 = hyperthermiaTimeline(occ, sim2);
    const mb = isFinite(hot2.t40_h) && isFinite(baselinet40)
       ? 60 * (hot2.t40_h - baselinet40)
       : (isFinite(baselinet40) ? Infinity : 0);
    recs.push({ ...intv, minutesBought: mb, peakC: sim2.peakT, guaranteed: false });
  }
  els.recs.innerHTML = "";
  const head = recs.filter(r => r.guaranteed);
  const tail = recs.filter(r => !r.guaranteed);
  tail.sort((a, b) => b.minutesBought - a.minutesBought);
  for (const r of head.concat(tail).slice(0, 5)) {
    const li = document.createElement("li");
    if (r.guaranteed) li.classList.add("guaranteed");
    const main = document.createElement("div");
    main.innerHTML = `<div class="rec-label">${r.label}</div>
                      <div class="rec-desc">${r.desc}</div>`;
    const nums = document.createElement("div"); nums.className = "rec-numbers";
    if (r.guaranteed) {
      nums.innerHTML = `<span class="reduction">SAFE</span><span>only safe option</span>`;
    } else {
      const mb = !isFinite(r.minutesBought) ? "all 2 h safe" :
                  (r.minutesBought > 0 ? `+${r.minutesBought.toFixed(0)} min` : "minimal");
      const pc = r.peakC === null ? "" : `peak cabin ${r.peakC.toFixed(0)} °C`;
      nums.innerHTML = `<span class="reduction">${mb}</span><span>${pc}</span>`;
    }
    li.appendChild(main); li.appendChild(nums);
    els.recs.appendChild(li);
  }
  els.statusHint.textContent = `Cabin peak ${sim.peakT.toFixed(1)} °C; ` +
                                  `core ${occ.label.split(",")[0]} reaches 40 °C at ${fmtMinutes(hot.t40_h)}.`;
}

const STORAGE_KEY = "hotcarwatch.profile.v1";
function saveProfile() {
  const p = { outdoorC: els.outdoorC.value, sun: els.sun.value,
              vehicle: els.vehicle.value, window: els.window.value,
              sunshade: els.sunshade.value, occupant: els.occupant.value,
              planMin: els.planMin.value };
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
        els.statusHint.textContent = "Saved."; }
  catch (_) { els.statusHint.textContent = "Could not save."; }
}
function loadProfile() {
  try { const p = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
        if (p) for (const id of Object.keys(p)) if (els[id] && p[id]) els[id].value = p[id]; }
  catch (_) {}
}

els.recompute.addEventListener("click", computeAndRender);
els.saveProfile.addEventListener("click", saveProfile);
for (const id of ["outdoorC","sun","vehicle","window","sunshade","occupant","planMin"]) {
  els[id].addEventListener("input", computeAndRender);
  els[id].addEventListener("change", computeAndRender);
}
PRESET_BUTTONS.forEach(b => b.addEventListener("click", () => {
  const v = JSON.parse(b.dataset.preset);
  els.outdoorC.value = v.T; els.sun.value = v.S; computeAndRender();
}));
window.addEventListener("resize", () => computeAndRender());

loadProfile();
computeAndRender();
