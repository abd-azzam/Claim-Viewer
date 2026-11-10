// A guided tour of the app, and the first-run chooser that starts it. It runs once: skipping or
// finishing stores cv:tour-done, and choosing a language stores cv:lang. Both are offered again from
// Settings.
const CV_TOUR_KEY = 'cv:tour-done';

const CV_TOUR = [
  { sel: '.tabs', en: ['Three workspaces', 'List reads and edits claims, Graph draws the connections, Library holds your PDFs and folders.'],
    id: ['Tiga ruang kerja', 'Daftar untuk membaca dan menyunting klaim, Grafik menggambar hubungannya, Pustaka menyimpan PDF dan foldernya.'] },
  { go: 'lib', sel: '#libtbl', en: ['Build your library', 'Add PDFs, organise readings into folders and edit bibliographic details. Use the Library search to find a reading by title or author.'],
    id: ['Kelola pustaka', 'Tambahkan PDF, kelompokkan bacaan ke dalam folder, dan sunting informasi bibliografi. Gunakan pencarian Pustaka untuk menemukan judul atau penulis.'] },
  { go: 'list', sel: '#flt', en: ['Filters', 'Narrow the claim list by collection, reading, type, pathway, axis and evidence.'],
    id: ['Penyaring', 'Persempit daftar klaim menurut koleksi, bacaan, jenis, jalur, sumbu, dan bukti.'] },
  { sel: '#list', en: ['Claims', 'Select text in the PDF to make a claim. Click a claim to copy it, edit it, or file it into a note.'],
    id: ['Klaim', 'Pilih teks di PDF untuk membuat klaim. Klik klaim untuk menyalin, menyunting, atau memasukkannya ke catatan.'] },
  { sel: '#rd', en: ['The reading', 'Read here. Zoom with Ctrl and the wheel, highlight in four colours, and right-click a passage for more actions.'],
    id: ['Bacaan', 'Baca di sini. Perbesar dengan Ctrl dan roda mouse, sorot dengan empat warna, dan klik kanan bagian teks untuk tindakan lain.'] },
  { sel: '#reading-tabs', en: ['Move between readings', 'Open several PDFs as tabs. Type a page number to jump there, or use full screen when you want more room to read.'],
    id: ['Beralih antarbacaan', 'Buka beberapa PDF sebagai tab. Ketik nomor halaman untuk melompat, atau gunakan layar penuh agar ruang baca lebih luas.'] },
  { sel: '#rt', en: ['Scan, listen and save', 'Use Scan OCR when PDF text cannot be selected. The progress box shows the page being scanned. Read aloud plays the text, and Save PDF exports the reading with your highlights.'],
    id: ['Pindai, dengarkan, dan simpan', 'Gunakan Pindai OCR jika teks PDF tidak dapat dipilih. Kotak progres menampilkan halaman yang dipindai. Baca nyaring membacakan teks, dan Simpan PDF mengekspor bacaan beserta sorotan.'] },
  { sel: '.rtabs', en: ['Ask AI about a reading', 'Save a provider and model in Settings, then open Ask AI. When a response includes page links, use them to check the answer against the PDF.'],
    id: ['Tanya AI tentang bacaan', 'Simpan penyedia dan model di Pengaturan, lalu buka Tanya AI. Jika jawaban menyertakan tautan halaman, periksa jawaban tersebut di PDF.'] },
  { go: 'graph', sel: '#gc2', en: ['The graph', 'Layers, the claim network, connected claims, roles, and the idea map of your notes.'],
    id: ['Grafik', 'Lapisan, jaringan klaim, klaim terhubung, peran, dan peta ide dari catatan Anda.'] },
  { go: 'notes', sel: '.bar .tabs.ln', en: ['Claims and Notes', 'Switch between the claim list and the notes workspace, where ideas, tags and child notes live.'],
    id: ['Klaim dan Catatan', 'Beralih antara daftar klaim dan ruang catatan, tempat ide, tag, dan catatan anak berada.'] },
  { go: 'list', sel: '#cv-settings-button', en: ['Cite in Word', 'Close Word before installing the add-in from Settings. Reopen Word, save the document and use the Claim Viewer ribbon to insert citations. Add a bibliography once to have it refresh after each new citation.'],
    id: ['Kutip di Word', 'Tutup Word sebelum memasang add-in dari Pengaturan. Buka Word, simpan dokumen, lalu sisipkan kutipan lewat tab Claim Viewer. Tambahkan bibliografi sekali agar diperbarui setiap kali kutipan baru ditambahkan.'] },
  { sel: '#cv-settings-button', en: ['Back up and export', 'Use Backup in Settings to save your research files. Use Reference Managers to export an RIS file for Zotero or another reference manager.'],
    id: ['Cadangkan dan ekspor', 'Gunakan Cadangan di Pengaturan untuk menyimpan berkas riset. Gunakan Pengelola Referensi untuk mengekspor berkas RIS bagi Zotero atau pengelola lain.'] },
  { sel: '#cv-settings-button', en: ['Make Claim Viewer yours', 'Change language, colour scheme and interface size in Settings. Use Check for Updates to check GitHub, and open Tutorial to revisit these steps.'],
    id: ['Sesuaikan Claim Viewer', 'Ubah bahasa, tema, dan ukuran antarmuka di Pengaturan. Gunakan Periksa Pembaruan untuk memeriksa GitHub, dan buka Panduan untuk melihat langkah ini lagi.'] }
];

let cvTourStep = 0;
let cvTourRoot = null;
let cvOnboarding = false;
let cvTourOpener = null;

function cvTourText(entry) {
  const pair = cvLang() === 'id' ? entry.id : entry.en;
  return { title: pair[0], body: pair[1] };
}

function cvTourTarget(sel) {
  const el = document.querySelector(sel);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  if (r.width < 8 || r.height < 8) return null;                 // exists but is not laid out
  if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return null;
  return { el, r };
}

function cvTourClose(done) {
  if (cvTourRoot) { cvTourRoot.remove(); cvTourRoot = null; }
  document.removeEventListener('keydown', cvTourKeys, true);
  if (cvTourOpener?.isConnected) cvTourOpener.focus();
  cvTourOpener = null;
  if (done) { try { localStorage.setItem(CV_TOUR_KEY, '1'); } catch (e) {}
    try { if (typeof store !== 'undefined' && store.set) store.set(CV_TOUR_KEY, '1'); } catch (e) {} }
  cvOnboarding = false;
}

function cvTourKeys(e) {
  if (e.key === 'Escape') { e.preventDefault(); cvTourClose(true); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); cvTourGo(1); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); cvTourGo(-1); }
}

function cvTourGo(delta) {
  const next = cvTourStep + delta;
  if (next < 0) return;
  if (next >= CV_TOUR.length) { cvTourClose(true); return; }
  cvTourStep = next;
  cvTourRender();
}

function cvTourRender() {
  if (!cvTourRoot) return;
  const entry = CV_TOUR[cvTourStep];
  if (entry.go && typeof show === 'function') {
    try {
      show(entry.go);
      if (entry.go === 'notes') { const n = document.getElementById('vn'); if (n) n.click(); }
      if (entry.go === 'list') { const c = document.getElementById('vc'); if (c) c.click(); }
    } catch (e) {}
  }
  const hit = cvTourTarget(entry.sel);
  const card = cvTourRoot.querySelector('.cv-tour-card');
  const ring = cvTourRoot.querySelector('.cv-tour-ring');
  const { title, body } = cvTourText(entry);
  card.querySelector('h3').textContent = title;
  card.querySelector('p').textContent = body;
  card.querySelector('.cv-tour-step').textContent = (cvTourStep + 1) + ' / ' + CV_TOUR.length;
  card.querySelector('[data-tour-back]').disabled = cvTourStep === 0;
  card.querySelector('[data-tour-next]').textContent = cvTourStep === CV_TOUR.length - 1
    ? (cvLang() === 'id' ? 'Selesai' : 'Finish') : (cvLang() === 'id' ? 'Lanjut' : 'Next');
  if (!hit) { ring.hidden = true; card.style.left = 'auto'; card.style.right = '24px'; card.style.top = '24px'; return; }
  const pad = 6, r = hit.r;
  ring.hidden = false;
  ring.style.cssText = 'position:fixed;pointer-events:none;border-radius:10px;z-index:10000;box-shadow:0 0 0 9999px rgba(0,0,0,.55),0 0 0 2px var(--acc) inset;';
  ring.style.left = (r.left - pad) + 'px'; ring.style.top = (r.top - pad) + 'px';
  ring.style.width = (r.width + pad * 2) + 'px'; ring.style.height = (r.height + pad * 2) + 'px';
  const below = r.bottom + 14;
  const wide = card.offsetWidth, height = card.offsetHeight;
  card.style.left = Math.max(12, Math.min(innerWidth - wide - 12, r.left)) + 'px';
  card.style.top = (below + height < innerHeight ? below : Math.max(12, r.top - height - 14)) + 'px';
  card.style.right = 'auto';
}

function cvTourStart(step) {
  cvTourClose(false);
  cvTourOpener = document.activeElement;
  cvTourStep = step || 0;
  const root = document.createElement('div');
  root.className = 'cv-tour';
  root.innerHTML =
    '<div class="cv-tour-ring" hidden></div>' +
    '<div class="cv-tour-card" role="dialog" aria-modal="false" aria-labelledby="cv-tour-title" style="position:fixed;z-index:10001;width:min(340px,calc(100vw - 32px));max-height:calc(100vh - 48px);overflow:auto">' +
    '<small class="cv-tour-step"></small>' +
    '<h3 id="cv-tour-title"></h3><p></p>' +
    '<div class="cv-tour-actions">' +
    '<button type="button" data-tour-skip>' + (cvLang() === 'id' ? 'Lewati panduan' : 'Skip tutorial') + '</button>' +
    '<span></span>' +
    '<button type="button" data-tour-back>' + (cvLang() === 'id' ? 'Kembali' : 'Back') + '</button>' +
    '<button type="button" data-tour-next></button>' +
    '</div></div>';
  document.body.append(root);
  cvTourRoot = root;
  root.querySelector('[data-tour-skip]').onclick = () => cvTourClose(true);
  root.querySelector('[data-tour-back]').onclick = () => cvTourGo(-1);
  root.querySelector('[data-tour-next]').onclick = () => cvTourGo(1);
  document.addEventListener('keydown', cvTourKeys, true);
  cvTourRender();
  root.querySelector('[data-tour-next]').focus();
}

// The first-run chooser: language first, then the tour. It appears only while cv:lang is unset, so a
// returning reader is never interrupted.
function cvOnboard() {
  if (cvOnboarding || cvTourRoot) return;
  let lang = null;
  try { lang = localStorage.getItem(CV_LANG_KEY); } catch (e) {}
  if (lang) {
    let done = false;
    try { done = localStorage.getItem(CV_TOUR_KEY) === '1'; } catch (e) {}
    if (!done) cvTourStart(0);
    return;
  }
  cvOnboarding = true;
  const d = document.createElement('dialog');
  d.className = 'cv-welcome';
  d.setAttribute('aria-labelledby', 'cv-welcome-title');
  d.innerHTML =
    '<h2 id="cv-welcome-title">Welcome to Claim Viewer</h2>' +
    '<p>Choose the language of the interface. You can change it later in Settings.</p>' +
    '<div class="cv-welcome-lang">' +
    '<button type="button" data-lang="en"><strong>English</strong><small>Continue in English</small></button>' +
    '<button type="button" data-lang="id"><strong>Bahasa Indonesia</strong><small>Lanjutkan dalam bahasa Indonesia</small></button>' +
    '</div>' +
    '<p class="cv-welcome-hint">A short guided tour starts next. You can skip it at any step.</p>';
  document.body.append(d);
  d.querySelectorAll('[data-lang]').forEach(b => b.onclick = () => {
    cvSetLang(b.dataset.lang);
    d.close(); d.remove();
    cvOnboarding = false;
    setTimeout(() => cvTourStart(0), 150);
  });
  d.addEventListener('close', () => { d.remove(); cvOnboarding = false; });
  d.showModal();
}

window.cvTourStart = cvTourStart;
window.cvOnboard = cvOnboard;
document.getElementById('cv-tour-button')?.addEventListener('click', () => cvTourStart(0));

function cvBoot() {
  try { cvApplyLang(); } catch (e) {}
  try { cvOnboard(); } catch (e) {}
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(cvBoot, 700));
else setTimeout(cvBoot, 700);
window.addEventListener('pywebviewready', () => setTimeout(() => { try { cvApplyLang(); } catch (e) {} }, 900));
