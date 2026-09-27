
import os
import re
import shutil
import subprocess
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, Response
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_BASE = BASE_DIR / "hasil_potongan"
ALLOWED_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4 GB

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_BASE.mkdir(exist_ok=True)

# job_id (nama folder) -> absolute path folder hasil.
# Perlu karena lokasi simpan sekarang bisa dipilih bebas, tidak hanya OUTPUT_BASE.
JOBS: dict[str, Path] = {}


def resolve_base_dir(lokasi: str) -> Path:
    """Ubah input lokasi dari web menjadi folder absolut yang siap dipakai."""
    lokasi = (lokasi or "").strip().strip('"').strip("'")
    if not lokasi:
        return OUTPUT_BASE
    p = Path(os.path.expandvars(os.path.expanduser(lokasi)))
    if not p.is_absolute():
        # path relatif dianggap relatif terhadap folder program
        p = (BASE_DIR / p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_job_dir(job: str) -> Path:
    safe_job = secure_filename(job)
    if safe_job in JOBS and JOBS[safe_job].is_dir():
        return JOBS[safe_job]
    # fallback untuk job lama yang tersimpan di OUTPUT_BASE
    return OUTPUT_BASE / safe_job


def clean_folder_name(name: str) -> str:
    name = (name or "").strip() or "potongan"
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", "_", name)
    return secure_filename(name) or "potongan"


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Potong Video per Detik</title>
<style>
*{box-sizing:border-box}body{font-family:Segoe UI,Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;min-height:100vh}
.wrap{max-width:760px;margin:0 auto;padding:32px 16px 60px}
.card{background:#1e293b;border:1px solid #334155;border-radius:16px;padding:24px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
h1{margin:0 0 4px;font-size:24px}p.sub{margin:0 0 20px;color:#94a3b8}
label{display:block;margin:14px 0 6px;font-weight:600}
input[type=file],input[type=number],input[type=text],select{width:100%;padding:10px 12px;border-radius:10px;border:1px solid #475569;background:#0f172a;color:#fff}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:600px){.row{grid-template-columns:1fr}}
button{margin-top:18px;width:100%;padding:13px;border:0;border-radius:12px;background:#22c55e;color:#052e16;font-weight:800;font-size:16px;cursor:pointer}
button:disabled{background:#475569;color:#cbd5e1;cursor:wait}
.hint{font-size:13px;color:#94a3b8;margin-top:6px}
#status{margin-top:16px;padding:12px;border-radius:10px;background:#0f172a;border:1px solid #334155;white-space:pre-wrap;font-size:14px}
#hasil{margin-top:16px}.item{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:10px 12px;margin:8px 0;font-size:14px}
.item a{color:#4ade80;text-decoration:none;font-weight:600}.pathbox{margin-top:10px;font-size:13px;color:#facc15;word-break:break-all}
video{width:100%;border-radius:12px;margin-top:10px;background:#000}
.topbtn{display:flex;gap:10px}.topbtn a{flex:1;text-align:center;background:#38bdf8;color:#082f49;padding:10px;border-radius:10px;font-weight:700;text-decoration:none}
.minibtn{display:flex;gap:8px;margin-top:8px}.mini{margin-top:0!important;width:auto!important;flex:1;padding:8px!important;font-size:13px!important;background:#334155!important;color:#e2e8f0!important}
.browbtn{display:flex;gap:8px;margin-top:8px}.browbtn .mini{flex:1}.lokrow{display:flex;gap:8px}.lokrow input{flex:1}.lokrow button{width:auto!important;margin-top:0!important;padding:10px 14px!important;font-size:14px!important;white-space:nowrap}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:50;padding:16px}
.modal.hidden{display:none}.mbox{background:#1e293b;border:1px solid #475569;border-radius:14px;max-width:560px;width:100%;max-height:80vh;display:flex;flex-direction:column;overflow:hidden}
.mhead{padding:14px 16px;border-bottom:1px solid #334155;font-weight:700}.mcur{padding:10px 16px;font-size:13px;color:#facc15;word-break:break-all;background:#0f172a}
.mlist{overflow:auto;padding:8px;min-height:200px}.mrow{display:flex;align-items:center;gap:8px;width:100%;text-align:left;background:transparent;color:#e2e8f0;border:0;border-radius:8px;padding:9px 10px;margin:0!important;font-size:14px!important;font-weight:400!important;cursor:pointer}.mrow:hover{background:#334155}.mfoot{padding:12px 16px;border-top:1px solid #334155;display:flex;gap:8px}.mfoot .mini{flex:1}.mnew{display:flex;gap:8px;padding:10px 16px;border-top:1px solid #334155}.mnew input{flex:1;padding:8px 10px;border-radius:8px;border:1px solid #475569;background:#0f172a;color:#fff}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
<h1>✂️ Potong Video per Detik</h1>
<p class="sub">Pilih video via web, tentukan tiap berapa detik, pilih nama folder hasil, lalu potong otomatis pakai ffmpeg.</p>

<label>1. Pilih video (bisa lebih dari 1)</label>
<input type="file" id="videos" accept="video/*,.mkv,.avi,.mov" multiple>
<video id="preview" controls style="display:none"></video>

<div class="row">
<div>
<label>2. Potong tiap berapa detik?</label>
<input type="number" id="detik" value="10" min="1" max="3600" step="1">
<div class="hint">Contoh: 10 = tiap 10 detik. Default 10.</div>
</div>
<div>
<label>3. Mode potong</label>
<select id="mode">
<option value="akurat" selected>Akurat pas detik (re-encode, disarankan)</option>
<option value="cepat">Cepat (copy, instan tapi durasi bisa meleset)</option>
</select>
<div class="hint">Akurat = tiap potongan PAS 10.00 dtk (agak lama). Cepat = instan tapi durasi mengikuti keyframe, bisa jadi 16+8.</div>
</div>
</div>

<label>4. Simpan di mana?</label>
<div class="lokrow">
<input type="text" id="lokasi" value="" placeholder="misal: D:\Hasil Potongan" oninput="updatePreview()">
<button type="button" onclick="bukaBrowser()">📂 Pilih Folder...</button>
</div>
<div class="hint">Klik <b>Pilih Folder...</b> untuk pilih folder seperti No.1, bisa jelajahi drive D:, E:, Desktop, dll. Atau ketik manual / pakai tombol cepat.</div>
<div class="minibtn">
<button type="button" class="mini" onclick="setLokasi('default')">📁 Default Proyek</button>
<button type="button" class="mini" onclick="setLokasi('desktop')">🖥️ Desktop</button>
<button type="button" class="mini" onclick="setLokasi('documents')">📄 Documents</button>
</div>
<label>Nama sub-folder hasil</label>
<input type="text" id="folder" value="potongan_10detik" placeholder="misal: potongan_tesis" oninput="updatePreview()">
<div class="hint" id="infopath"></div>
<div class="pathbox" id="previewpath"></div>

<button id="btn" onclick="proses()">Potong Sekarang</button>
<div id="status">Siap. Pilih video lalu klik Potong.</div>
<div id="hasil"></div>
</div>
</div>
<div class="modal hidden" id="modal">
<div class="mbox">
<div class="mhead">📂 Pilih folder penyimpanan</div>
<div class="mcur" id="mcur">...</div>
<div class="mlist" id="mlist"></div>
<div class="mnew">
<input type="text" id="mnewname" placeholder="Nama folder baru...">
<button type="button" class="mini" style="flex:none" onclick="buatFolder()">+ Buat</button>
</div>
<div class="mfoot">
<button type="button" class="mini" onclick="pilihBrowse()">✅ Pilih Folder Ini</button>
<button type="button" class="mini" onclick="tutupBrowser()">Batal</button>
</div>
</div>
</div>
<script>
const fileInput=document.getElementById('videos'),preview=document.getElementById('preview');
fileInput.onchange=()=>{if(fileInput.files.length){preview.style.display='block';preview.src=URL.createObjectURL(fileInput.files[0]);}};
let INFO={};
function setLokasi(k){
 const el=document.getElementById('lokasi');
 if(k==='default')el.value=INFO.output_base||'';
 else if(k==='desktop')el.value=INFO.desktop||'';
 else if(k==='documents')el.value=INFO.documents||'';
 updatePreview();
}
function updatePreview(){
 const lok=document.getElementById('lokasi').value||INFO.output_base||'';
 const fld=(document.getElementById('folder').value||'potongan').replace(/[\\/:*?"<>|]+/g,'_');
 document.getElementById('previewpath').textContent='📁 Akan tersimpan di: '+lok+'\\'+fld+'_[waktu]';
}
let CURPATH='';
async function bukaBrowser(){
 document.getElementById('modal').classList.remove('hidden');
 const start=document.getElementById('lokasi').value||INFO.output_base||'';
 await muatBrowse(start);
}
function tutupBrowser(){document.getElementById('modal').classList.add('hidden');}
async function muatBrowse(path){
 const list=document.getElementById('mlist'),cur=document.getElementById('mcur');
 list.innerHTML='<div class="hint">Memuat...</div>';
 try{
  if(!path){ // tampilkan daftar drive
   const r=await fetch('/api/drives');const j=await r.json();
   CURPATH='';
   cur.textContent='Pilih drive:';
   list.innerHTML='';
   for(const d of j.drives){
    const b=document.createElement('button');b.className='mrow';b.textContent='💾 '+d;
    b.onclick=()=>muatBrowse(d);list.appendChild(b);
   }
   const b2=document.createElement('button');b2.className='mrow';b2.textContent='📁 Default Proyek: '+(INFO.output_base||'');
   b2.onclick=()=>muatBrowse(INFO.output_base);list.appendChild(b2);
   return;
  }
  const r=await fetch('/api/browse?path='+encodeURIComponent(path));
  const j=await r.json();
  if(!r.ok)throw new Error(j.error||'Gagal');
  CURPATH=j.current;
  cur.textContent='📁 '+j.current;
  list.innerHTML='';
  const up=document.createElement('button');up.className='mrow';up.textContent='⬆️ Naik / Ganti Drive';
  up.onclick=()=>{if(j.parent)muatBrowse(j.parent);else muatBrowse('');};list.appendChild(up);
  if(!j.dirs.length){list.innerHTML+='<div class="hint">Tidak ada sub-folder. Klik "Pilih Folder Ini" atau buat folder baru.</div>';}
  for(const d of j.dirs){
   const b=document.createElement('button');b.className='mrow';b.textContent='📁 '+d.name;
   b.onclick=()=>muatBrowse(d.path);list.appendChild(b);
  }
 }catch(e){list.innerHTML='<div class="hint">❌ '+e.message+'</div>';}
}
function pilihBrowse(){
 if(!CURPATH){alert('Pilih dulu foldernya (klik 2x untuk masuk, lalu Pilih Folder Ini).');return;}
 document.getElementById('lokasi').value=CURPATH;
 updatePreview();tutupBrowser();
}
async function buatFolder(){
 const nama=document.getElementById('mnewname').value.trim();
 if(!nama){alert('Isi nama folder baru!');return;}
 if(!CURPATH){alert('Masuk dulu ke drive/folder tujuan!');return;}
 const r=await fetch('/api/mkdir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:CURPATH,name:nama})});
 const j=await r.json();
 if(!r.ok){alert(j.error||'Gagal');return;}
 document.getElementById('mnewname').value='';
 await muatBrowse(j.path);
}
async function proses(){
 const files=fileInput.files;
 const detik=document.getElementById('detik').value;
 const mode=document.getElementById('mode').value;
 const folder=document.getElementById('folder').value;
 const lokasi=document.getElementById('lokasi').value;
 const btn=document.getElementById('btn'),status=document.getElementById('status'),hasil=document.getElementById('hasil');
 if(!files.length){alert('Pilih dulu videonya!');return;}
 if(!detik||detik<1){alert('Detik harus >= 1');return;}
 if(!lokasi.trim()){alert('Isi dulu lokasi simpan (misal D:\\Hasil)!');return;}
 btn.disabled=true;hasil.innerHTML='';status.textContent='⏳ Mengupload & memotong... tunggu...';
 const fd=new FormData();
 for(const f of files)fd.append('videos',f);
 fd.append('detik',detik);fd.append('mode',mode);fd.append('folder',folder);fd.append('lokasi',lokasi);
 try{
  const r=await fetch('/api/potong',{method:'POST',body:fd});
  const j=await r.json();
  if(!r.ok)throw new Error(j.error||'Gagal memotong');
  status.textContent=`✅ Selesai! ${j.total_file} potongan dari ${j.jobs.length} video.\n📁 Tersimpan di:\n${j.save_path}`;
  let h=`<div class="pathbox">📁 Lokasi di laptop:<br><b>${j.save_path}</b></div>`;
  h+=`<div class="topbtn" style="margin-top:10px"><a href="/api/zip/${j.job_id}">⬇️ Download Semua (ZIP)</a></div>`;
   for(const jb of j.jobs){
    h+=`<div class="item"><b>${jb.asal}</b>: ${jb.jumlah} potongan (${jb.detik} dtk, ${jb.mode})<br>`;
    for(let k=0;k<jb.files.length;k++){const f=jb.files[k];const d=(jb.durasi&&jb.durasi[k]!=null)?` (${jb.durasi[k]} dtk)`:'';
     h+=`<a href="/api/download/${j.job_id}/${encodeURIComponent(f)}">⬇️ ${f}</a>${d}<br>`;}
    h+=`</div>`;
   }
  hasil.innerHTML=h;
 }catch(e){status.textContent='❌ Error: '+e.message;}
 btn.disabled=false;
}
fetch('/api/info').then(r=>r.json()).then(j=>{INFO=j;document.getElementById('lokasi').value=j.output_base;document.getElementById('infopath').textContent='Default: '+j.output_base+' | Desktop: '+j.desktop+' | Documents: '+j.documents;updatePreview();});
</script>
</body>
</html>"""


@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.get("/api/info")
def info():
    home = Path.home()
    return jsonify({
        "output_base": str(OUTPUT_BASE),
        "desktop": str(home / "Desktop"),
        "documents": str(home / "Documents"),
    })


@app.get("/api/drives")
def drives():
    import string
    found = []
    for h in string.ascii_uppercase:
        d = f"{h}:\\"
        if os.path.exists(d):
            found.append(d)
    if not found:
        found = [str(BASE_DIR), str(Path.home())]
    return jsonify({"drives": found})


@app.get("/api/browse")
def browse():
    raw = (request.args.get("path") or "").strip().strip('"').strip("'")
    if not raw:
        return jsonify({"error": "Path kosong"}), 400
    p = Path(os.path.expandvars(os.path.expanduser(raw)))
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    if not p.exists():
        return jsonify({"error": f"Folder tidak ada: {p}"}), 404
    if not p.is_dir():
        p = p.parent
    try:
        dirs = sorted(
            [{"name": q.name, "path": str(q)} for q in p.iterdir() if q.is_dir() and not q.name.startswith("$")],
            key=lambda x: x["name"].lower(),
        )
    except PermissionError:
        return jsonify({"error": "Tidak punya akses ke folder ini"}), 403
    parent = str(p.parent) if p.parent != p else ""
    return jsonify({"current": str(p), "parent": parent, "dirs": dirs})


@app.post("/api/mkdir")
def mkdir():
    data = request.get_json(force=True, silent=True) or {}
    raw = (data.get("path") or "").strip()
    name = clean_folder_name(data.get("name") or "")
    if not raw or not name:
        return jsonify({"error": "Path dan nama folder wajib diisi"}), 400
    p = Path(os.path.expandvars(os.path.expanduser(raw)))
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    target = p / name
    target.mkdir(parents=True, exist_ok=True)
    return jsonify({"path": str(target)})


def probe_duration(src: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
        capture_output=True, text=True,
    )
    return float(p.stdout.strip())


def run_ffmpeg_split(src: Path, dst_pattern: Path, detik: int, mode: str):
    if mode == "akurat":
        # Potong PAS per N detik via seek per potongan + re-encode.
        # (Segment muxer + force_key_frames tidak bisa diandalkan bila
        #  keyframe video jarang, hasilnya bisa 16+9 padahal setting 10.)
        import math
        total = probe_duration(src)
        n = max(1, int(math.ceil(total / detik - 1e-9)))
        for i in range(n):
            start = i * detik
            dur = min(float(detik), total - start)
            if dur <= 0.05:
                break
            out = str(dst_pattern).replace("%03d", f"{i:03d}")
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(src),
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac",
                "-map", "0",
                "-avoid_negative_ts", "make_zero",
                out,
            ]
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(p.stderr[-3000:])
        return
    else:  # cepat: copy tanpa re-encode, instan tapi HANYA bisa potong di keyframe
        cmd = [  # sehingga durasi bisa meleset (misal 16+8 padahal setting 10)
            "ffmpeg", "-y",
            "-i", str(src),
            "-c", "copy", "-map", "0",
            "-segment_time", str(detik),
            "-f", "segment",
            "-reset_timestamps", "1",
            "-break_non_keyframes", "1",
            str(dst_pattern),
        ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-3000:])


@app.post("/api/potong")
def potong():
    try:
        detik = int(request.form.get("detik", "10"))
    except ValueError:
        return jsonify({"error": "Detik harus angka"}), 400
    if not 1 <= detik <= 3600:
        return jsonify({"error": "Detik harus 1 - 3600"}), 400

    mode = request.form.get("mode", "akurat")
    if mode not in ("cepat", "akurat"):
        mode = "akurat"

    files = request.files.getlist("videos")
    if not files:
        return jsonify({"error": "Tidak ada video diupload"}), 400

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    folder = clean_folder_name(request.form.get("folder", "potongan"))
    try:
        base_dir = resolve_base_dir(request.form.get("lokasi", ""))
    except Exception as e:
        return jsonify({"error": f"Lokasi simpan tidak valid: {e}"}), 400
    job_dir = base_dir / f"{folder}_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    JOBS[job_dir.name] = job_dir

    jobs = []
    total = 0
    for f in files:
        orig = secure_filename(f.filename or "video.mp4") or "video.mp4"
        ext = Path(orig).suffix.lower() or ".mp4"
        if ext not in ALLOWED_EXT:
            ext = ".mp4"
        stem = Path(orig).stem[:40] or "video"
        tmp_src = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
        f.save(tmp_src)
        try:
            pattern = job_dir / f"{stem}_{detik}dtk_%03d{ext}"
            run_ffmpeg_split(tmp_src, pattern, detik, mode)
        finally:
            if tmp_src.exists():
                tmp_src.unlink()
        out_files = sorted(p.name for p in job_dir.glob(f"{stem}_{detik}dtk_*"))
        if not out_files:  # fallback: ffmpeg kadang hanya 1 file tanpa segment
            out_files = sorted(p.name for p in job_dir.iterdir() if p.is_file())
        durasi = []
        for n_ in out_files:
            try:
                durasi.append(round(probe_duration(job_dir / n_), 2))
            except Exception:
                durasi.append(None)
        total += len(out_files)
        jobs.append({"asal": orig, "jumlah": len(out_files), "detik": detik, "mode": mode, "files": out_files, "durasi": durasi})

    return jsonify({
        "job_id": job_dir.name,
        "save_path": str(job_dir),
        "total_file": total,
        "jobs": jobs,
    })


@app.get("/api/download/<job>/<fname>")
def download(job, fname):
    job_dir = get_job_dir(job)
    safe_file = secure_filename(fname)
    path = job_dir / safe_file
    if not path.is_file():
        return jsonify({"error": "File tidak ditemukan"}), 404
    return send_file(path, as_attachment=True)


@app.get("/api/zip/<job>")
def zip_job(job):
    job_dir = get_job_dir(job)
    if not job_dir.is_dir():
        return jsonify({"error": "Folder tidak ditemukan"}), 404
    zip_path = job_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(job_dir.iterdir()):
            if p.is_file():
                z.write(p, p.name)
    return send_file(zip_path, as_attachment=True, download_name=f"{job_dir.name}.zip")


if __name__ == "__main__":
    print(f"Upload dir : {UPLOAD_DIR}")
    print(f"Hasil      : {OUTPUT_BASE}")
    print("Buka http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
