"use strict";
/* Akademik Çıktı Takibi — arayüz
   Sunucu: dönem, kapsam, arama, gizliler, ayı-bilinmeyenler filtrelerini uygular.
   İstemci: tür, öğretim üyesi, indeks ve "ayı eksik" filtrelerini uygular (sayılar anında güncellenir). */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const NOW_Y = new Date().getFullYear();
const KIND = {makale:"Makale", bildiri:"Bildiri", kitap:"Kitap", proje:"Proje", patent:"Patent"};
const KIND_PL = {"":"Tümü", makale:"Makaleler", bildiri:"Bildiriler", kitap:"Kitap ve bölümler", proje:"Projeler", patent:"Patentler"};
const AYK = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
const PRESET = {"5y":[NOW_Y-4,1,NOW_Y,12], buyil:[NOW_Y,1,NOW_Y,12], gecenyil:[NOW_Y-1,1,NOW_Y-1,12], hepsi:["",1,"",12]};

const S = {meta:null, hocalar:[], rows:[], kind:"", hoca:new Set(), eksik:false, sel:null, edit:null};

/* ---------------------------------------------------------------- yardımcılar */
async function api(url, opt = {}) {
  const o = {...opt};
  if (o.body && typeof o.body !== "string") { o.body = JSON.stringify(o.body); o.headers = {"Content-Type":"application/json"}; }
  const r = await fetch(url, o);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.hata || r.statusText);
  return d;
}
function toast(m) { const t = $("#toast"); t.textContent = m; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2200); }
const hocaAdi = id => { const h = S.hocalar.find(x => x.yok_id === id); return h ? `${h.ad} ${h.soyad}` : id; };
const typing = () => /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName) || $("dialog[open]");

/* ---------------------------------------------------------------- dönem */
function fillSelects() {
  $$("#basAy, #bitAy").forEach(s => s.innerHTML = S.meta.aylar.map((a, i) => `<option value="${i+1}">${a}</option>`).join(""));
  const yy = []; for (let y = NOW_Y + 1; y >= 1990; y--) yy.push(y);
  $$("#basYil, #bitYil").forEach(s => s.innerHTML = `<option value="">—</option>` + yy.map(y => `<option>${y}</option>`).join(""));
  $("#sMinYil").innerHTML = yy.map(y => `<option>${y}</option>`).join("");
}
const range = () => [$("#basYil").value, +$("#basAy").value, $("#bitYil").value, +$("#bitAy").value];
function setRange(by, ba, ey, ea) { $("#basYil").value = by; $("#basAy").value = ba; $("#bitYil").value = ey; $("#bitAy").value = ea; syncPreset(); }
function syncPreset() {
  const [by, ba, ey, ea] = range();
  const m = Object.entries(PRESET).find(([, v]) => String(v[0]) === by && v[1] === ba && String(v[2]) === ey && v[3] === ea);
  $("#preset").value = m ? m[0] : "ozel";
}
function rangeText() {
  const [by, ba, ey, ea] = range();
  if (!by && !ey) return "tüm yıllar";
  return `${by ? `${S.meta.aylar[ba-1]} ${by}` : "…"} – ${ey ? `${S.meta.aylar[ea-1]} ${ey}` : "…"}`;
}

/* ---------------------------------------------------------------- kalıcı filtre */
function save() {
  try { localStorage.setItem("aot", JSON.stringify({r: range(), k: S.kind, h: [...S.hoca], ka: $("#kapsam").value, a: $("#aysizlar").checked})); } catch {}
}
function restore() {
  setRange(...PRESET["5y"]);   // varsayılan: son 5 yıl, Ocak–Aralık
  try {
    const f = JSON.parse(localStorage.getItem("aot") || "null"); if (!f) return;
    setRange(...f.r); S.kind = f.k || ""; S.hoca = new Set(f.h || []); $("#kapsam").value = f.ka || ""; $("#aysizlar").checked = f.a !== false;
  } catch {}
}

/* ---------------------------------------------------------------- veri */
function serverParams(extra = {}) {
  const [by, ba, ey, ea] = range();
  const p = {bas_yil: by, bas_ay: ba, bit_yil: ey, bit_ay: ea, kapsam: $("#kapsam").value, ara: $("#ara").value.trim(),
             aysizlar: $("#aysizlar").checked ? 1 : 0, gizliler: $("#gizliler").checked ? 1 : 0, ...extra};
  return new URLSearchParams(Object.entries(p).filter(([, v]) => v !== "" && v != null)).toString();
}
let seq = 0;
async function load() {
  const my = ++seq;
  const t = setTimeout(() => { if (my === seq) $("#tbody").innerHTML = `<tr class="loading"><td colspan="4">Yükleniyor…</td></tr>`; }, 200);
  try { const rows = await api("/api/kayitlar?" + serverParams()); if (my === seq) { S.rows = rows; render(); } }
  finally { clearTimeout(t); }
}

/* ---------------------------------------------------------------- filtreleme (istemci) */
const altKey = r => r.kind === "bildiri" ? (r.kategori || "") : (r.tur || "");
function pass(r, skip = "") {
  if (skip !== "kind" && S.kind && r.kind !== S.kind) return false;
  if (skip !== "hoca" && S.hoca.size && !S.hoca.has(r.hoca_id)) return false;
  if (skip !== "alt" && $("#altTur").value && altKey(r) !== $("#altTur").value) return false;
  if (skip !== "eksik" && S.eksik && r.ay) return false;
  return true;
}
const visible = () => S.rows.filter(r => pass(r));

/* ---------------------------------------------------------------- çizim */
function render() {
  // türler
  const base = S.rows.filter(r => pass(r, "kind"));
  const of = k => base.filter(r => r.kind === k);
  const cnt = (arr, fn) => arr.filter(fn).length;
  const mk = of("makale"), bd = of("bildiri"), kt = of("kitap"), pj = of("proje"), pt = of("patent");
  const sub = {
    "": `${new Set(base.map(r => r.hoca_id)).size} öğretim üyesi`,
    makale: `${cnt(mk, r => /^(SCI|SCI-E|SSCI|AHCI)$/.test(r.tur))} SCI/SCI-E · ${cnt(mk, r => /^Q[12]$/.test(r.quartile))} Q1–Q2`,
    bildiri: `${cnt(bd, r => r.tur === "Uluslararası")} uluslararası · ${cnt(bd, r => /Tam/.test(r.kategori))} tam metin`,
    kitap: `${cnt(kt, r => r.tur === "Kitap Bölümü")} bölüm · ${cnt(kt, r => r.tur !== "Kitap Bölümü")} kitap`,
    proje: `${cnt(pj, r => /devam/i.test(r.durum))} devam ediyor · ${cnt(pj, r => /yürütücü/i.test(r.rol))} yürütücü`,
    patent: pt.length ? `${cnt(pt, r => /patent/i.test(r.tur))} patent · ${cnt(pt, r => !/patent/i.test(r.tur))} diğer` : "Bu dönemde kayıt yok",
  };
  const kc = {"": base.length, makale: mk.length, bildiri: bd.length, kitap: kt.length, proje: pj.length, patent: pt.length};
  $("#navKind").innerHTML = Object.keys(KIND_PL).map(k =>
    `<button data-k="${k}" class="kpi k-${k || "all"} ${S.kind === k ? "on" : ""} ${kc[k] ? "" : "zero"}" aria-pressed="${S.kind === k}">
      <span class="kpi-l">${KIND_PL[k]}</span><b>${kc[k]}</b></button>`).join("");

  $("#categorySummary").textContent = S.kind ? sub[S.kind] : "";

  // öğretim üyeleri
  const hc = {}; S.rows.filter(r => pass(r, "hoca")).forEach(r => hc[r.hoca_id] = (hc[r.hoca_id] || 0) + 1);
  const aktif = S.hocalar.filter(h => h.aktif);
  $("#navHoca").innerHTML = `<button data-h="" aria-pressed="${!S.hoca.size}" class="${S.hoca.size ? "" : "on"}"><span class="box" aria-hidden="true"></span><span class="nm">Tümü</span><span class="n">${S.rows.filter(r => pass(r, "hoca")).length}</span></button>` +
    aktif.map(h => `<button data-h="${h.yok_id}" aria-pressed="${S.hoca.has(h.yok_id)}" aria-label="${esc(h.ad)} ${esc(h.soyad)}" class="${S.hoca.has(h.yok_id) ? "on" : ""} ${hc[h.yok_id] ? "" : "zero"}">
      <span class="box" aria-hidden="true"></span><span class="nm" title="${esc(h.ad)} ${esc(h.soyad)}">${esc(h.ad)} ${esc(h.soyad)}</span><span class="n">${hc[h.yok_id] || 0}</span></button>`).join("");

  // indeks seçenekleri
  const sel = $("#altTur"), cur = sel.value;
  const vals = [...new Set(S.rows.filter(r => pass(r, "alt")).map(altKey).filter(Boolean))].sort((a, b) => a.localeCompare(b, "tr"));
  sel.innerHTML = `<option value="">Tüm indeksler</option>` + vals.map(v => `<option>${esc(v)}</option>`).join("");
  sel.value = vals.includes(cur) ? cur : "";

  // ayı eksik
  const eksik = S.rows.filter(r => pass(r, "eksik") && !r.ay).length;
  const be = $("#btnEksik");
  be.textContent = S.eksik ? `Ayı eksik olanlar (${eksik}) — tümünü göster` : `Ayı eksik ${eksik} kayıt`;
  be.setAttribute("aria-pressed", S.eksik);
  be.hidden = !eksik && !S.eksik;
  be.title = "Ay bilgisi girilmemiş kayıtları listeler. Ayı tarih sütunundan seçebilirsiniz.";

  // sıfırla
  const [by, ba, ey, ea] = range();
  const def = String(by) === String(NOW_Y - 4) && ba === 1 && String(ey) === String(NOW_Y) && ea === 12;
  $("#btnTemizle").hidden = def && !S.kind && !S.hoca.size && !$("#kapsam").value && !$("#altTur").value && !$("#ara").value && !$("#gizliler").checked && !S.eksik;

  // tablo
  const rows = visible();
  const who = S.hoca.size === 0 ? "" : S.hoca.size === 1 ? ` · ${hocaAdi([...S.hoca][0])}` : ` · ${S.hoca.size} öğretim üyesi`;
  $("#summary").innerHTML = `${rows.length} kayıt <em>· ${rangeText()}${esc(who)}</em>`;
  const empty = $("#empty");
  if (!rows.length) {
    $("#tbody").innerHTML = "";
    empty.hidden = false;
    empty.innerHTML = S.rows.length || $("#ara").value
      ? `<b>Bu seçimle eşleşen kayıt yok.</b>Dönemi genişletin ya da filtreleri sıfırlayın.`
      : `<b>Henüz kayıt yok.</b>Soldaki “YÖKSİS'ten güncelle” ile verileri çekin.`;
    return;
  }
  empty.hidden = true;
  let html = "", lastY;
  const yc = {}; rows.forEach(r => yc[r.yil ?? "—"] = (yc[r.yil ?? "—"] || 0) + 1);
  for (const r of rows) {
    const y = r.yil ?? "—";
    if (y !== lastY) { html += `<tr class="ygroup"><td colspan="4"><b>${esc(y)}</b><span>· ${yc[y]} kayıt</span></td></tr>`; lastY = y; }
    html += rowHtml(r);
  }
  $("#tbody").innerHTML = html;
}

function venue(r) {
  switch (r.kind) {
    case "makale": return [r.dergi, [r.cilt && `${r.cilt}`, r.sayi && `(${r.sayi})`].filter(Boolean).join(""), r.sayfa && `s. ${r.sayfa}`].filter(Boolean).join(", ");
    case "bildiri": return [r.etkinlik, [r.sehir, r.ulke].filter(Boolean).join(", ")].filter(Boolean).join(" — ");
    case "kitap": return [r.tur === "Kitap Bölümü" && r.kitap_adi && `“${r.kitap_adi}” içinde`, r.yayinevi].filter(Boolean).join(", ");
    case "proje": return [r.tur, r.proje_no && `no. ${r.proje_no}`, r.baslangic && `${r.baslangic} – ${r.bitis || "…"}`, r.butce].filter(Boolean).join(" · ");
    case "patent": return [r.basvuru_no, r.bulus_sahibi].filter(Boolean).join(" · ");
  }
  return "";
}
function badgeClass(v) {
  if (/^(SCI|SCI-E|SSCI|AHCI)$/.test(v)) return "sci solid";
  if (/^Q[1-4]$/.test(v)) return v.toLowerCase();
  if (/^TR Dizin$/i.test(v)) return "tr";
  if (/^(Scopus|ESCI)$/.test(v)) return "sc";
  if (/^Tamamlandı$/.test(v)) return "ok";
  if (/^(Devam|Başvuru)$/.test(v)) return "wait";
  if (/^Red$/.test(v)) return "no";
  return "plain";
}
function idxHtml(r) {
  const parts = {
    makale: [r.tur, r.quartile, r.kapsam && !/Diğer/.test(r.tur || "") ? r.kapsam : ""],
    bildiri: [r.kategori, r.tur], kitap: [r.tur, r.kapsam], proje: [r.rol, r.durum], patent: [r.tur, r.durum],
  }[r.kind] || [];
  return parts.filter(Boolean).map(v => `<span class="bdg ${badgeClass(v)}">${esc(v)}</span>`).join("");
}
function rowHtml(r) {
  const mon = `<label class="mon-w ${r.ay ? "" : "is-blank"}" title="Ayı değiştir">${r.ay ? AYK[r.ay - 1] : "ay ekle"}` +
    `<select class="mon" data-id="${r.id}" aria-label="Ay"><option value="">—</option>` +
    AYK.map((a, i) => `<option value="${i+1}" ${r.ay == i+1 ? "selected" : ""}>${S.meta.aylar[i]}</option>`).join("") + `</select></label>`;
  const f = [];
  if (r.manuel) f.push("elle eklendi");
  if (r.duzenlendi?.length) f.push(`<span class="w" title="${esc(r.duzenlendi.join(", "))}">düzenlendi</span>`);
  if (r.yoksiste_yok) f.push(`<span class="x" title="Son güncellemede YÖKSİS'te bulunamadı">YÖKSİS'te artık yok</span>`);
  if (r.gizli) f.push("gizli");
  const v = venue(r);
  return `<tr class="r k-${r.kind} ${r.gizli ? "gizli" : ""} ${S.sel === r.id ? "on" : ""}" data-id="${r.id}">
    <td><span class="kind">${KIND[r.kind]}</span>${mon}</td>
    <td><button type="button" class="t">${esc(r.baslik)}</button>${v ? `<div class="v">${esc(v)}</div>` : ""}
      <div class="mmeta">${esc(hocaAdi(r.hoca_id))} ${idxHtml(r)}</div>
      ${f.length ? `<div class="f">${f.join(" · ")}</div>` : ""}</td>
    <td class="who">${esc(hocaAdi(r.hoca_id))}</td>
    <td class="idx">${idxHtml(r)}</td></tr>`;
}

/* ---------------------------------------------------------------- düzenleme paneli */
function fieldHtml(f, r) {
  const val = r[f.ad] ?? "", id = "f_" + f.ad;
  const was = (r.duzenlendi || []).includes(f.ad)
    ? `<span class="was" title="YÖKSİS'teki değer: ${esc(r.kaynak?.[f.ad] ?? "(boş)")}">düzenlendi</span>` : "";
  let inp;
  if (f.tip === "long") inp = `<textarea id="${id}" rows="${f.ad === "baslik" ? 3 : 2}" class="${f.ad === "baslik" ? "title" : ""}">${esc(val)}</textarea>`;
  else if (f.tip === "month") inp = `<select id="${id}"><option value="">—</option>${S.meta.aylar.map((a, i) => `<option value="${i+1}" ${val == i+1 ? "selected" : ""}>${a}</option>`).join("")}</select>`;
  else if (f.tip === "select") {
    const o = [...(S.meta.secenek[f.secenek] || [])]; if (val && !o.includes(val)) o.unshift(val);
    inp = `<input id="${id}" list="dl_${f.ad}" value="${esc(val)}"><datalist id="dl_${f.ad}">${o.map(x => `<option value="${esc(x)}">`).join("")}</datalist>`;
  } else inp = `<input id="${id}" type="${f.tip === "int" ? "number" : "text"}" value="${esc(val)}">`;
  return `<div class="fld"><label for="${id}">${f.etiket}${was}</label>${inp}</div>`;
}
function openInsp(r, yeni = false) {
  if (S.edit && dirty() && !confirm("Kaydedilmemiş değişiklikler var. Vazgeçilsin mi?")) return;
  S.edit = {r, yeni}; S.sel = yeni ? null : r.id;
  const al = S.meta.alanlar[r.kind];
  const by = n => al.find(f => f.ad === n);
  const rest = al.filter(f => !["baslik", "yil", "ay"].includes(f.ad));
  let h = "";
  if (yeni || r.manuel) {
    h += `<div class="fld half"><div><label for="f__kind">Tür</label><select id="f__kind" ${yeni ? "" : "disabled"}>${Object.entries(KIND).map(([k, l]) => `<option value="${k}" ${k === r.kind ? "selected" : ""}>${l}</option>`).join("")}</select></div>
      <div><label for="f__hoca">Öğretim üyesi</label><select id="f__hoca">${S.hocalar.map(x => `<option value="${x.yok_id}" ${x.yok_id === r.hoca_id ? "selected" : ""}>${esc(x.ad)} ${esc(x.soyad)}</option>`).join("")}</select></div></div>`;
  }
  h += fieldHtml(by("baslik"), r);
  h += `<div class="fld half"><div>${fieldHtml(by("yil"), r).replace(/^<div class="fld">|<\/div>$/g, "")}</div><div>${fieldHtml(by("ay"), r).replace(/^<div class="fld">|<\/div>$/g, "")}</div></div>`;
  h += `<div class="insp-sec">Ayrıntılar</div>` + rest.map(f => fieldHtml(f, r)).join("");
  if (r.link) h += `<div class="fld"><a class="txt" href="${esc(r.link)}" target="_blank" rel="noopener">Yayını aç ↗</a></div>`;
  $("#inspBody").innerHTML = h;
  $("#inspKind").textContent = yeni ? "Yeni kayıt" : `${KIND[r.kind]} · ${r.yil ?? ""}`;
  $("#inspSrc").textContent = yeni ? "YÖKSİS'te olmayan bir çıktıyı elle ekleyin" :
    `${hocaAdi(r.hoca_id)} — ${r.manuel ? "elle eklendi" : "YÖKSİS kaydı; düzeltmeleriniz güncellemede korunur"}`;
  $("#inspReset").hidden = yeni || r.manuel || !(r.duzenlendi || []).length;
  $("#inspHide").hidden = yeni;
  $("#inspHide").textContent = r.manuel ? "Sil" : r.gizli ? "Tekrar göster" : "Gizle";
  $("#inspPrev").hidden = $("#inspNext").hidden = yeni;
  $("#inspSave").disabled = !yeni;
  $("#inspSave").textContent = yeni ? "Ekle" : "Kaydet";
  if (yeni) $("#f__kind").onchange = () => { S.edit = null; openInsp({...collect(), kind: $("#f__kind").value, hoca_id: $("#f__hoca").value}, true); };
  $("#insp").hidden = false;
  $("#insp").className = `insp k-${r.kind}`;
  history.replaceState(null, "", yeni ? location.pathname : `#kayit=${r.id}`);
  $$("#tbody tr.r").forEach(tr => tr.classList.toggle("on", +tr.dataset.id === S.sel));
  $(`#tbody tr[data-id="${S.sel}"]`)?.scrollIntoView({block: "nearest"});
  if (yeni) $("#f_baslik").focus();
}
function closeInsp(force) {
  if (!force && S.edit && dirty() && !confirm("Kaydedilmemiş değişiklikler var. Kapatılsın mı?")) return;
  S.edit = null; S.sel = null; $("#insp").hidden = true;
  history.replaceState(null, "", location.pathname);
  $$("#tbody tr.on").forEach(tr => tr.classList.remove("on"));
}
function collect() {
  const out = {};
  S.meta.alanlar[S.edit.r.kind].forEach(f => {
    let v = ($("#f_" + f.ad)?.value ?? "").trim();
    if (f.tip === "int" || f.tip === "month") v = v === "" ? null : parseInt(v, 10);
    out[f.ad] = v;
  });
  return out;
}
const norm = v => (v === "" || v === undefined ? null : v);
function changes() {
  const {r} = S.edit, v = collect(), ch = {};
  for (const [k, x] of Object.entries(v)) if (norm(r[k]) !== norm(x)) ch[k] = x;
  return ch;
}
function dirty() {
  if (!S.edit || S.edit.yeni) return S.edit?.yeni && !!$("#f_baslik")?.value.trim();
  return Object.keys(changes()).length > 0 || ($("#f__hoca") && $("#f__hoca").value !== S.edit.r.hoca_id);
}
function markDirty() {
  if (!S.edit || S.edit.yeni) return;
  const ch = changes();
  S.meta.alanlar[S.edit.r.kind].forEach(f => $("#f_" + f.ad)?.classList.toggle("mod", f.ad in ch));
  $("#inspSave").disabled = !dirty();
}
async function saveInsp() {
  const {r, yeni} = S.edit;
  if (yeni) {
    const v = collect(); if (!v.baslik) { toast("Başlık gerekli"); $("#f_baslik").focus(); return; }
    const n = await api("/api/kayitlar", {method: "POST", body: {kind: $("#f__kind").value, hoca_id: $("#f__hoca").value, data: v}});
    toast("Kayıt eklendi"); S.edit = null; await load(); const nr = S.rows.find(x => x.id === n.id); nr ? openInsp(nr) : closeInsp(true); return;
  }
  const body = {}, ch = changes();
  if (Object.keys(ch).length) body.data = ch;
  if (r.manuel && $("#f__hoca") && $("#f__hoca").value !== r.hoca_id) body.hoca_id = $("#f__hoca").value;
  if (!Object.keys(body).length) return;
  await api(`/api/kayitlar/${r.id}`, {method: "PATCH", body});
  toast("Kaydedildi"); S.edit = null;
  await load();
  const nr = S.rows.find(x => x.id === r.id);
  nr && pass(nr) ? openInsp(nr) : closeInsp(true);
}
function step(d) {
  const vis = visible(); if (!vis.length) return;
  let i = vis.findIndex(r => r.id === S.sel);
  i = i < 0 ? (d > 0 ? 0 : vis.length - 1) : Math.min(vis.length - 1, Math.max(0, i + d));
  openInsp(vis[i]);
}
async function setHidden(r) {
  await api(`/api/kayitlar/${r.id}`, {method: "PATCH", body: {gizli: !r.gizli}});
  toast(r.gizli ? "Kayıt tekrar listede" : "Kayıt gizlendi. “Gizlenenleri göster” ile görebilirsiniz.");
  S.edit = null; await load();
  const nr = S.rows.find(x => x.id === r.id); nr ? openInsp(nr) : closeInsp(true);
}

/* ---------------------------------------------------------------- öğretim üyeleri */
async function loadHocalar() {
  S.hocalar = await api("/api/hocalar");
  [...S.hoca].forEach(id => { if (!S.hocalar.some(h => h.yok_id === id && h.aktif)) S.hoca.delete(id); });
}
function renderHocaTable() {
  $("#hBody").innerHTML = S.hocalar.map(h => `<tr data-id="${h.yok_id}">
    <td><input data-f="ad" value="${esc(h.ad)}" aria-label="Ad"></td><td><input data-f="soyad" value="${esc(h.soyad)}" aria-label="Soyad"></td>
    <td><a href="https://akademik.yok.gov.tr/academician-details?authorGuidId=${h.yok_id}" target="_blank" rel="noopener">${h.yok_id}</a></td>
    <td><input type="checkbox" data-f="aktif" ${h.aktif ? "checked" : ""} aria-label="Aktif"></td>
    <td><small>${esc(h.son_senkron || "—")}</small></td>
    <td><button type="button" class="txt danger" data-del>Kaldır</button></td></tr>`).join("");
}
let araT;
async function hocaAra(q) {
  const el = $("#hSonuc");
  if (q.length < 3) { el.innerHTML = ""; return; }
  el.innerHTML = `<div class="res"><small>YÖK Akademik'te aranıyor…</small></div>`;
  try {
    const res = await api("/api/ara?q=" + encodeURIComponent(q));
    if (!res.length) { el.innerHTML = `<div class="res"><small>Sonuç bulunamadı.</small></div>`; return; }
    res.sort((a, b) => /BALIKES/.test(b.kadro_yeri) - /BALIKES/.test(a.kadro_yeri));
    el.innerHTML = res.map(r => `<div class="res"><div>${esc(r.ad)} ${esc(r.soyad)}<small>${esc(r.kadro_yeri)}</small></div>
      ${S.hocalar.some(h => h.yok_id === r.yok_id) ? "<small>listede</small>" : `<button type="button" class="btn ghost" data-add='${esc(JSON.stringify(r))}'>Ekle</button>`}</div>`).join("");
  } catch (e) { el.innerHTML = `<div class="res"><small>${esc(e.message)}</small></div>`; }
}

/* ---------------------------------------------------------------- güncelleme */
let pollT, wasRunning = false, showProg = false;
const fmt = s => s ? s.slice(0, 10).split("-").reverse().join(".") + (s.length > 10 ? " " + s.slice(11, 16) : "") : "—";
async function pollSync() {
  const j = await api("/api/senkron").catch(() => null); if (!j) return;
  const st = $("#syncStatus"), son = j.bitis || j.son_tam_senkron;
  st.classList.toggle("run", j.calisiyor);
  st.textContent = j.calisiyor ? `${j.kaynak === "otomatik" ? "Otomatik güncelleme" : "Güncelleniyor"}: ${j.ilerleme}/${j.toplam}` : `Son güncelleme ${fmt(son)}`;
  $("#syncSub").textContent = j.calisiyor ? j.mesaj : (j.oto_aktif ? `Sonraki otomatik: ${j.sonraki}` : "Otomatik güncelleme kapalı");
  $("#syncMeter").hidden = !j.calisiyor;
  const pct = (j.toplam ? 100 * j.ilerleme / j.toplam : 0) + "%";
  $$(".meter i").forEach(i => i.style.width = pct);
  $("#btnSync").disabled = j.calisiyor;
  $("#otoAktif").checked = j.oto_aktif;
  $("#otoBilgi").textContent = j.oto_aktif
    ? `Ayın ilk gününden sonra ilk fırsatta, tüm aktif öğretim üyeleri için son 5 yıl çekilir. Sonraki: ${j.sonraki}.`
    : "Kapalı. Veriler yalnızca bu pencereden elle güncellenir.";
  $("#sProg").hidden = !(j.calisiyor || showProg);
  $("#sProg .msg").textContent = j.mesaj;
  $("#sProg .errs").innerHTML = (j.hatalar || []).map(e => `<li>${esc(e)}</li>`).join("");
  $("#sBasla").disabled = j.calisiyor;
  $("#sBasla").textContent = j.calisiyor ? "Güncelleniyor…" : "Güncellemeyi başlat";
  clearTimeout(pollT);
  pollT = setTimeout(pollSync, j.calisiyor ? 1200 : 60000);
  if (wasRunning && !j.calisiyor) { await loadHocalar(); await load(); toast(j.hatalar?.length ? `Güncelleme bitti, ${j.hatalar.length} hata` : "Güncelleme tamamlandı"); }
  wasRunning = j.calisiyor;
}
function openSync() {
  $("#sMinYil").value = $("#basYil").value || NOW_Y - 4;
  $("#sTurler").innerHTML = Object.entries(KIND).map(([k, l]) => `<label><input type="checkbox" value="${k}" checked> ${l}</label>`).join("");
  $("#sHocalar").innerHTML = S.hocalar.filter(h => h.aktif).map(h => `<label><input type="checkbox" value="${h.yok_id}" checked> ${esc(h.ad)} ${esc(h.soyad)}</label>`).join("");
  showProg = false; $("#dlgSync").showModal(); pollSync();
}

/* ---------------------------------------------------------------- olaylar */
function bind() {
  $("#peopleToggle").onclick = () => {
    const expanded = $("#peopleToggle").getAttribute("aria-expanded") !== "true";
    $("#peopleToggle").setAttribute("aria-expanded", expanded);
    $(".side").classList.toggle("expanded", expanded);
  };
  const reload = () => { save(); load(); };
  $("#preset").onchange = e => { if (e.target.value !== "ozel") setRange(...PRESET[e.target.value]); else $("#basAy").focus(); reload(); };
  $$("#basAy, #bitAy, #basYil, #bitYil").forEach(s => s.addEventListener("change", () => { syncPreset(); reload(); }));
  $$("#kapsam, #aysizlar, #gizliler").forEach(s => s.addEventListener("change", reload));
  let t; $("#ara").addEventListener("input", () => { clearTimeout(t); t = setTimeout(load, 220); });
  $("#altTur").addEventListener("change", render);
  $("#btnEksik").onclick = () => { S.eksik = !S.eksik; render(); };
  $("#btnTemizle").onclick = () => {
    setRange(...PRESET["5y"]); S.kind = ""; S.hoca.clear(); S.eksik = false;
    $("#kapsam").value = ""; $("#altTur").value = ""; $("#ara").value = ""; $("#gizliler").checked = false; $("#aysizlar").checked = true;
    reload();
  };

  $("#navKind").onclick = e => { const b = e.target.closest("button"); if (!b) return; S.kind = b.dataset.k; save(); render(); $$("#navKind button").find(x => x.dataset.k === S.kind)?.focus(); };
  $("#navHoca").onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    const id = b.dataset.h;
    if (!id) S.hoca.clear(); else S.hoca.has(id) ? S.hoca.delete(id) : S.hoca.add(id);
    save(); render(); $$("#navHoca button").find(x => x.dataset.h === id)?.focus();
  };

  // tablo
  $("#tbody").addEventListener("change", async e => {
    if (!e.target.classList.contains("mon")) return;
    const id = +e.target.dataset.id, v = e.target.value ? +e.target.value : null;
    await api(`/api/kayitlar/${id}`, {method: "PATCH", body: {data: {ay: v}}});
    const r = S.rows.find(x => x.id === id); r.ay = v;
    if (!r.duzenlendi.includes("ay")) r.duzenlendi.push("ay");
    toast(v ? `${S.meta.aylar[v - 1]} olarak kaydedildi` : "Ay bilgisi kaldırıldı");
    if (S.edit?.r.id === id) $("#f_ay").value = v ?? "";
    render();
  });
  $("#tbody").addEventListener("click", e => {
    if (e.target.closest("select, a")) return;
    const tr = e.target.closest("tr.r"); if (!tr) return;
    openInsp(S.rows.find(x => x.id === +tr.dataset.id));
  });
  $("#btnYeni").onclick = () => openInsp({kind: S.kind || "makale", hoca_id: [...S.hoca][0] || S.hocalar.find(h => h.aktif)?.yok_id, yil: NOW_Y, duzenlendi: []}, true);

  // panel
  $("#inspBody").addEventListener("input", markDirty);
  $("#inspBody").addEventListener("change", markDirty);
  $("#inspForm").addEventListener("submit", e => { e.preventDefault(); saveInsp().catch(x => toast(x.message)); });
  $("#inspClose").onclick = () => closeInsp();
  $("#inspCancel").onclick = () => { if (S.edit?.yeni) closeInsp(); else { const r = S.edit.r; S.edit = null; openInsp(r); } };
  $("#inspPrev").onclick = () => step(-1);
  $("#inspNext").onclick = () => step(1);
  $("#inspReset").onclick = async () => {
    const r = S.edit.r; await api(`/api/kayitlar/${r.id}`, {method: "PATCH", body: {sifirla: true}});
    toast("YÖKSİS değerleri geri yüklendi"); S.edit = null; await load(); const nr = S.rows.find(x => x.id === r.id); nr ? openInsp(nr) : closeInsp(true);
  };
  $("#inspHide").onclick = async () => {
    const r = S.edit.r;
    if (r.manuel) {
      if (!confirm("Bu kayıt kalıcı olarak silinecek. Emin misiniz?")) return;
      await api(`/api/kayitlar/${r.id}`, {method: "DELETE"}); toast("Kayıt silindi"); closeInsp(true); load();
    } else setHidden(r);
  };

  // öğretim üyeleri
  $("#btnHocalar").onclick = $("#btnHocalar2").onclick = () => { renderHocaTable(); $("#hSonuc").innerHTML = ""; $("#hAra").value = ""; $("#dlgHoca").showModal(); };
  $("#hBody").addEventListener("change", async e => {
    const tr = e.target.closest("tr"), f = e.target.dataset.f; if (!f) return;
    const v = f === "aktif" ? (e.target.checked ? 1 : 0) : e.target.value.trim();
    await api(`/api/hocalar/${tr.dataset.id}`, {method: "PATCH", body: {[f]: v}});
    await loadHocalar(); render(); toast("Kaydedildi");
  });
  $("#hBody").addEventListener("click", async e => {
    if (!e.target.closest("[data-del]")) return;
    const id = e.target.closest("tr").dataset.id;
    if (!confirm(`${hocaAdi(id)} listeden kaldırılacak ve tüm kayıtları silinecek. Emin misiniz?`)) return;
    await api(`/api/hocalar/${id}`, {method: "DELETE"});
    await loadHocalar(); renderHocaTable(); load();
  });
  $("#hAra").addEventListener("input", e => { clearTimeout(araT); araT = setTimeout(() => hocaAra(e.target.value.trim()), 350); });
  $("#hSonuc").addEventListener("click", async e => {
    const b = e.target.closest("[data-add]"); if (!b) return;
    const r = JSON.parse(b.dataset.add);
    await api("/api/hocalar", {method: "POST", body: r});
    await loadHocalar(); renderHocaTable(); hocaAra($("#hAra").value.trim()); render();
    toast(`${r.ad} ${r.soyad} eklendi. Kayıtları için “YÖKSİS'ten güncelle”yi çalıştırın.`);
  });
  $("#hEkle").onclick = async () => {
    const v = $("#hId").value.trim(); if (!v) return $("#hId").focus();
    try { await api("/api/hocalar", {method: "POST", body: {yok_id: v}}); $("#hId").value = ""; await loadHocalar(); renderHocaTable(); render(); toast("Eklendi"); }
    catch (e) { toast(e.message); }
  };

  // güncelleme
  $("#btnSync").onclick = openSync;
  $("#otoAktif").onchange = async e => {
    await api("/api/otomatik", {method: "POST", body: {aktif: e.target.checked}});
    toast(e.target.checked ? "Her ay otomatik güncellenecek" : "Otomatik güncelleme kapatıldı"); pollSync();
  };
  $("#sBasla").onclick = async () => {
    const turler = $$("#sTurler input:checked").map(i => i.value), hocalar = $$("#sHocalar input:checked").map(i => i.value);
    if (!turler.length || !hocalar.length) return toast("En az bir tür ve bir öğretim üyesi seçin");
    try {
      await api("/api/senkron", {method: "POST", body: {turler, hocalar, min_yil: +$("#sMinYil").value, detay: $("#sDetay").checked}});
      showProg = true; wasRunning = true; pollSync();
    } catch (e) { toast(e.message); }
  };

  // excel
  $("#btnExcel").onclick = () => {
    const rows = visible(), c = {}; rows.forEach(r => c[r.kind] = (c[r.kind] || 0) + 1);
    const all = S.rows.filter(r => pass(r, "kind")), ca = {}; all.forEach(r => ca[r.kind] = (ca[r.kind] || 0) + 1);
    const draw = () => {
      const src = $("#xTumTurler").checked ? ca : c;
      const tot = Object.values(src).reduce((a, b) => a + b, 0);
      $("#xOzet").innerHTML = Object.keys(KIND).map(k => `<tr><td>${KIND_PL[k]}</td><td>${src[k] || 0}</td></tr>`).join("") + `<tr><td>Toplam</td><td>${tot}</td></tr>`;
    };
    $("#xTumTurler").checked = !S.kind;
    $("#xTumTurler").onchange = draw; draw();
    const who = S.hoca.size ? [...S.hoca].map(hocaAdi).join(", ") : "tüm öğretim üyeleri";
    $("#xDonem").textContent = `${rangeText()} · ${who}. Her sayfa yeniden eskiye sıralanır.` + (S.eksik ? " (“Ayı eksik” görünümü Excel'e uygulanmaz.)" : "");
    $("#dlgExcel").showModal();
  };
  $("#xIndir").onclick = () => {
    const extra = {birlestir: $("#xBirlestir").checked ? 1 : 0, hocalar: [...S.hoca].join(",")};
    if (!$("#xTumTurler").checked && S.kind) extra.turler = S.kind;
    if ($("#altTur").value) extra.alt_tur = $("#altTur").value;
    location.href = "/api/excel?" + serverParams(extra);
    $("#dlgExcel").close(); toast("Excel dosyası indiriliyor");
  };

  // klavye
  document.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && (e.key === "s" || e.key === "Enter") && !$("#insp").hidden) { e.preventDefault(); if (!$("#inspSave").disabled) saveInsp(); return; }
    if (typing()) { if (e.key === "Escape" && document.activeElement === $("#ara")) $("#ara").blur(); return; }
    if (e.key === "/") { e.preventDefault(); $("#ara").focus(); }
    else if (e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); step(1); }
    else if (e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); step(-1); }
    else if (e.key === "Escape" && !$("#insp").hidden) closeInsp();
  });
  $$("dialog").forEach(d => d.addEventListener("click", e => { if (e.target === d) d.close(); }));
  window.addEventListener("beforeunload", e => { if (dirty()) { e.preventDefault(); e.returnValue = ""; } });
}

(async function init() {
  S.meta = await api("/api/meta");
  fillSelects(); restore(); await loadHocalar(); bind(); await load(); pollSync();
  const m = location.hash.match(/kayit=(\d+)/);
  const r = m && S.rows.find(x => x.id === +m[1]);
  if (r) openInsp(r);
})().catch(e => document.body.insertAdjacentHTML("afterbegin", `<p style="padding:12px;margin:0;background:#fbeaea;color:#000">Arayüz yüklenemedi: ${esc(e.message)}</p>`));
