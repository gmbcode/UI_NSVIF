// Math Helpers
function getPolygonArea(pts) {
    let area = 0;
    for (let i = 0; i < pts.length; i++) {
        let j = (i + 1) % pts.length;
        area += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1];
    }
    return Math.abs(area / 2);
}

function computeSetbackPolygon(vertices, setback_h, setback_v) {
    const n = vertices.length;
    if (n < 3) return [];
    let poly = vertices.map(v => [v[0], v[1]]);
    let area = 0;
    for (let i = 0; i < n; i++) {
        const p1 = poly[i];
        const p2 = poly[(i + 1) % n];
        area += p1[0] * p2[1] - p2[0] * p1[1];
    }
    if (area < 0) poly.reverse();

    const lines = [];
    for (let i = 0; i < n; i++) {
        const p1 = poly[i];
        const p2 = poly[(i + 1) % n];
        const dx = p2[0] - p1[0];
        const dy = p2[1] - p1[1];
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 1e-6) continue;

        const ux = dx / len, uy = dy / len;
        const nx = -uy, ny = ux;
        const isHorizontal = Math.abs(dx) > Math.abs(dy);
        const d = isHorizontal ? setback_v : setback_h;

        lines.push({ p1: [p1[0] + d * nx, p1[1] + d * ny], dir: [ux, uy] });
    }

    const offsetVertices = [];
    const m = lines.length;
    for (let i = 0; i < m; i++) {
        const l1 = lines[(i - 1 + m) % m];
        const l2 = lines[i];
        const det = l2.dir[0] * l1.dir[1] - l1.dir[0] * l2.dir[1];

        if (Math.abs(det) < 1e-6) {
            offsetVertices.push([l2.p1[0], l2.p1[1]]);
        } else {
            const t1 = ((l2.p1[1] - l1.p1[1]) * l2.dir[0] - (l2.p1[0] - l1.p1[0]) * l2.dir[1]) / det;
            offsetVertices.push([l1.p1[0] + t1 * l1.dir[0], l1.p1[1] + t1 * l1.dir[1]]);
        }
    }
    return offsetVertices;
}

function isPointInPolygon(point, vs) {
    let x = point[0], y = point[1];
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        let xi = vs[i][0], yi = vs[i][1];
        let xj = vs[j][0], yj = vs[j][1];
        let intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

function getBuildableArea(shrunk, tx, ty, tr) {
    if (!shrunk || shrunk.length < 3) return 0;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    shrunk.forEach(p => {
        if (p[0] < minX) minX = p[0];
        if (p[0] > maxX) maxX = p[0];
        if (p[1] < minY) minY = p[1];
        if (p[1] > maxY) maxY = p[1];
    });

    const w = maxX - minX, h = maxY - minY;
    if (w <= 0 || h <= 0) return 0;

    const steps = 60, dx = w / steps, dy = h / steps;
    let count = 0;

    for (let i = 0; i < steps; i++) {
        const x = minX + (i + 0.5) * dx;
        for (let j = 0; j < steps; j++) {
            const y = minY + (j + 0.5) * dy;
            if (isPointInPolygon([x, y], shrunk)) {
                if (((x - tx) ** 2 + (y - ty) ** 2) >= tr * tr) count++;
            }
        }
    }
    return Math.round((count / (steps * steps)) * (w * h));
}

// PlotEditor Class
class PlotEditor {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.margin = 35;
        this.vertices = [[15, 15], [92, 10], [86, 69], [16, 81]];
        this.setback_h = 8;
        this.setback_v = 25;

        this.draggedIndex = -1;
        this.hoveredIndex = -1;
        this.snapToGrid = true;
        this.onChangeCallback = null;

        this.resize();
        this.initEvents();
    }

    resize() {
        const parent = this.canvas.parentElement;
        this.canvas.width = parent.clientWidth;
        this.canvas.height = parent.clientHeight;
        const size = Math.min(this.canvas.width, this.canvas.height);
        this.scale = (size - 2 * this.margin) / 100;
        this.offsetX = (this.canvas.width - (100 * this.scale)) / 2;
        this.offsetY = (this.canvas.height - (100 * this.scale)) / 2;
        this.draw();
    }

    initEvents() {
        this.canvas.addEventListener('mousedown', e => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', e => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', () => this.draggedIndex = -1);
        this.canvas.addEventListener('mouseleave', () => this.draggedIndex = -1);
        this.canvas.addEventListener('dblclick', e => this.onDoubleClick(e));
    }

    tx(wx) { return this.offsetX + wx * this.scale; }
    ty(wy) { return this.canvas.height - this.offsetY - wy * this.scale; }
    invTx(cx) { return (cx - this.offsetX) / this.scale; }
    invTy(cy) { return (this.canvas.height - this.offsetY - cy) / this.scale; }

    getClosestVertex(wx, wy, threshold) {
        let minDist = Infinity, minIdx = -1;
        this.vertices.forEach((v, i) => {
            const dist = Math.sqrt((v[0] - wx) ** 2 + (v[1] - wy) ** 2);
            if (dist < minDist && dist < threshold) { minDist = dist; minIdx = i; }
        });
        return minIdx;
    }

    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        this.draggedIndex = this.getClosestVertex(this.invTx(e.clientX - rect.left), this.invTy(e.clientY - rect.top), 15 / this.scale);
    }

    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const wx = this.invTx(e.clientX - rect.left), wy = this.invTy(e.clientY - rect.top);

        if (this.draggedIndex !== -1) {
            let nx = Math.max(0, Math.min(100, wx)), ny = Math.max(0, Math.min(100, wy));
            if (this.snapToGrid) { nx = Math.round(nx); ny = Math.round(ny); }
            this.vertices[this.draggedIndex] = [nx, ny];
            if (this.onChangeCallback) this.onChangeCallback();
            this.draw();
        } else {
            const newHover = this.getClosestVertex(wx, wy, 15 / this.scale);
            if (newHover !== this.hoveredIndex) {
                this.hoveredIndex = newHover;
                this.draw();
            }
        }
    }

    onDoubleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const wx = this.invTx(e.clientX - rect.left), wy = this.invTy(e.clientY - rect.top);
        if(this.vertices.length >= 3) {
            this.vertices.splice(1, 0, [Math.round(wx), Math.round(wy)]);
            if (this.onChangeCallback) this.onChangeCallback();
            this.draw();
        }
    }

    draw() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Grid
        ctx.strokeStyle = '#2d2d35';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 100; i += 10) {
            ctx.beginPath(); ctx.moveTo(this.tx(i), this.ty(0)); ctx.lineTo(this.tx(i), this.ty(100)); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(this.tx(0), this.ty(i)); ctx.lineTo(this.tx(100), this.ty(i)); ctx.stroke();

            ctx.fillStyle = '#5a5a63';
            ctx.font = '9px monospace';
            ctx.textAlign = 'center';
            if(i > 0 && i < 100) ctx.fillText(i + "'", this.tx(i), this.ty(0) + 12);
        }

        // Buildable Area (Setback Polygon)
        const shrunk = computeSetbackPolygon(this.vertices, this.setback_h, this.setback_v);
        const tx_val = parseFloat(document.getElementById('treeX').value) || 0;
        const ty_val = parseFloat(document.getElementById('treeY').value) || 0;
        const tr_val = parseFloat(document.getElementById('treeRadius').value) || 0;

        if (shrunk && shrunk.length >= 3) {
            ctx.save();
            ctx.beginPath();
            shrunk.forEach((p, i) => i === 0 ? ctx.moveTo(this.tx(p[0]), this.ty(p[1])) : ctx.lineTo(this.tx(p[0]), this.ty(p[1])));
            ctx.closePath();
            ctx.fillStyle = 'rgba(34, 197, 94, 0.12)';
            ctx.fill();

            if (tr_val > 0) {
                ctx.globalCompositeOperation = 'destination-out';
                ctx.beginPath();
                ctx.arc(this.tx(tx_val), this.ty(ty_val), tr_val * this.scale, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.restore();

            ctx.beginPath();
            shrunk.forEach((p, i) => i === 0 ? ctx.moveTo(this.tx(p[0]), this.ty(p[1])) : ctx.lineTo(this.tx(p[0]), this.ty(p[1])));
            ctx.closePath();
            ctx.strokeStyle = 'rgba(34, 197, 94, 0.8)';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Main Boundary
        ctx.beginPath();
        this.vertices.forEach((p, i) => i === 0 ? ctx.moveTo(this.tx(p[0]), this.ty(p[1])) : ctx.lineTo(this.tx(p[0]), this.ty(p[1])));
        ctx.closePath();
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Tree Protection Zone
        if (tr_val > 0) {
            ctx.beginPath();
            ctx.arc(this.tx(tx_val), this.ty(ty_val), tr_val * this.scale, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
            ctx.fill();
            ctx.strokeStyle = 'rgba(59, 130, 246, 0.6)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.fillStyle = '#3b82f6';
            ctx.font = '9px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Tree zone', this.tx(tx_val), this.ty(ty_val) + 3);
        }

        // Vertices & Labels
        this.vertices.forEach((p, i) => {
            const isHovered = (i === this.hoveredIndex || i === this.draggedIndex);
            ctx.beginPath();
            ctx.arc(this.tx(p[0]), this.ty(p[1]), isHovered ? 7 : 5, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.fill();
            ctx.strokeStyle = isHovered ? '#7c6af7' : '#ef4444';
            ctx.lineWidth = isHovered ? 3 : 2;
            ctx.stroke();

            ctx.fillStyle = '#9b9ba4';
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(`V${i}`, this.tx(p[0]), this.ty(p[1]) - 10);

            if (isHovered) {
                ctx.fillStyle = '#fff';
                ctx.fillText(`(${Math.round(p[0])}, ${Math.round(p[1])})`, this.tx(p[0]), this.ty(p[1]) - 22);
            }
        });
    }
}

// Global Sync Functions
function syncEditorToUiControls() {
    if(!window.editor) return;
    document.getElementById('jsonCoords').value = JSON.stringify(window.editor.vertices);
    renderVerticesTable();
    updateMetrics();
}

function updateMetrics() {
    if(!window.editor) return;
    const pts = window.editor.vertices;
    const lotArea = getPolygonArea(pts);
    const shrunk = computeSetbackPolygon(pts, window.editor.setback_h, window.editor.setback_v);

    const tx = parseFloat(document.getElementById('treeX').value) || 0;
    const ty = parseFloat(document.getElementById('treeY').value) || 0;
    const tr = parseFloat(document.getElementById('treeRadius').value) || 0;

    const footprintArea = getBuildableArea(shrunk, tx, ty, tr);
    const coverage = lotArea > 0 ? (footprintArea / lotArea) * 100 : 0;

    document.getElementById('valLotArea').innerText = Math.round(lotArea).toLocaleString();
    document.getElementById('valFootprintArea').innerText = Math.round(footprintArea).toLocaleString();
    document.getElementById('valCoverage').innerText = Math.round(coverage) + '%';
}

function renderVerticesTable() {
    const tbody = document.getElementById('vertexTableBody');
    tbody.innerHTML = '';
    window.editor.vertices.forEach((v, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="px-3 py-2 text-zinc-400 font-medium">V${i}</td>
            <td class="px-3 py-2"><input type="number" data-idx="${i}" data-axis="0" value="${v[0]}" class="v-input w-14 bg-[#0e0e10] border border-[#2e2e33] rounded px-1.5 py-1 text-zinc-200 outline-none focus:border-indigo-500"></td>
            <td class="px-3 py-2"><input type="number" data-idx="${i}" data-axis="1" value="${v[1]}" class="v-input w-14 bg-[#0e0e10] border border-[#2e2e33] rounded px-1.5 py-1 text-zinc-200 outline-none focus:border-indigo-500"></td>
            <td class="px-3 py-2 text-center"><button data-idx="${i}" class="v-delete text-red-400 hover:text-red-300 font-bold bg-red-500/10 hover:bg-red-500/20 px-2 py-0.5 rounded transition-colors">✕</button></td>
        `;
        tbody.appendChild(tr);
    });

    document.querySelectorAll('.v-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            const axis = parseInt(e.target.dataset.axis);
            window.editor.vertices[idx][axis] = parseFloat(e.target.value) || 0;
            window.editor.draw();
            syncEditorToUiControls();
        });
    });

    document.querySelectorAll('.v-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if(window.editor.vertices.length <= 3) return alert("Minimum 3 vertices required.");
            window.editor.vertices.splice(parseInt(e.target.dataset.idx), 1);
            window.editor.draw();
            syncEditorToUiControls();
        });
    });
    const btnTopology = document.getElementById('btnViewTopology');
    if (btnTopology) {
        btnTopology.addEventListener('click', () => {
            alert("Topology will be visible when the topology agent is connected.");
        });
    }
}

// Initializer
document.addEventListener('DOMContentLoaded', () => {

    // 1. Initialize Canvas Editor
    window.editor = new PlotEditor('plotCanvas');
    window.addEventListener('resize', () => window.editor.resize());
    window.editor.onChangeCallback = syncEditorToUiControls;

    syncEditorToUiControls();

    // UI Tools Setup
    document.getElementById('btnShapeRect').addEventListener('click', () => {
        window.editor.vertices = [[20, 20], [80, 20], [80, 80], [20, 80]];
        window.editor.draw(); syncEditorToUiControls();
    });

    document.getElementById('btnShapeL').addEventListener('click', () => {
        window.editor.vertices = [[10, 10], [50, 10], [50, 45], [80, 45], [80, 80], [10, 80]];
        window.editor.draw(); syncEditorToUiControls();
    });

    document.getElementById('btnClearAll').addEventListener('click', () => {
        window.editor.vertices = [[20, 20], [80, 20], [80, 80]];
        window.editor.draw(); syncEditorToUiControls();
    });

    document.getElementById('btnAddVertex').addEventListener('click', () => {
        const v = window.editor.vertices;
        if(v.length >= 3) {
            v.push([Math.round((v[v.length-1][0] + v[0][0]) / 2), Math.round((v[v.length-1][1] + v[0][1]) / 2)]);
            window.editor.draw(); syncEditorToUiControls();
        }
    });

    document.getElementById('snapGridToggle').addEventListener('change', (e) => {
        window.editor.snapToGrid = e.target.checked;
    });

    // Link Tree Inputs to Canvas Redraw
    ['treeX', 'treeY', 'treeRadius'].forEach(id => {
        document.getElementById(id).addEventListener('input', () => {
            window.editor.draw();
            updateMetrics();
        });
    });

    // 2. Initialize Setbacks Logic
    const regionSelect = document.getElementById('regionSelect');
    const updateWidgets = async (city) => {
        try {
            const res = await fetch(`/api/setbacks/${city}`);
            const data = await res.json();

            document.getElementById('setbackWidgets').innerHTML = `
                <div class="bg-[#18181b] border border-[#2e2e33] p-2.5 rounded-lg flex flex-col">
                    <span class="text-[10px] text-zinc-500 uppercase tracking-wider">Front Setback</span>
                    <span class="text-lg font-semibold text-indigo-400">${data.front} ft</span>
                </div>
                <div class="bg-[#18181b] border border-[#2e2e33] p-2.5 rounded-lg flex flex-col">
                    <span class="text-[10px] text-zinc-500 uppercase tracking-wider">Rear Setback</span>
                    <span class="text-lg font-semibold text-indigo-400">${data.rear} ft</span>
                </div>
                <div class="bg-[#18181b] border border-[#2e2e33] p-2.5 rounded-lg flex flex-col">
                    <span class="text-[10px] text-zinc-500 uppercase tracking-wider">Side Setback</span>
                    <span class="text-lg font-semibold text-indigo-400">${data.side} ft</span>
                </div>
                <div class="bg-[#18181b] border border-[#2e2e33] p-2.5 rounded-lg flex flex-col">
                    <span class="text-[10px] text-zinc-500 uppercase tracking-wider">Max Height</span>
                    <span class="text-lg font-semibold text-indigo-400">${data.max_height} ft</span>
                </div>
            `;

            if(window.editor) {
                window.editor.setback_v = data.front;
                window.editor.setback_h = data.side;
                window.editor.draw();
                updateMetrics();
            }
        } catch (error) { console.error("Failed to load setbacks", error); }
    };
    regionSelect.addEventListener('change', (e) => updateWidgets(e.target.value));
    updateWidgets(regionSelect.value);

    // 3. Initialize Chat Agent
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatBox = document.getElementById('chatBox');
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        const usrDiv = document.createElement('div');
        usrDiv.className = "self-end bg-indigo-600 text-white px-3 py-2 rounded-lg max-w-[90%]";
        usrDiv.textContent = text;
        chatBox.appendChild(usrDiv);
        chatInput.value = '';
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const res = await fetch('/api/planning/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            setTimeout(() => {
                const agtDiv = document.createElement('div');
                agtDiv.className = "self-start bg-[#2e2e33] text-zinc-100 px-3 py-2 rounded-lg max-w-[90%]";
                agtDiv.textContent = data.reply;
                chatBox.appendChild(agtDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            }, 600);
        } catch (e) {}
    });

    // 4. Modal Submission Logic
    const popup = document.getElementById('dummyPopup');
    const popupContent = document.getElementById('popupContent');

    document.getElementById('btnValidate').addEventListener('click', () => {
        popup.classList.add('modal-active');
        // Slight delay to trigger CSS transition
        setTimeout(() => popupContent.classList.add('modal-enter'), 10);
    });

    document.getElementById('btnClosePopup').addEventListener('click', () => {
        popupContent.classList.remove('modal-enter');
        setTimeout(() => popup.classList.remove('modal-active'), 300);
    });
});