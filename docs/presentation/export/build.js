// Builds Group 6 deck as PPTX from docs/presentation/slides/*/slide.html
const fs = require("fs");
const path = require("path");
const cheerio = require("cheerio");
const pptxgen = require("pptxgenjs");

const PRES_DIR = process.argv[2];
const OUT = process.argv[3];
const deck = JSON.parse(fs.readFileSync(path.join(PRES_DIR, "deck.json"), "utf8"));

// map slide id -> folder
const folders = {};
for (const d of fs.readdirSync(path.join(PRES_DIR, "slides"))) {
  const f = path.join(PRES_DIR, "slides", d, "slide.html");
  if (!fs.existsSync(f)) continue;
  const m = fs.readFileSync(f, "utf8").match(/<section id="([^"]+)"/);
  if (m) folders[m[1]] = f;
}

const P = {
  night: "1C1C21", night2: "26262D", night3: "2E2E36", snow: "F5F5F7", white: "FCFCFD",
  ink: "17171C", greyD: "9A9AA6", greyL: "62626D", violet: "7C3AED", violetL: "A78BFA",
  violetD: "6D28D9", cyan: "22D3EE", teal: "2DD4BF", lightCard: "EFEFF3", lightLine: "E2E2E8",
};
const CHIP = { c1: "7C3AED", c2: "0E7490", c3: "0F766E", c4: "4338CA", ca: "B45309" };
const DOT = { d1: "A78BFA", d2: "22D3EE", d3: "2DD4BF", d4: "7C3AED", d5: "38BDF8" };
const STAGE = { "": "7C3AED", s2: "22D3EE", s3: "2DD4BF", s4: "A78BFA" };
const FONT = "Arial";

const W = 13.333, H = 7.5, MX = 0.75;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = deck.title;
pres.author = "Group 6";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const clean = (s) => s.replace(/\s+/g, " ").trim();

// Turn an element's inner HTML into pptx text runs (b and .hl spans)
function runs($, el, base, hlColor) {
  const out = [];
  const walk = (node, bold, color) => {
    node.contents().each((_, c) => {
      if (c.type === "text") {
        const t = c.data.replace(/\s+/g, " ");
        if (t) out.push({ text: t, options: { ...base, bold, color } });
      } else if (c.name === "br") {
        out.push({ text: "", options: { ...base, breakLine: true } });
      } else if (c.name === "b") {
        walk($(c), true, color);
      } else if (c.name === "span" && $(c).hasClass("hl")) {
        walk($(c), bold, hlColor);
      } else {
        walk($(c), bold, color);
      }
    });
  };
  walk($(el), !!base.bold, base.color);
  // breakLine belongs on the run before the break
  const res = [];
  for (const r of out) {
    if (r.options.breakLine && r.text === "") {
      if (res.length) res[res.length - 1].options = { ...res[res.length - 1].options, breakLine: true };
      continue;
    }
    res.push(r);
  }
  // trim edges
  if (res.length) {
    res[0].text = res[0].text.replace(/^\s+/, "");
    res[res.length - 1].text = res[res.length - 1].text.replace(/\s+$/, "");
  }
  res.forEach((r, i) => { if (r.options.breakLine && res[i + 1]) res[i + 1].text = res[i + 1].text.replace(/^\s+/, ""); });
  return res;
}

function build(id) {
  const html = fs.readFileSync(folders[id], "utf8");
  const $ = cheerio.load(html, null, false);
  const sec = $("section").first();
  const dark = sec.hasClass("dark");
  const T = dark
    ? { bg: P.night, fg: P.snow, mute: P.greyD, card: P.night2, card2: P.night3, hl: P.violetL, eyebrow: P.violetL, line: "3A3A44" }
    : { bg: P.white, fg: P.ink, mute: P.greyL, card: P.lightCard, card2: "E6E6EC", hl: P.violetD, eyebrow: P.violetD, line: P.lightLine };

  const s = pres.addSlide();
  s.background = { color: T.bg };

  // decorative arcs on cover
  if (false) {
    const arcs = [[3.2, P.violet, 0, 120], [2.6, "3F3F48", 280, 60], [2.6, P.cyan, 20, 50], [2.0, P.teal, 300, 80], [1.4, P.violetL, 340, 45]];
    const cx = W, cy = H / 2 + 0.3;
    arcs.forEach(([r, c, a1, len]) => {
      s.addShape(pres.shapes.BLOCK_ARC, {
        x: cx - r, y: cy - r, w: 2 * r, h: 2 * r,
        fill: { color: c }, line: { color: c, width: 0 },
        angleRange: [a1, a1 + len], arcThicknessRatio: 0.12, objectName: "arc",
      });
    });
  }

  // top bar
  const tb = sec.find(".topbar p");
  s.addText($(tb[0]).text(), { x: MX, y: 0.35, w: 4, h: 0.35, fontSize: 13, bold: true, color: T.fg, margin: 0, isTextBox: true, charSpacing: 1 });
  s.addText($(tb[1]).text(), { x: W - MX - 4, y: 0.35, w: 4, h: 0.35, fontSize: 13, color: T.mute, align: "right", margin: 0, isTextBox: true });

  // eyebrow + head
  const eb = sec.find(".eyebrow").first();
  let y = id === "cover" ? 1.4 : 0.95;
  if (eb.length) {
    s.addText(clean(eb.text()), { x: MX, y, w: W - 2 * MX, h: 0.35, fontSize: 15, bold: true, color: T.eyebrow, margin: 0, isTextBox: true });
    y += 0.45;
  }
  const head = sec.find(".head").first();
  const isCover = id === "cover";
  const headSize = isCover ? 36 : 32;
  const headRuns = runs($, head, { fontSize: headSize, color: T.fg, bold: false }, T.hl);
  const headH = isCover ? 1.35 : 1.25;
  s.addText(headRuns, { x: MX, y, w: W - 2 * MX, h: headH, valign: "top", margin: 0, isTextBox: true, lineSpacingMultiple: 1.0 });
  y += headH + 0.3;

  const note = sec.find("p.note").first();
  const bottom = note.length ? 6.55 : 6.95;

  // ---- content blocks ----
  const content = { x: MX, y, w: W - 2 * MX, h: bottom - y };

  if (sec.find(".people").length) people($, s, sec.find(".people").first(), content, T, id);
  else if (sec.find(".flow").length) flow($, s, sec, content, T);
  else if (sec.find(".duo").length) duo($, s, sec, content, T);
  else if (sec.find(".gloss").length) gloss($, s, sec, content, T);
  else if (sec.find(".split").length) split($, s, sec, content, T);
  else if (sec.find(".card").length) rowList($, s, sec.find(".card").first().find(".row"), content, T, 0.62);

  if (note.length) {
    s.addText(clean(note.text()), { x: MX, y: 6.75, w: W - 2 * MX, h: 0.4, fontSize: 12, color: T.mute, margin: 0, isTextBox: true, valign: "top" });
  }

  const aside = sec.find("aside").first();
  if (aside.length) s.addNotes(clean(aside.text()));
}

function people($, s, el, box, T, id) {
  const ps = el.find(".person").toArray();
  const three = el.hasClass("three");
  const cols = three ? 3 : ps.length;
  const gap = 0.3;
  const cw = (box.w - gap * (cols - 1)) / cols;
  const ch = id === "cover" ? 2.0 : 1.45;
  const startY = id === "cover" ? box.y + 0.3 : box.y;
  ps.forEach((p, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const x = box.x + c * (cw + gap), yy = startY + r * (ch + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: yy, w: cw, h: ch, rectRadius: 0.12, fill: { color: T.card }, line: { color: T.card, width: 0 } });
    const dotCls = ($(p).find(".dot").attr("class") || "").split(" ").find((k) => DOT[k]);
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: yy + 0.3, w: 0.32, h: 0.32, fill: { color: DOT[dotCls] || P.violet }, line: { color: DOT[dotCls] || P.violet, width: 0 } });
    const tx = x + 0.75, tw = cw - 0.95;
    const name = clean($(p).find(".name").text()), task = clean($(p).find(".task").text()), rev = clean($(p).find(".rev").text());
    s.addText([
      { text: name, options: { fontSize: 20, bold: true, color: T.fg, breakLine: true } },
      { text: task, options: { fontSize: 14, color: T.fg, breakLine: true } },
      { text: rev, options: { fontSize: 13, color: T.mute } },
    ], { x: tx, y: yy + 0.22, w: tw, h: ch - 0.4, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 4 });
  });
}

function flow($, s, sec, box, T) {
  const st = sec.find(".stage").toArray();
  const aw = 0.4, gap = 0.12;
  const sw = (box.w - (st.length - 1) * (aw + 2 * gap)) / st.length;
  const sh = 2.35;
  st.forEach((e, i) => {
    const x = box.x + i * (sw + aw + 2 * gap);
    const cls = ($(e).attr("class") || "").split(" ").find((k) => STAGE[k] !== undefined && k !== "stage") || "";
    const col = STAGE[cls] || STAGE[""];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: box.y, w: sw, h: sh, rectRadius: 0.12, fill: { color: T.card }, line: { color: T.card, width: 0 } });
    const h3 = clean($(e).find("h3").text());
    const [num, ...rest] = h3.split("·");
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: box.y + 0.25, w: 0.45, h: 0.45, fill: { color: col }, line: { color: col, width: 0 } });
    s.addText(num.trim(), { x: x + 0.25, y: box.y + 0.25, w: 0.45, h: 0.45, fontSize: 16, bold: true, color: P.ink, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(rest.join("·").trim(), { x: x + 0.8, y: box.y + 0.25, w: sw - 0.95, h: 0.45, fontSize: 17, bold: true, color: T.fg, valign: "middle", margin: 0, isTextBox: true });
    const ps = $(e).find("p").toArray().map((p) => clean($(p).text()));
    s.addText(ps.map((t, k) => ({ text: t, options: { breakLine: k < ps.length - 1 } })), {
      x: x + 0.25, y: box.y + 0.9, w: sw - 0.45, h: sh - 1.05, fontSize: 15, color: T.mute, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 6,
    });
    if (i < st.length - 1) {
      s.addShape(pres.shapes.RIGHT_ARROW, { x: x + sw + gap, y: box.y + sh / 2 - 0.18, w: aw, h: 0.36, fill: { color: P.violet }, line: { color: P.violet, width: 0 } });
    }
  });
  const lg = sec.find(".legend p").toArray();
  const ly = box.y + sh + 0.4;
  const lr = [];
  lg.forEach((p, k) => {
    const rr = runs($, p, { fontSize: 15, color: T.mute, bold: false }, T.hl).map((r) => ({ ...r, options: { ...r.options, color: r.options.bold ? T.fg : T.mute } }));
    if (k < lg.length - 1 && rr.length) rr[rr.length - 1].options.breakLine = true;
    lr.push(...rr);
  });
  s.addText(lr, { x: box.x, y: ly, w: box.w, h: 0.9, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 6 });
}

function quoteCard($, s, col, x, y, w, h, T) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: T.card }, line: { color: T.card, width: 0 } });
  const lbl = clean(col.find(".lbl").text());
  const quote = clean(col.find(".quote").text());
  const metas = col.find(".meta").toArray();
  const items = [{ text: lbl.toUpperCase(), options: { fontSize: 13, bold: true, color: T.eyebrow, charSpacing: 1, breakLine: true, paraSpaceAfter: 10 } },
    { text: quote, options: { fontSize: 19, italic: true, color: T.fg, breakLine: true, paraSpaceAfter: 14 } }];
  metas.forEach((m, k) => {
    const b = clean($(m).find("b").text());
    const rest = clean($(m).text()).slice(b.length).trim();
    items.push({ text: b + "  ", options: { fontSize: 14, bold: true, color: T.fg } });
    items.push({ text: rest, options: { fontSize: 14, color: T.mute, breakLine: k < metas.length - 1, paraSpaceAfter: 6 } });
  });
  s.addText(items, { x: x + 0.3, y: y + 0.28, w: w - 0.6, h: h - 0.5, valign: "top", margin: 0, isTextBox: true });
}

function rowList($, s, rows, box, T, rh) {
  const arr = rows.toArray();
  const gap = 0.1;
  rh = Math.min(rh, (box.h - gap * (arr.length - 1)) / arr.length);
  arr.forEach((r, i) => {
    const y = box.y + i * (rh + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: box.x, y, w: box.w, h: rh, rectRadius: 0.08, fill: { color: T.card }, line: { color: T.card, width: 0 } });
    const chip = $(r).find(".chip");
    const cls = (chip.attr("class") || "").split(" ").find((k) => CHIP[k]);
    const cs = Math.min(0.4, rh - 0.16);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: box.x + 0.15, y: y + (rh - cs) / 2, w: cs, h: cs, rectRadius: 0.06, fill: { color: CHIP[cls] || P.violet }, line: { color: CHIP[cls] || P.violet, width: 0 } });
    const label = chip.find("x-icon").length ? "!" : clean(chip.text());
    s.addText(label, { x: box.x + 0.15, y: y + (rh - cs) / 2, w: cs, h: cs, fontSize: 15, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true });
    const tag = clean($(r).find(".tag").text());
    const tagW = tag ? 1.25 : 0;
    s.addText(clean($(r).find(".t").text()), { x: box.x + 0.15 + cs + 0.2, y, w: box.w - cs - 0.55 - tagW - 0.1, h: rh, fontSize: 15, color: T.fg, valign: "middle", margin: 0, isTextBox: true });
    if (tag) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: box.x + box.w - tagW - 0.15, y: y + (rh - 0.32) / 2, w: tagW, h: 0.32, rectRadius: 0.16, fill: { color: T.card2 }, line: { color: T.line, width: 0.75 } });
      s.addText(tag, { x: box.x + box.w - tagW - 0.15, y: y + (rh - 0.32) / 2, w: tagW, h: 0.32, fontSize: 11, bold: true, color: T.mute, align: "center", valign: "middle", margin: 0, isTextBox: true });
    }
  });
}

function split($, s, sec, box, T) {
  const lw = 4.6, gap = 0.35;
  quoteCard($, s, sec.find(".done-col").first(), box.x, box.y, lw, box.h, T);
  const rx = box.x + lw + gap, rw = box.w - lw - gap;
  let ry = box.y;
  const pill = sec.find(".pill").first();
  if (pill.length) {
    s.addText([{ text: "Code  ", options: { bold: true, color: T.eyebrow } }, { text: clean(pill.text()), options: { color: T.fg, fontFace: "Courier New" } }],
      { x: rx, y: ry, w: rw, h: 0.4, fontSize: 14, margin: 0, isTextBox: true, valign: "middle" });
    ry += 0.55;
  }
  rowList($, s, sec.find(".row"), { x: rx, y: ry, w: rw, h: box.y + box.h - ry }, T, 0.72);
}

function duo($, s, sec, box, T) {
  const cols = sec.find(".done-col").toArray();
  const gap = 0.35, w = (box.w - gap) / 2;
  cols.forEach((c, i) => quoteCard($, s, $(c), box.x + i * (w + gap), box.y + 0.2, w, Math.min(box.h, 2.9), T));
}

function gloss($, s, sec, box, T) {
  const ts = sec.find(".term").toArray();
  const half = Math.ceil(ts.length / 2), gap = 0.4, w = (box.w - gap) / 2;
  [ts.slice(0, half), ts.slice(half)].forEach((col, ci) => {
    const items = [];
    col.forEach((t, k) => {
      const b = clean($(t).find("b").text());
      const rest = clean($(t).text()).slice(b.length).replace(/^\s*·\s*/, "");
      items.push({ text: b + "  ", options: { bold: true, color: T.hl } });
      items.push({ text: rest, options: { color: T.fg, breakLine: k < col.length - 1 } });
    });
    s.addText(items, { x: box.x + ci * (w + gap), y: box.y - 0.1, w, h: box.h + 0.3, fontSize: 15, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 7 });
  });
}

// sections as in deck.json
const startToSection = {};
let n = 0;
for (const k of Object.keys(deck.sections)) startToSection[deck.sections[k].start] = ++n === 1 ? "Pitch (10 minutes)" : "Backup slides";

for (const id of deck.order) {
  if (!folders[id]) throw new Error("missing slide " + id);
  build(id);
}

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote", OUT, deck.order.length, "slides"));
