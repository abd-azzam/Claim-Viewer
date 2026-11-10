// Interface language for Claim Viewer. Only the chrome is translated: a dictionary maps the English
// label to its Indonesian form, and the reverse map switches back. User content (claims, notes,
// PDFs, chats) is never touched, because those containers are skipped outright.
const CV_LANG_KEY = 'cv:lang';

const CV_ID = {
  'List': 'Daftar', 'Graph': 'Grafik', 'Library': 'Pustaka',
  'Find words in quotes': 'Cari kata dalam kutipan', 'Quote or gist': 'Kutipan atau ringkasan',
  'Collection': 'Koleksi', 'Reading': 'Bacaan', 'Type of claim': 'Jenis klaim', 'Pathway': 'Jalur',
  'Axis A': 'Sumbu A', 'Axis B': 'Sumbu B', 'Change in axis B': 'Perubahan sumbu B',
  'Kind of evidence': 'Jenis bukti', 'Own or cited claim': 'Klaim sendiri atau dikutip',
  'Any author': 'Semua penulis', 'Own': 'Sendiri', 'Cited': 'Dikutip',
  'Group the list by': 'Kelompokkan daftar menurut', 'Group: source': 'Kelompok: sumber',
  'Group: pathway': 'Kelompok: jalur', 'Group: axis A': 'Kelompok: sumbu A',
  'Group: axis B': 'Kelompok: sumbu B', 'Group: tag': 'Kelompok: tag', 'Group: section': 'Kelompok: bagian',
  'Links to other readings': 'Tautan ke bacaan lain', 'Any links': 'Semua tautan',
  'Connected to reading': 'Terhubung ke bacaan', 'Any reading': 'Semua bacaan',
  '+ Folder': '+ Folder', 'Find a note': 'Cari catatan', 'Tag': 'Tag', 'Sub-tag': 'Sub-tag',
  'Any': 'Semua', 'Title, body, tag': 'Judul, isi, tag', 'All roles': 'Semua peran',
  'All Pathway': 'Semua jalur', 'All Determinant': 'Semua determinan', 'All Effect': 'Semua efek',
  'Any sign': 'Arah apa pun', 'All evidence': 'Semua bukti', 'Group: source': 'Kelompok: sumber',
  'Claims': 'Klaim', 'Notes': 'Catatan', 'Export': 'Ekspor', 'Links': 'Tautan',
  'Merge readings': 'Gabung bacaan', 'Notes list': 'Daftar catatan',
  'Reset layout': 'Atur ulang tata letak', 'Undo': 'Urungkan', 'Delete': 'Hapus',
  'Layers': 'Lapisan', 'Claim network': 'Jaringan klaim', 'Connected claims': 'Klaim terhubung',
  'Roles': 'Peran', 'Idea map / hierarchy': 'Peta ide / hierarki', 'Create nodes': 'Buat simpul',
  'Group': 'Kelompok', 'topic': 'topik', 'PDF source': 'sumber PDF', 'source + topic': 'sumber + topik',
  'Re-layout': 'Tata ulang', 'Fit': 'Pas', 'Ask AI': 'Tanya AI', 'Clear chat': 'Hapus obrolan',
  'AI settings': 'Pengaturan AI', 'Send': 'Kirim', 'Ask about this reading': 'Tanya tentang bacaan ini',
  'Settings': 'Pengaturan', 'General': 'Umum', 'Appearance': 'Tampilan', 'Word': 'Word',
  'New': 'Baru', 'About': 'Tentang', 'Feedback': 'Masukan', 'Advanced': 'Lanjutan',
  'Language': 'Bahasa', 'Theme': 'Tema', 'Font': 'Huruf', 'UI scale': 'Skala antarmuka',
  'Save': 'Simpan', 'Cancel': 'Batal', 'Close': 'Tutup', 'Copy': 'Salin', 'Edit': 'Ubah',
  'To note': 'Ke catatan', 'Show in graph': 'Tampilkan di grafik',
  'New note': 'Catatan baru', 'Keyword index': 'Indeks kata kunci', 'Note graph': 'Grafik catatan',
  'Note': 'Catatan', 'Add PDF': '+ Tambah PDF', 'Filter readings…': 'Saring bacaan…',
  'Type': 'Jenis', 'Title': 'Judul', 'Year': 'Tahun', 'Author': 'Penulis',
  'readings': 'bacaan', 'reading': 'bacaan', 'items': 'item', 'Type of claim': 'Jenis klaim',
  'Pathway': 'Jalur', 'Quote or gist': 'Kutipan atau ringkasan', 'Keyword index': 'Indeks kata kunci',
  'Copy text': 'Salin teks', 'Add as claim': 'Jadikan klaim', 'Define': 'Definisikan',
  'Remove highlight': 'Hapus sorotan', 'Note on this passage': 'Catatan pada bagian ini',
  'Connect to another reading…': 'Hubungkan ke bacaan lain…', 'Dark mode': 'Mode gelap',
  'Show tutorial': 'Tampilkan panduan', 'Back': 'Kembali', 'Next': 'Lanjut',
  'Skip tutorial': 'Lewati panduan', 'Finish': 'Selesai', 'Start': 'Mulai'
};

const CV_EN = {};
for (const en in CV_ID) CV_EN[CV_ID[en]] = en;

// Content that must never be rewritten: claims, notes, PDF text, chat answers.
const CV_SKIP = '#list, #zklist, #ailog, #gout, #gv, .textLayer, #rd, .card, .zkc, .aim, .aih, textarea, input[type=text], input[type=search], script, style, [contenteditable="true"]';

function cvLang() {
  try { return (localStorage.getItem(CV_LANG_KEY) || 'en') === 'id' ? 'id' : 'en'; } catch (e) { return 'en'; }
}

function cvPhrase(text, to) {
  const s = String(text || '');
  const trimmed = s.trim();
  if (!trimmed) return s;
  const map = to === 'id' ? CV_ID : CV_EN;
  const hit = map[trimmed];
  if (!hit) return s;
  return s.replace(trimmed, hit);
}

function cvApplyLang(root) {
  const to = cvLang();
  const scope = root || document.body;
  const skip = el => !el || (el.closest && el.closest(CV_SKIP));
  const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !/\S/.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
      return skip(node.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    }
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(n => { const v = cvPhrase(n.nodeValue, to); if (v !== n.nodeValue) n.nodeValue = v; });

  ['placeholder', 'title', 'aria-label'].forEach(attr => {
    scope.querySelectorAll('[' + attr + ']').forEach(el => {
      if (skip(el)) return;
      const v = cvPhrase(el.getAttribute(attr), to);
      if (v !== el.getAttribute(attr)) el.setAttribute(attr, v);
    });
  });
  document.documentElement.lang = to;
}

function cvSetLang(lang) {
  const to = lang === 'id' ? 'id' : 'en';
  try { localStorage.setItem(CV_LANG_KEY, to); } catch (e) {}
  if (typeof store !== 'undefined' && store.set) { try { store.set(CV_LANG_KEY, to); } catch (e) {} }
  cvApplyLang();
  window.dispatchEvent(new CustomEvent('cv-language', { detail: to }));
  return to;
}

window.cvLang = cvLang;
window.cvSetLang = cvSetLang;
window.cvApplyLang = cvApplyLang;
window.cvPhrase = cvPhrase;
