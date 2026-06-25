const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

pres.layout = "LAYOUT_16x9";
pres.author = "Maritime Fuel Optimization Team";
pres.title = "Fuel Consumption Optimization Using AI-Based Tools";

// ── Color palette ──────────────────────────────────────────────────────────
const NAVY     = "0A1628";
const NAVY_MID = "162544";
const BLUE     = "1B65A6";
const ORANGE   = "E8772E";
const WHITE    = "FFFFFF";
const LIGHT_BG = "F4F6FA";
const GRAY     = "6B7280";
const DARK     = "1E293B";
const LIGHT_GRAY = "E2E8F0";

// Helper: fresh shadow factory
const cardShadow = () => ({ type: "outer", color: "000000", blur: 4, offset: 2, angle: 135, opacity: 0.10 });

// Helper: slide number on every content slide
function addSlideNum(slide, num) {
  slide.addText(String(num), {
    x: 9.3, y: 5.2, w: 0.5, h: 0.3, fontSize: 9,
    color: GRAY, align: "right", fontFace: "Calibri"
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 1: Title
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  // Accent bar at top
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: ORANGE } });
  s.addText("Fuel Consumption Optimization\nUsing AI-Based Tools", {
    x: 0.8, y: 1.0, w: 8.4, h: 2.2, fontSize: 36, fontFace: "Calibri",
    color: WHITE, bold: true, lineSpacingMultiple: 1.2
  });
  s.addText("Indian Coast Guard — Problem Statement 77", {
    x: 0.8, y: 3.2, w: 8.4, h: 0.5, fontSize: 18, fontFace: "Calibri",
    color: ORANGE, bold: false
  });
  s.addText("Quantum-Inspired Optimization for Maritime Fuel Efficiency", {
    x: 0.8, y: 3.8, w: 8.4, h: 0.5, fontSize: 14, fontFace: "Calibri",
    color: "94A3B8", italic: true
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 4.5, w: 2.0, h: 0.03, fill: { color: ORANGE } });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 2: Problem Statement
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 2);
  s.addText("The Problem", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Three cards
  const cards = [
    { title: "Cubic Speed-Power Law", body: "A ship's fuel burn rate grows with the cube of speed. Doubling speed increases fuel rate ~8×. Even small speed reductions yield large savings." },
    { title: "Operational Constraint", body: "Ships must arrive by a deadline (mission schedule). The captain cannot just go as slow as possible — there is a minimum feasible speed." },
    { title: "Environmental Impact", body: "Waves, wind, and currents change fuel burn significantly. A storm can increase fuel consumption by 30-50%. Route matters, not just speed." }
  ];
  cards.forEach((c, i) => {
    const cx = 0.7 + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 1.4, w: 2.8, h: 3.2, fill: { color: LIGHT_BG },
      shadow: cardShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.4, w: 2.8, h: 0.06, fill: { color: ORANGE } });
    s.addText(c.title, {
      x: cx + 0.2, y: 1.6, w: 2.4, h: 0.6, fontSize: 14, fontFace: "Calibri",
      color: NAVY, bold: true, valign: "top"
    });
    s.addText(c.body, {
      x: cx + 0.2, y: 2.3, w: 2.4, h: 2.0, fontSize: 11, fontFace: "Calibri",
      color: DARK, valign: "top", lineSpacingMultiple: 1.3
    });
  });
  s.addText("fuel_rate  ∝  displacement²ᐟ³  ×  speed³", {
    x: 0.7, y: 4.8, w: 8.6, h: 0.4, fontSize: 13, fontFace: "Consolas",
    color: BLUE, align: "center", bold: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 3: Objectives
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 3);
  s.addText("Objectives", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  const objs = [
    { num: "01", title: "Predict Fuel Burn", desc: "Build an ML model that learns the cubic speed-power law from ship voyage data and predicts fuel rate (tonnes/day) for any condition." },
    { num: "02", title: "Optimize Speed", desc: "Find the fuel-minimizing speed that still meets the arrival deadline — data-driven slow steaming with CO₂ reporting." },
    { num: "03", title: "Optimize Route", desc: "Find the minimum-fuel path through a weather field, detouring around storms when the fuel savings outweigh the extra distance." },
    { num: "04", title: "Quantum-Inspired QUBO", desc: "Formulate both problems as QUBOs — the binary optimization form quantum annealers solve natively — portable to D-Wave hardware." }
  ];
  objs.forEach((o, i) => {
    const cy = 1.3 + i * 1.0;
    s.addText(o.num, {
      x: 0.7, y: cy, w: 0.6, h: 0.7, fontSize: 22, fontFace: "Calibri",
      color: ORANGE, bold: true, valign: "middle"
    });
    s.addText(o.title, {
      x: 1.4, y: cy, w: 2.2, h: 0.7, fontSize: 14, fontFace: "Calibri",
      color: NAVY, bold: true, valign: "middle"
    });
    s.addText(o.desc, {
      x: 3.7, y: cy, w: 5.8, h: 0.7, fontSize: 11, fontFace: "Calibri",
      color: DARK, valign: "middle", lineSpacingMultiple: 1.2
    });
    if (i < 3) {
      s.addShape(pres.shapes.LINE, { x: 0.7, y: cy + 0.85, w: 8.6, h: 0, line: { color: LIGHT_GRAY, width: 0.5 } });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 4: Approach Overview
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 4);
  s.addText("Approach — Phased Development", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  const phases = [
    { label: "Phase 1", title: "Data + ML + Classical Optimization", items: "Synthetic data from physics\nTrain ML fuel-rate model (R² ≈ 0.99)\nSimulated annealing speed optimizer\nGrid search validation + CO₂ reporting", color: BLUE },
    { label: "Phase 2", title: "Quantum-Inspired QUBO", items: "Speed optimization as QUBO (proof)\nWeather routing as QUBO (headline)\nSolve with neal (D-Wave sampler)\nValidate against exact DP solver", color: ORANGE },
    { label: "Phase 3", title: "Dashboard (Planned)", items: "Streamlit interactive UI\nPick ship + conditions + voyage\nVisualize optimal speed & route\nReal-time fuel & CO₂ savings", color: "6B7280" }
  ];
  phases.forEach((p, i) => {
    const cx = 0.5 + i * 3.15;
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 1.4, w: 2.95, h: 3.6, fill: { color: LIGHT_BG },
      shadow: cardShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.4, w: 2.95, h: 0.5, fill: { color: p.color } });
    s.addText(p.label, {
      x: cx, y: 1.4, w: 2.95, h: 0.5, fontSize: 14, fontFace: "Calibri",
      color: WHITE, bold: true, align: "center", valign: "middle"
    });
    s.addText(p.title, {
      x: cx + 0.2, y: 2.05, w: 2.55, h: 0.55, fontSize: 13, fontFace: "Calibri",
      color: NAVY, bold: true, valign: "top"
    });
    s.addText(p.items.split("\n").map((t, j, arr) => ({
      text: t,
      options: { bullet: true, fontSize: 10.5, color: DARK, breakLine: j < arr.length - 1 }
    })), {
      x: cx + 0.2, y: 2.65, w: 2.55, h: 2.2, fontFace: "Calibri",
      valign: "top", paraSpaceAfter: 4
    });
    // Arrow between phases
    if (i < 2) {
      s.addText("→", {
        x: cx + 2.95, y: 2.8, w: 0.2, h: 0.5, fontSize: 22,
        color: GRAY, align: "center", valign: "middle", fontFace: "Calibri"
      });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 5: Ship Classes
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 5);
  s.addText("Ship Classes Modeled", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });
  s.addText("Three Indian Coast Guard ship classes spanning small interceptors to large patrol vessels", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.4, fontSize: 12, color: GRAY, fontFace: "Calibri"
  });

  const hdrOpts = { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle" };
  const cellOpts = { fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle", color: DARK };
  const altFill = { fill: { color: LIGHT_BG } };

  const rows = [
    [
      { text: "Parameter", options: hdrOpts },
      { text: "Interceptor", options: hdrOpts },
      { text: "Fast Patrol", options: hdrOpts },
      { text: "Offshore Patrol", options: hdrOpts }
    ],
    [
      { text: "Displacement", options: { ...cellOpts, bold: true, align: "left" } },
      { text: "~60 t", options: cellOpts },
      { text: "~550 t", options: cellOpts },
      { text: "~2000 t", options: cellOpts }
    ],
    [
      { text: "Engine Power", options: { ...cellOpts, bold: true, align: "left", ...altFill } },
      { text: "4,000 kW", options: { ...cellOpts, ...altFill } },
      { text: "8,000 kW", options: { ...cellOpts, ...altFill } },
      { text: "12,000 kW", options: { ...cellOpts, ...altFill } }
    ],
    [
      { text: "Hull Coefficient", options: { ...cellOpts, bold: true, align: "left" } },
      { text: "0.42", options: cellOpts },
      { text: "0.50", options: cellOpts },
      { text: "0.55", options: cellOpts }
    ],
    [
      { text: "Max Speed", options: { ...cellOpts, bold: true, align: "left", ...altFill } },
      { text: "35 kn", options: { ...cellOpts, ...altFill } },
      { text: "28 kn", options: { ...cellOpts, ...altFill } },
      { text: "25 kn", options: { ...cellOpts, ...altFill } }
    ],
    [
      { text: "Service Speed", options: { ...cellOpts, bold: true, align: "left" } },
      { text: "28 kn", options: cellOpts },
      { text: "22 kn", options: cellOpts },
      { text: "18 kn", options: cellOpts }
    ],
    [
      { text: "Fuel Types", options: { ...cellOpts, bold: true, align: "left", ...altFill } },
      { text: "MGO", options: { ...cellOpts, ...altFill } },
      { text: "MGO / VLSFO", options: { ...cellOpts, ...altFill } },
      { text: "VLSFO / HFO", options: { ...cellOpts, ...altFill } }
    ]
  ];
  s.addTable(rows, {
    x: 0.7, y: 1.6, w: 8.6,
    colW: [2.2, 2.13, 2.13, 2.14],
    border: { pt: 0.5, color: LIGHT_GRAY },
    rowH: [0.45, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4]
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 6: Data Generation — Physics Model
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 6);
  s.addText("Data Generation — Physics Model", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Left column: formulas
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.3, w: 5.2, h: 3.8, fill: { color: NAVY_MID },
    shadow: cardShadow()
  });
  s.addText("Core Physics (Admiralty Law)", {
    x: 0.7, y: 1.4, w: 4.8, h: 0.45, fontSize: 14, fontFace: "Calibri",
    color: ORANGE, bold: true
  });
  const formulas = [
    "propulsion = 5×10⁻⁵ × disp²ᐟ³ × (speed − current)³",
    "             × hull_coeff × (1 + 0.06 × waves)",
    "             × (1 + 0.005 × wind) × laden_factor",
    "",
    "hotel_load = 0.02 × displacement²ᐟ³",
    "",
    "fuel_rate = (propulsion + hotel) / fuel_energy",
    "            × (1 + 6% noise)"
  ];
  s.addText(formulas.map((t, i) => ({
    text: t, options: { breakLine: i < formulas.length - 1, fontSize: 11, color: "CBD5E1" }
  })), {
    x: 0.8, y: 1.9, w: 4.8, h: 2.8, fontFace: "Consolas", valign: "top",
    lineSpacingMultiple: 1.4
  });

  // Right column: details
  s.addText("10,000 Synthetic Records", {
    x: 6.0, y: 1.3, w: 3.5, h: 0.5, fontSize: 16, fontFace: "Calibri",
    color: NAVY, bold: true
  });
  const details = [
    "Sample ship class + parameters from Gaussian distributions",
    "Wave height: Gamma(2,1) distribution",
    "Wind: correlated with waves (5 + 6×waves + noise)",
    "Current: Normal(0, 1.2 kn)",
    "Load: Laden (1.15×) or Ballast (0.85×)",
    "6% multiplicative noise simulates real-world measurement uncertainty"
  ];
  s.addText(details.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < details.length - 1, fontSize: 10.5, color: DARK }
  })), {
    x: 6.0, y: 1.9, w: 3.7, h: 3.0, fontFace: "Calibri", valign: "top", paraSpaceAfter: 6
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 7: Feature Engineering
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 7);
  s.addText("Feature Engineering", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Static features card
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.3, w: 4.3, h: 3.5, fill: { color: LIGHT_BG }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.3, w: 4.3, h: 0.5, fill: { color: BLUE } });
  s.addText("Static Features (ship design)", {
    x: 0.5, y: 1.3, w: 4.3, h: 0.5, fontSize: 13, fontFace: "Calibri",
    color: WHITE, bold: true, align: "center", valign: "middle"
  });
  const staticF = [
    "displacement_tonnes — ship's total mass",
    "engine_power_kw — installed engine power",
    "hull_coefficient — hull shape (drag factor)",
    "ship_type — Interceptor / Fast / Offshore",
    "fuel_type — MGO / VLSFO / HFO"
  ];
  s.addText(staticF.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < staticF.length - 1, fontSize: 11, color: DARK }
  })), {
    x: 0.8, y: 2.0, w: 3.8, h: 2.5, fontFace: "Calibri", valign: "top", paraSpaceAfter: 6
  });

  // Dynamic features card
  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.3, w: 4.3, h: 3.5, fill: { color: LIGHT_BG }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.3, w: 4.3, h: 0.5, fill: { color: ORANGE } });
  s.addText("Dynamic Features (voyage conditions)", {
    x: 5.2, y: 1.3, w: 4.3, h: 0.5, fontSize: 13, fontFace: "Calibri",
    color: WHITE, bold: true, align: "center", valign: "middle"
  });
  const dynF = [
    "speed_knots — the decision variable",
    "wave_height_m — sea state",
    "wind_speed_kn — wind conditions",
    "current_speed_kn — ocean current",
    "load_condition — Laden / Ballast"
  ];
  s.addText(dynF.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < dynF.length - 1, fontSize: 11, color: DARK }
  })), {
    x: 5.5, y: 2.0, w: 3.8, h: 2.5, fontFace: "Calibri", valign: "top", paraSpaceAfter: 6
  });

  s.addText("Target:  fuel_rate_tpd  (tonnes per day)", {
    x: 0.7, y: 5.0, w: 8.6, h: 0.35, fontSize: 13, fontFace: "Consolas",
    color: BLUE, align: "center", bold: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 8: ML Pipeline
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 8);
  s.addText("ML Pipeline", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Pipeline flow boxes
  const steps = [
    { label: "Raw Data\n10,000 rows", color: BLUE },
    { label: "Column\nTransformer", color: BLUE },
    { label: "Train/Test\n80/20 Split", color: BLUE },
    { label: "3 Models\nCompared", color: ORANGE },
    { label: "5-Fold\nCross-Val", color: ORANGE }
  ];
  steps.forEach((st, i) => {
    const cx = 0.5 + i * 1.9;
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 1.4, w: 1.65, h: 0.9, fill: { color: st.color },
      shadow: cardShadow()
    });
    s.addText(st.label, {
      x: cx, y: 1.4, w: 1.65, h: 0.9, fontSize: 11, fontFace: "Calibri",
      color: WHITE, bold: true, align: "center", valign: "middle"
    });
    if (i < steps.length - 1) {
      s.addText("→", {
        x: cx + 1.65, y: 1.4, w: 0.25, h: 0.9, fontSize: 18,
        color: GRAY, align: "center", valign: "middle"
      });
    }
  });

  // Details
  s.addText("ColumnTransformer", {
    x: 0.7, y: 2.7, w: 4.0, h: 0.4, fontSize: 14, fontFace: "Calibri",
    color: NAVY, bold: true
  });
  const ctDetails = [
    "Numeric features: pass through unchanged",
    "Categorical features: OneHotEncoder",
    "Pipeline bundles preprocessing + model",
    "Single call for prediction"
  ];
  s.addText(ctDetails.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < ctDetails.length - 1, fontSize: 11, color: DARK }
  })), {
    x: 0.7, y: 3.1, w: 4.2, h: 1.8, fontFace: "Calibri", valign: "top", paraSpaceAfter: 4
  });

  s.addText("Three Models Compared", {
    x: 5.2, y: 2.7, w: 4.3, h: 0.4, fontSize: 14, fontFace: "Calibri",
    color: NAVY, bold: true
  });
  const models = [
    "Linear Regression (baseline)",
    "Random Forest (200 trees)",
    "HistGradientBoosting (best)"
  ];
  s.addText(models.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < models.length - 1, fontSize: 11, color: DARK }
  })), {
    x: 5.2, y: 3.1, w: 4.3, h: 1.2, fontFace: "Calibri", valign: "top", paraSpaceAfter: 4
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 9: Model Comparison Results
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 9);
  s.addText("Model Comparison — Results", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  const hdr = { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle" };
  const cell = { fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle", color: DARK };
  const alt = { fill: { color: LIGHT_BG } };
  const best = { fill: { color: "E8F5E9" } };

  const tbl = [
    [
      { text: "Model", options: { ...hdr, align: "left" } },
      { text: "CV R²", options: hdr },
      { text: "Test R²", options: hdr },
      { text: "MAE", options: hdr },
      { text: "RMSE", options: hdr },
      { text: "MAPE", options: hdr }
    ],
    [
      { text: "Linear Regression", options: { ...cell, align: "left" } },
      { text: "0.641", options: cell },
      { text: "0.648", options: cell },
      { text: "9.10", options: cell },
      { text: "12.97", options: cell },
      { text: "354%", options: { ...cell, color: "DC2626", bold: true } }
    ],
    [
      { text: "Random Forest", options: { ...cell, align: "left", ...alt } },
      { text: "0.977", options: { ...cell, ...alt } },
      { text: "0.980", options: { ...cell, ...alt } },
      { text: "1.52", options: { ...cell, ...alt } },
      { text: "3.06", options: { ...cell, ...alt } },
      { text: "9.3%", options: { ...cell, ...alt } }
    ],
    [
      { text: "Gradient Boosting", options: { ...cell, align: "left", ...best, bold: true } },
      { text: "0.987", options: { ...cell, ...best, bold: true } },
      { text: "0.987", options: { ...cell, ...best, bold: true } },
      { text: "1.30", options: { ...cell, ...best, bold: true } },
      { text: "2.45", options: { ...cell, ...best, bold: true } },
      { text: "11.3%", options: { ...cell, ...best, bold: true } }
    ]
  ];
  s.addTable(tbl, {
    x: 0.7, y: 1.3, w: 8.6,
    colW: [2.4, 1.24, 1.24, 1.24, 1.24, 1.24],
    border: { pt: 0.5, color: LIGHT_GRAY },
    rowH: [0.45, 0.45, 0.45, 0.45]
  });

  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 3.4, w: 8.6, h: 1.4, fill: { color: "FFF7ED" },
    shadow: cardShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 3.4, w: 0.06, h: 1.4, fill: { color: ORANGE } });
  s.addText("Key Insight", {
    x: 1.0, y: 3.5, w: 8.0, h: 0.35, fontSize: 13, fontFace: "Calibri",
    color: ORANGE, bold: true
  });
  s.addText(
    "Linear regression fails badly (R² = 0.65, MAPE = 354%) because it cannot capture the cubic speed-power law " +
    "across ships spanning 5–90 t/day. This demonstrates WHY nonlinear ML models are essential for this problem. " +
    "Gradient Boosting achieves R² ≈ 0.99 — the model has effectively rediscovered the physics from noisy data.",
    {
      x: 1.0, y: 3.85, w: 8.0, h: 0.8, fontSize: 11, fontFace: "Calibri",
      color: DARK, lineSpacingMultiple: 1.3
    }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 10: Model Output Placeholder
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 10);
  s.addText("Model Performance — Visual Results", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.3, w: 8.6, h: 3.8, fill: { color: LIGHT_BG },
    line: { color: LIGHT_GRAY, width: 1.5, dashType: "dash" }
  });
  s.addText("[ Insert model comparison charts here ]", {
    x: 0.7, y: 2.5, w: 8.6, h: 1.0, fontSize: 18, fontFace: "Calibri",
    color: GRAY, align: "center", valign: "middle", italic: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 11: Speed Optimization — U-Shaped Curve
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 11);
  s.addText("Speed Optimization — The U-Shaped Curve", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 30, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  s.addText("total_fuel = rate(speed) × distance / (24 × speed)", {
    x: 0.7, y: 1.2, w: 8.6, h: 0.4, fontSize: 14, fontFace: "Consolas",
    color: BLUE, align: "center", bold: true
  });

  // Two competing effects
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.8, w: 4.3, h: 1.8, fill: { color: "FEF2F2" }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.8, w: 0.06, h: 1.8, fill: { color: "DC2626" } });
  s.addText("Going Faster", { x: 0.8, y: 1.9, w: 3.8, h: 0.35, fontSize: 13, color: "DC2626", bold: true, fontFace: "Calibri" });
  s.addText("Higher fuel rate (cubic law)\nRate grows as speed³\nMore fuel per hour at sea", {
    x: 0.8, y: 2.3, w: 3.8, h: 1.1, fontSize: 11, color: DARK, fontFace: "Calibri", lineSpacingMultiple: 1.4
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.8, w: 4.3, h: 1.8, fill: { color: "FFF7ED" }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.8, w: 0.06, h: 1.8, fill: { color: ORANGE } });
  s.addText("Going Slower", { x: 5.5, y: 1.9, w: 3.8, h: 0.35, fontSize: 13, color: ORANGE, bold: true, fontFace: "Calibri" });
  s.addText("Longer voyage time\nHotel load accumulates (generators,\nelectronics run regardless of speed)", {
    x: 5.5, y: 2.3, w: 3.8, h: 1.1, fontSize: 11, color: DARK, fontFace: "Calibri", lineSpacingMultiple: 1.4
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.9, w: 9.0, h: 1.3, fill: { color: "F0FDF4" }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.9, w: 0.06, h: 1.3, fill: { color: "16A34A" } });
  s.addText("The Result: A U-Shaped Curve", { x: 0.8, y: 4.0, w: 8.4, h: 0.35, fontSize: 13, color: "16A34A", bold: true, fontFace: "Calibri" });
  s.addText(
    "The bottom of the U is the \"economic speed.\" Under a tight deadline, the minimum feasible speed may be above it. " +
    "Under a relaxed deadline, the optimizer reaches the true economic speed — going even slower would waste fuel.",
    { x: 0.8, y: 4.35, w: 8.4, h: 0.7, fontSize: 11, color: DARK, fontFace: "Calibri", lineSpacingMultiple: 1.3 }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 12: Simulated Annealing
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 12);
  s.addText("Simulated Annealing (SA)", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Algorithm steps
  const saSteps = [
    "Start at a random solution with high temperature T",
    "Propose a small random change (adjust speed / flip a bit)",
    "If change improves objective → always accept",
    "If change worsens by ΔE → accept with probability exp(−ΔE / T)",
    "Reduce temperature: T → T × 0.995 (cooling schedule)",
    "Repeat for 2,000 iterations until T ≈ 0"
  ];
  s.addText(saSteps.map((t, i) => ({
    text: t, options: { bullet: { type: "number" }, breakLine: i < saSteps.length - 1, fontSize: 11, color: DARK }
  })), {
    x: 0.7, y: 1.2, w: 5.5, h: 2.5, fontFace: "Calibri", valign: "top", paraSpaceAfter: 4
  });

  // Metropolis rule box
  s.addShape(pres.shapes.RECTANGLE, { x: 6.5, y: 1.2, w: 3.0, h: 1.5, fill: { color: NAVY_MID }, shadow: cardShadow() });
  s.addText("Metropolis Rule", {
    x: 6.5, y: 1.3, w: 3.0, h: 0.35, fontSize: 12, fontFace: "Calibri",
    color: ORANGE, bold: true, align: "center"
  });
  s.addText("P(accept) = exp(−ΔE / T)", {
    x: 6.5, y: 1.7, w: 3.0, h: 0.35, fontSize: 13, fontFace: "Consolas",
    color: WHITE, align: "center"
  });
  s.addText("High T → explore freely\nLow T → only accept improvements", {
    x: 6.5, y: 2.1, w: 3.0, h: 0.5, fontSize: 10, fontFace: "Calibri",
    color: "94A3B8", align: "center", lineSpacingMultiple: 1.3
  });

  // vs Gradient Descent
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.9, w: 9.0, h: 1.3, fill: { color: LIGHT_BG }, shadow: cardShadow() });
  s.addText("Why not Gradient Descent?", { x: 0.8, y: 4.0, w: 8.4, h: 0.35, fontSize: 13, color: NAVY, bold: true, fontFace: "Calibri" });
  s.addText(
    "Gradient descent needs continuous, differentiable functions — it computes slopes and slides downhill. " +
    "Our QUBO variables are binary (0 or 1): there is no gradient. SA works by evaluating the function at " +
    "random neighbors (no derivatives needed) and can escape local minima via the Metropolis rule.",
    { x: 0.8, y: 4.35, w: 8.4, h: 0.7, fontSize: 11, color: DARK, fontFace: "Calibri", lineSpacingMultiple: 1.3 }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 13: Speed Optimization Results
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 13);
  s.addText("Speed Optimization — Results", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });
  s.addText("Offshore Patrol Vessel, 600 nm leg, baseline = 18 kn service speed", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.35, fontSize: 12, color: GRAY, fontFace: "Calibri"
  });

  const hdr = { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle" };
  const cell = { fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle", color: DARK };
  const alt = { fill: { color: LIGHT_BG } };

  const tbl = [
    [
      { text: "Scenario", options: { ...hdr, align: "left" } },
      { text: "Optimal Speed", options: hdr },
      { text: "Fuel (t)", options: hdr },
      { text: "vs Baseline", options: hdr },
      { text: "CO₂ Saved", options: hdr }
    ],
    [
      { text: "Tight schedule (40 h)", options: { ...cell, align: "left" } },
      { text: "15.0 kn", options: cell },
      { text: "39.9", options: cell },
      { text: "−29%", options: { ...cell, color: "16A34A", bold: true } },
      { text: "52.5 t", options: cell }
    ],
    [
      { text: "Relaxed schedule (90 h)", options: { ...cell, align: "left", ...alt } },
      { text: "8.4 kn", options: { ...cell, ...alt } },
      { text: "18.3", options: { ...cell, ...alt } },
      { text: "−68%", options: { ...cell, ...alt, color: "16A34A", bold: true } },
      { text: "121.8 t", options: { ...cell, ...alt } }
    ]
  ];
  s.addTable(tbl, {
    x: 0.7, y: 1.6, w: 8.6,
    colW: [2.6, 1.5, 1.5, 1.5, 1.5],
    border: { pt: 0.5, color: LIGHT_GRAY },
    rowH: [0.45, 0.45, 0.45]
  });

  // Big number callouts
  s.addShape(pres.shapes.RECTANGLE, { x: 1.0, y: 3.0, w: 3.5, h: 1.8, fill: { color: "F0FDF4" }, shadow: cardShadow() });
  s.addText("−29%", { x: 1.0, y: 3.1, w: 3.5, h: 1.0, fontSize: 44, color: "16A34A", bold: true, align: "center", fontFace: "Calibri" });
  s.addText("fuel saved (tight deadline)", { x: 1.0, y: 4.0, w: 3.5, h: 0.4, fontSize: 12, color: GRAY, align: "center", fontFace: "Calibri" });

  s.addShape(pres.shapes.RECTANGLE, { x: 5.5, y: 3.0, w: 3.5, h: 1.8, fill: { color: "F0FDF4" }, shadow: cardShadow() });
  s.addText("−68%", { x: 5.5, y: 3.1, w: 3.5, h: 1.0, fontSize: 44, color: "16A34A", bold: true, align: "center", fontFace: "Calibri" });
  s.addText("fuel saved (relaxed deadline)", { x: 5.5, y: 4.0, w: 3.5, h: 0.4, fontSize: 12, color: GRAY, align: "center", fontFace: "Calibri" });

  s.addText("SA matches brute-force grid optimum to within 0.01 kn — confirmed true optimum.", {
    x: 0.7, y: 5.0, w: 8.6, h: 0.35, fontSize: 11, color: BLUE, align: "center", fontFace: "Calibri", italic: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 14: Speed Plot Placeholder
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 14);
  s.addText("Speed Optimization — Plots", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.3, w: 8.6, h: 3.8, fill: { color: LIGHT_BG },
    line: { color: LIGHT_GRAY, width: 1.5, dashType: "dash" }
  });
  s.addText("[ Insert voyage_fuel_vs_speed.png and speed_qubo plots here ]", {
    x: 0.7, y: 2.5, w: 8.6, h: 1.0, fontSize: 18, fontFace: "Calibri",
    color: GRAY, align: "center", valign: "middle", italic: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 15: QUBO — Theory
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 15);
  s.addText("QUBO — Quadratic Unconstrained Binary Optimization", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 26, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Formula box
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 9.0, h: 0.7, fill: { color: NAVY_MID }, shadow: cardShadow() });
  s.addText("minimize   H  =  Σᵢ qᵢ·xᵢ   +   Σᵢⱼ qᵢⱼ·xᵢ·xⱼ       where  xᵢ ∈ {0, 1}", {
    x: 0.5, y: 1.2, w: 9.0, h: 0.7, fontSize: 15, fontFace: "Consolas",
    color: WHITE, align: "center", valign: "middle"
  });

  // Key points
  const points = [
    { title: "Ising Model Equivalence", desc: "QUBO (0/1 variables) is mathematically identical to the Ising model (±1 spins) from 1920s physics — the substitution sᵢ = 2xᵢ − 1 converts between them." },
    { title: "Constraints as Penalties", desc: "No \"subject to\" section. Constraints become penalty terms: e.g., pick exactly one option → P × (Σxᵢ − 1)². Violating adds huge energy." },
    { title: "Hardware Portable", desc: "D-Wave quantum annealers solve QUBO/Ising natively. The same QUBO dict we pass to neal (classical) can go to DWaveSampler() — one line change." }
  ];
  points.forEach((p, i) => {
    const cy = 2.15 + i * 1.05;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 9.0, h: 0.9, fill: { color: LIGHT_BG }, shadow: cardShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 0.06, h: 0.9, fill: { color: ORANGE } });
    s.addText(p.title, {
      x: 0.8, y: cy + 0.05, w: 8.4, h: 0.3, fontSize: 12, fontFace: "Calibri", color: NAVY, bold: true
    });
    s.addText(p.desc, {
      x: 0.8, y: cy + 0.35, w: 8.4, h: 0.5, fontSize: 10.5, fontFace: "Calibri", color: DARK, lineSpacingMultiple: 1.2
    });
  });

  s.addText("Reference: Lucas (2014), \"Ising formulations of many NP problems\"", {
    x: 0.7, y: 5.1, w: 8.6, h: 0.3, fontSize: 10, fontFace: "Calibri", color: GRAY, italic: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 16: QUBO Speed (Phase 2a)
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 16);
  s.addText("QUBO Speed Optimization (Phase 2a)", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 30, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Encoding
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 9.0, h: 1.5, fill: { color: NAVY_MID }, shadow: cardShadow() });
  s.addText("QUBO Encoding (One-Hot Discretization)", {
    x: 0.7, y: 1.3, w: 8.6, h: 0.35, fontSize: 13, fontFace: "Calibri", color: ORANGE, bold: true
  });
  const encLines = [
    "H  =  Σᵢ fuelᵢ · xᵢ                         (minimize fuel)",
    "   +  P × (Σᵢ xᵢ − 1)²                      (pick exactly one speed)",
    "   +  P × Σ (infeasible xᵢ)                  (meet the deadline)"
  ];
  s.addText(encLines.map((t, i) => ({
    text: t, options: { breakLine: i < encLines.length - 1, fontSize: 11, color: "CBD5E1" }
  })), {
    x: 0.8, y: 1.7, w: 8.4, h: 0.9, fontFace: "Consolas", valign: "top", lineSpacingMultiple: 1.4
  });

  // Results table
  s.addText("Results — 40 candidate speeds, 600 nm, 40 h deadline", {
    x: 0.7, y: 3.0, w: 8.6, h: 0.4, fontSize: 13, fontFace: "Calibri", color: NAVY, bold: true
  });
  const hdr = { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle" };
  const cell = { fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle", color: DARK };
  const tbl = [
    [{ text: "Method", options: { ...hdr, align: "left" } }, { text: "Speed (kn)", options: hdr }, { text: "Fuel (t)", options: hdr }],
    [{ text: "QUBO (neal)", options: { ...cell, align: "left", bold: true } }, { text: "15.31", options: { ...cell, bold: true } }, { text: "42.07", options: { ...cell, bold: true } }],
    [{ text: "Simulated Annealing", options: { ...cell, align: "left", fill: { color: LIGHT_BG } } }, { text: "15.03", options: { ...cell, fill: { color: LIGHT_BG } } }, { text: "39.90", options: { ...cell, fill: { color: LIGHT_BG } } }],
    [{ text: "Brute-force Grid", options: { ...cell, align: "left" } }, { text: "15.02", options: cell }, { text: "39.92", options: cell }]
  ];
  s.addTable(tbl, {
    x: 1.5, y: 3.4, w: 7.0,
    colW: [2.8, 2.1, 2.1],
    border: { pt: 0.5, color: LIGHT_GRAY },
    rowH: [0.4, 0.4, 0.4, 0.4]
  });

  s.addText("QUBO matches grid within the 0.54 kn discretization step — QUBO machinery is correct ✓", {
    x: 0.7, y: 5.1, w: 8.6, h: 0.3, fontSize: 11, fontFace: "Calibri", color: "16A34A", align: "center", bold: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 17: Weather Routing — The Problem
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 17);
  s.addText("Weather Routing — The Problem", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  const routePoints = [
    { title: "Grid Discretization", desc: "Ocean region becomes an n_rows × n_cols grid. Ship starts at the west port, must reach the east port, advancing one column per stage." },
    { title: "Movement Rules", desc: "At each stage, the ship can stay in the same row or move ±1 row (north/south). No teleporting across multiple rows." },
    { title: "ML-Driven Cell Costs", desc: "Each cell's fuel cost is computed by the Phase 1 Gradient Boosting model using that cell's wave height and corresponding wind." },
    { title: "Combinatorial Explosion", desc: "Total possible paths = rows^cols. For an 11×25 grid: 11²⁵ ≈ 10²⁶ paths. Brute force is impossible — we need QUBO." }
  ];
  routePoints.forEach((p, i) => {
    const cy = 1.25 + i * 1.0;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 9.0, h: 0.85, fill: { color: LIGHT_BG }, shadow: cardShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 0.06, h: 0.85, fill: { color: i < 3 ? BLUE : ORANGE } });
    s.addText(p.title, {
      x: 0.8, y: cy + 0.05, w: 2.5, h: 0.75, fontSize: 12, fontFace: "Calibri", color: NAVY, bold: true, valign: "middle"
    });
    s.addText(p.desc, {
      x: 3.3, y: cy + 0.05, w: 6.0, h: 0.75, fontSize: 11, fontFace: "Calibri", color: DARK, valign: "middle", lineSpacingMultiple: 1.2
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 18: Weather Routing QUBO Formulation
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 18);
  s.addText("Weather Routing — QUBO Formulation", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 30, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  s.addText("Binary variable   x[c, r]  =  1   ⟺   \"ship is in row r at column c\"", {
    x: 0.7, y: 1.15, w: 8.6, h: 0.4, fontSize: 13, fontFace: "Consolas", color: BLUE, align: "center"
  });

  // Energy terms
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.7, w: 9.0, h: 2.8, fill: { color: NAVY_MID }, shadow: cardShadow() });
  s.addText("Energy Hamiltonian", {
    x: 0.7, y: 1.8, w: 8.6, h: 0.35, fontSize: 13, fontFace: "Calibri", color: ORANGE, bold: true
  });
  const hTerms = [
    "H  =  Σ  cost[r,c] · x[c,r]                                    (fuel objective)",
    "   +  surcharge × cost[r',c+1] · x[c,r] · x[c+1,r']            (diagonal penalty)",
    "   +  P × Σc (Σr x[c,r] − 1)²                                  (one row per column)",
    "   +  P × (wrong rows at first / last col)                      (fixed endpoints)",
    "   +  P × Σ x[c,r] · x[c+1,r']   for |r−r'| ≥ 2               (no teleporting)"
  ];
  s.addText(hTerms.map((t, i) => ({
    text: t, options: { breakLine: i < hTerms.length - 1, fontSize: 10.5, color: "CBD5E1" }
  })), {
    x: 0.8, y: 2.2, w: 8.4, h: 2.1, fontFace: "Consolas", valign: "top", lineSpacingMultiple: 1.5
  });

  s.addText("Penalty  P  =  10 × max(cell_cost)     — large enough to prevent violations, small enough for fine optimization", {
    x: 0.7, y: 4.7, w: 8.6, h: 0.4, fontSize: 11, fontFace: "Calibri", color: DARK, align: "center"
  });
  s.addText("Solved with  neal.SimulatedAnnealingSampler()  — same API as  DWaveSampler()", {
    x: 0.7, y: 5.1, w: 8.6, h: 0.3, fontSize: 11, fontFace: "Calibri", color: BLUE, align: "center", italic: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 19: Dynamic Programming — Exact Validation
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 19);
  s.addText("Exact Validation — Dynamic Programming", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 30, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Formula
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.2, w: 9.0, h: 0.7, fill: { color: NAVY_MID }, shadow: cardShadow() });
  s.addText("dp[c][r]  =  min( dp[c-1][r-1],  dp[c-1][r],  dp[c-1][r+1] )  +  cost[r][c]", {
    x: 0.5, y: 1.2, w: 9.0, h: 0.7, fontSize: 13, fontFace: "Consolas", color: WHITE, align: "center", valign: "middle"
  });

  // How it works
  const dpPoints = [
    "Exploits optimal substructure: best path to (c, r) must arrive from best path to a neighbor at c−1",
    "Complexity: O(rows × cols) — runs instantly on any grid size (replaces exponential brute force)",
    "Traces back through pointers to recover the exact optimal path",
    "Used to validate QUBO: if QUBO fuel is within ~1% of DP, the QUBO formulation is working"
  ];
  s.addText(dpPoints.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i < dpPoints.length - 1, fontSize: 11.5, color: DARK }
  })), {
    x: 0.7, y: 2.2, w: 8.6, h: 2.0, fontFace: "Calibri", valign: "top", paraSpaceAfter: 8
  });

  // Why not just use DP?
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.2, w: 9.0, h: 1.0, fill: { color: "FFF7ED" }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.2, w: 0.06, h: 1.0, fill: { color: ORANGE } });
  s.addText("Why not just use DP instead of QUBO?", {
    x: 0.8, y: 4.25, w: 8.4, h: 0.3, fontSize: 12, fontFace: "Calibri", color: ORANGE, bold: true
  });
  s.addText(
    "DP works for this specific grid structure. But QUBO generalizes to problems where DP doesn't apply " +
    "(joint speed+route, multi-objective, non-monotone paths). And QUBO is portable to quantum hardware — DP is not.",
    { x: 0.8, y: 4.55, w: 8.4, h: 0.55, fontSize: 11, fontFace: "Calibri", color: DARK, lineSpacingMultiple: 1.3 }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 20: Weather Routing Results
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 20);
  s.addText("Weather Routing — Results", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  const hdr = { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 10.5, fontFace: "Calibri", align: "center", valign: "middle" };
  const cell = { fontSize: 10.5, fontFace: "Calibri", align: "center", valign: "middle", color: DARK };
  const alt = { fill: { color: LIGHT_BG } };

  const tbl = [
    [
      { text: "Grid", options: { ...hdr, align: "left" } },
      { text: "Storms", options: hdr },
      { text: "QUBO Vars", options: hdr },
      { text: "Naive (t)", options: hdr },
      { text: "QUBO (t)", options: hdr },
      { text: "Exact (t)", options: hdr },
      { text: "Gap", options: hdr },
      { text: "Fuel Saved", options: hdr }
    ],
    [
      { text: "5 × 7", options: { ...cell, align: "left" } },
      { text: "1 (centre)", options: cell },
      { text: "35", options: cell },
      { text: "58.3", options: cell },
      { text: "52.7", options: cell },
      { text: "52.7", options: cell },
      { text: "0.00%", options: { ...cell, color: "16A34A", bold: true } },
      { text: "9.6%", options: { ...cell, bold: true } }
    ],
    [
      { text: "7 × 15", options: { ...cell, align: "left", ...alt } },
      { text: "3", options: { ...cell, ...alt } },
      { text: "105", options: { ...cell, ...alt } },
      { text: "—", options: { ...cell, ...alt } },
      { text: "—", options: { ...cell, ...alt } },
      { text: "—", options: { ...cell, ...alt } },
      { text: "0.00%", options: { ...cell, ...alt, color: "16A34A", bold: true } },
      { text: "~8%", options: { ...cell, ...alt, bold: true } }
    ],
    [
      { text: "9 × 19", options: { ...cell, align: "left" } },
      { text: "4", options: cell },
      { text: "171", options: cell },
      { text: "—", options: cell },
      { text: "—", options: cell },
      { text: "—", options: cell },
      { text: "0.97%", options: { ...cell, color: BLUE, bold: true } },
      { text: "~7%", options: { ...cell, bold: true } }
    ],
    [
      { text: "11 × 25", options: { ...cell, align: "left", ...alt } },
      { text: "6", options: { ...cell, ...alt } },
      { text: "275", options: { ...cell, ...alt } },
      { text: "53.76", options: { ...cell, ...alt } },
      { text: "49.94", options: { ...cell, ...alt } },
      { text: "49.35", options: { ...cell, ...alt } },
      { text: "1.18%", options: { ...cell, ...alt, color: BLUE, bold: true } },
      { text: "7.1%", options: { ...cell, ...alt, bold: true } }
    ]
  ];
  s.addTable(tbl, {
    x: 0.3, y: 1.2, w: 9.4,
    colW: [0.9, 1.1, 1.1, 1.1, 1.1, 1.1, 0.9, 1.1],
    border: { pt: 0.5, color: LIGHT_GRAY },
    rowH: [0.42, 0.42, 0.42, 0.42, 0.42]
  });

  // Callouts
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.6, w: 4.3, h: 1.5, fill: { color: "F0FDF4" }, shadow: cardShadow() });
  s.addText("7–10%", { x: 0.5, y: 3.7, w: 4.3, h: 0.8, fontSize: 40, color: "16A34A", bold: true, align: "center", fontFace: "Calibri" });
  s.addText("fuel saved by routing around storms", { x: 0.5, y: 4.4, w: 4.3, h: 0.35, fontSize: 12, color: GRAY, align: "center", fontFace: "Calibri" });

  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 3.6, w: 4.3, h: 1.5, fill: { color: LIGHT_BG }, shadow: cardShadow() });
  s.addText("< 1.2%", { x: 5.2, y: 3.7, w: 4.3, h: 0.8, fontSize: 40, color: BLUE, bold: true, align: "center", fontFace: "Calibri" });
  s.addText("gap from exact optimum (QUBO is near-optimal)", { x: 5.2, y: 4.4, w: 4.3, h: 0.35, fontSize: 11, color: GRAY, align: "center", fontFace: "Calibri" });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 21: Route Plot Placeholder
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 21);
  s.addText("Weather Routing — Visual Results", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 1.3, w: 8.6, h: 3.8, fill: { color: LIGHT_BG },
    line: { color: LIGHT_GRAY, width: 1.5, dashType: "dash" }
  });
  s.addText("[ Insert route_qubo plots here — multiple weather conditions ]", {
    x: 0.7, y: 2.5, w: 8.6, h: 1.0, fontSize: 18, fontFace: "Calibri",
    color: GRAY, align: "center", valign: "middle", italic: true
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 22: IMO Compliance
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 22);
  s.addText("IMO Compliance — CO₂ Reporting", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Emission factors table
  const hdr = { fill: { color: NAVY }, color: WHITE, bold: true, fontSize: 12, fontFace: "Calibri", align: "center", valign: "middle" };
  const cell = { fontSize: 12, fontFace: "Calibri", align: "center", valign: "middle", color: DARK };
  const tbl = [
    [{ text: "Fuel Type", options: hdr }, { text: "CO₂ Factor (t CO₂ / t fuel)", options: hdr }],
    [{ text: "MGO (Marine Gas Oil)", options: { ...cell, align: "left" } }, { text: "3.206", options: { ...cell, bold: true } }],
    [{ text: "VLSFO (Very Low Sulphur)", options: { ...cell, align: "left", fill: { color: LIGHT_BG } } }, { text: "3.151", options: { ...cell, bold: true, fill: { color: LIGHT_BG } } }],
    [{ text: "HFO (Heavy Fuel Oil)", options: { ...cell, align: "left" } }, { text: "3.114", options: { ...cell, bold: true } }]
  ];
  s.addTable(tbl, {
    x: 0.7, y: 1.3, w: 5.0,
    colW: [3.0, 2.0],
    border: { pt: 0.5, color: LIGHT_GRAY },
    rowH: [0.42, 0.42, 0.42, 0.42]
  });
  s.addText("Official IMO values used in Carbon Intensity Indicator (CII) calculations", {
    x: 0.7, y: 3.1, w: 5.0, h: 0.3, fontSize: 10, fontFace: "Calibri", color: GRAY, italic: true
  });

  // Example savings
  s.addShape(pres.shapes.RECTANGLE, { x: 6.2, y: 1.3, w: 3.3, h: 2.0, fill: { color: "F0FDF4" }, shadow: cardShadow() });
  s.addText("Example", { x: 6.4, y: 1.4, w: 2.9, h: 0.3, fontSize: 12, fontFace: "Calibri", color: "16A34A", bold: true });
  s.addText(
    "29% fuel saving on tight schedule\n= 16.4 t fuel saved\n= 52.5 t CO₂ saved per leg\n\n" +
    "68% fuel saving on relaxed\n= 37.9 t fuel saved\n= 121.8 t CO₂ saved per leg",
    { x: 6.4, y: 1.7, w: 2.9, h: 1.5, fontSize: 10.5, fontFace: "Calibri", color: DARK, lineSpacingMultiple: 1.3 }
  );

  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.7, w: 9.0, h: 1.3, fill: { color: LIGHT_BG }, shadow: cardShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.7, w: 0.06, h: 1.3, fill: { color: BLUE } });
  s.addText("Why CO₂ Reporting Matters", {
    x: 0.8, y: 3.8, w: 8.4, h: 0.3, fontSize: 13, fontFace: "Calibri", color: NAVY, bold: true
  });
  s.addText(
    "The IMO requires ships to report Carbon Intensity Indicator (CII) ratings annually. Ships with poor CII ratings " +
    "face operational restrictions. Our system automatically converts fuel savings into CO₂ reductions using official " +
    "IMO emission factors, providing the data needed for compliance reporting.",
    { x: 0.8, y: 4.15, w: 8.4, h: 0.7, fontSize: 11, fontFace: "Calibri", color: DARK, lineSpacingMultiple: 1.3 }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 23: Key References
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 23);
  s.addText("Key References", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  const refs = [
    { author: "Lucas, A. (2014)", title: "\"Ising formulations of many NP problems\"", journal: "Frontiers in Physics", note: "The recipe book for encoding optimization problems as QUBOs" },
    { author: "Feld, S. et al. (2019)", title: "\"A Hybrid Solution Method for the Capacitated Vehicle Routing Problem Using a Quantum Annealer\"", journal: "Frontiers in ICT", note: "D-Wave applied to fleet routing — same problem structure as ours" },
    { author: "Stollenwerk, T. et al. (2020)", title: "\"Flight Gate Assignment with a Quantum Annealer\"", journal: "Quantum Science and Technology", note: "QUBO for transport/trajectory optimization" },
    { author: "Ajagekar, A. & You, F. (2019)", title: "\"Quantum computing for energy systems optimization\"", journal: "Energy", note: "QUBO formulations for energy-related scheduling" },
    { author: "D-Wave Systems", title: "Ocean SDK Documentation", journal: "docs.ocean.dwavesys.com", note: "PyQUBO + neal + DWaveSampler toolchain" }
  ];
  refs.forEach((r, i) => {
    const cy = 1.2 + i * 0.82;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: cy, w: 9.0, h: 0.72,
      fill: { color: i % 2 === 0 ? LIGHT_BG : WHITE }
    });
    s.addText([
      { text: r.author + "  ", options: { bold: true, fontSize: 11, color: NAVY } },
      { text: r.title, options: { italic: true, fontSize: 11, color: DARK } }
    ], { x: 0.7, y: cy + 0.02, w: 8.6, h: 0.35, fontFace: "Calibri" });
    s.addText(r.journal + "  —  " + r.note, {
      x: 0.7, y: cy + 0.35, w: 8.6, h: 0.3, fontSize: 10, fontFace: "Calibri", color: GRAY
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 24: Honest Caveats
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 24);
  s.addText("Honest Caveats", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });
  s.addText("Transparency strengthens the presentation — state limitations before the audience asks", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.35, fontSize: 12, color: GRAY, fontFace: "Calibri", italic: true
  });

  const caveats = [
    { title: "Synthetic Data", desc: "Physics coefficients are plausible but not calibrated to specific ICG vessels. The model proves the approach works — real ship data would improve accuracy." },
    { title: "Classical Solver", desc: "QUBO is solved with neal (classical simulated annealing), not real quantum hardware. But the formulation is hardware-portable — one line change to run on D-Wave." },
    { title: "Independent Optimization", desc: "Speed and route are optimized separately. In reality they are interdependent. A joint QUBO is planned as a Phase 2+ extension." },
    { title: "Grid Approximation", desc: "The ocean is continuous; our grid discretization is an approximation. Finer grids improve accuracy but increase QUBO size." }
  ];
  caveats.forEach((c, i) => {
    const cy = 1.6 + i * 0.95;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 9.0, h: 0.8, fill: { color: LIGHT_BG }, shadow: cardShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 0.06, h: 0.8, fill: { color: ORANGE } });
    s.addText(c.title, {
      x: 0.8, y: cy + 0.05, w: 2.2, h: 0.7, fontSize: 12, fontFace: "Calibri", color: NAVY, bold: true, valign: "middle"
    });
    s.addText(c.desc, {
      x: 3.0, y: cy + 0.05, w: 6.2, h: 0.7, fontSize: 11, fontFace: "Calibri", color: DARK, valign: "middle", lineSpacingMultiple: 1.2
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 25: Roadmap & Future Work
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  addSlideNum(s, 25);
  s.addText("Roadmap & Future Work", {
    x: 0.7, y: 0.3, w: 8.6, h: 0.7, fontSize: 32, fontFace: "Calibri",
    color: NAVY, bold: true, margin: 0
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.7, y: 0.95, w: 1.2, h: 0.04, fill: { color: ORANGE } });

  // Done phases
  const done = [
    { label: "Phase 1", status: "DONE", desc: "Synthetic data + ML model (R² ≈ 0.99) + SA speed optimizer + CO₂ reporting" },
    { label: "Phase 2", status: "DONE", desc: "QUBO speed optimization + QUBO weather routing, validated against exact DP solver" }
  ];
  done.forEach((d, i) => {
    const cy = 1.3 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: cy, w: 9.0, h: 0.55, fill: { color: "F0FDF4" } });
    s.addText("✓", { x: 0.6, y: cy, w: 0.4, h: 0.55, fontSize: 16, color: "16A34A", bold: true, valign: "middle", fontFace: "Calibri" });
    s.addText(d.label, { x: 1.0, y: cy, w: 1.2, h: 0.55, fontSize: 12, color: NAVY, bold: true, valign: "middle", fontFace: "Calibri" });
    s.addText(d.desc, { x: 2.2, y: cy, w: 7.0, h: 0.55, fontSize: 11, color: DARK, valign: "middle", fontFace: "Calibri" });
  });

  // Planned
  s.addText("Planned Extensions", {
    x: 0.7, y: 2.9, w: 8.6, h: 0.4, fontSize: 14, fontFace: "Calibri", color: NAVY, bold: true
  });
  const future = [
    { label: "Phase 3", desc: "Streamlit dashboard — pick ship + conditions, visualize optimal speed/route, real-time savings" },
    { label: "Joint QUBO", desc: "Optimize speed AND route simultaneously in one QUBO (larger variable count, needs more annealing)" },
    { label: "Multi-segment", desc: "Speed profile optimization — different speed per leg under a total time budget" },
    { label: "Real Data", desc: "Retrain on public datasets (e.g., FuelCast) to demonstrate transfer to real vessels" },
    { label: "GA Comparison", desc: "Genetic algorithm optimizer for a three-way comparison: SA vs GA vs QUBO" },
    { label: "Quantum HW", desc: "Submit the same QUBO to real D-Wave quantum hardware via Leap cloud access" }
  ];
  future.forEach((f, i) => {
    const cy = 3.3 + i * 0.37;
    s.addText("○", { x: 0.6, y: cy, w: 0.3, h: 0.35, fontSize: 11, color: ORANGE, valign: "middle", fontFace: "Calibri" });
    s.addText(f.label, { x: 0.9, y: cy, w: 1.5, h: 0.35, fontSize: 11, color: NAVY, bold: true, valign: "middle", fontFace: "Calibri" });
    s.addText(f.desc, { x: 2.4, y: cy, w: 7.0, h: 0.35, fontSize: 11, color: DARK, valign: "middle", fontFace: "Calibri" });
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 26: Thank You
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: ORANGE } });
  s.addText("Thank You", {
    x: 0.5, y: 1.5, w: 9.0, h: 1.2, fontSize: 48, fontFace: "Calibri",
    color: WHITE, bold: true, align: "center", valign: "middle"
  });
  s.addText("Questions & Discussion", {
    x: 0.5, y: 2.8, w: 9.0, h: 0.6, fontSize: 20, fontFace: "Calibri",
    color: ORANGE, align: "center", valign: "middle"
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 4.0, y: 3.6, w: 2.0, h: 0.03, fill: { color: "94A3B8" } });
  s.addText("Maritime Fuel Consumption Optimization\nIndian Coast Guard — Problem Statement 77", {
    x: 0.5, y: 3.9, w: 9.0, h: 0.8, fontSize: 13, fontFace: "Calibri",
    color: "94A3B8", align: "center", lineSpacingMultiple: 1.4
  });
}

// ── Write file ─────────────────────────────────────────────────────────────
const outPath = process.cwd() + "\\outputs\\presentation.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("Saved ->", outPath);
}).catch(err => {
  console.error("Error:", err);
});
