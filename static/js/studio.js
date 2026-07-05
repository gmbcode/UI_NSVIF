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

function parseDXF(text) {
    const lines = text.split(/\r?\n/).map(line => line.trim());
    let vertices = [];
    let currentX = null;
    let currentY = null;
    let isEntities = false;
    let isLwpolyline = false;
    let polylinePoints = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        
        if (line === "ENTITIES") {
            isEntities = true;
            continue;
        }
        if (line === "ENDSEC" && isEntities) {
            isEntities = false;
            break;
        }
        
        if (!isEntities) continue;

        if (line === "LWPOLYLINE") {
            if (polylinePoints.length >= 3) {
                vertices = polylinePoints;
            }
            polylinePoints = [];
            isLwpolyline = true;
            continue;
        }

        if (line === "0" && isLwpolyline) {
            if (polylinePoints.length >= 3) {
                vertices = polylinePoints;
            }
            isLwpolyline = false;
        }

        if (isLwpolyline) {
            if (line === "10" && i + 1 < lines.length) {
                currentX = parseFloat(lines[i + 1]);
            }
            if (line === "20" && i + 1 < lines.length) {
                currentY = parseFloat(lines[i + 1]);
                if (currentX !== null && !isNaN(currentX) && !isNaN(currentY)) {
                    polylinePoints.push([currentX, currentY]);
                    currentX = null;
                    currentY = null;
                }
            }
        }
    }

    if (polylinePoints.length >= 3) {
        vertices = polylinePoints;
    }

    if (vertices.length === 0) {
        let allX = [];
        let allY = [];
        for (let i = 0; i < lines.length; i++) {
            if (lines[i] === "10" && i + 1 < lines.length) {
                const val = parseFloat(lines[i + 1]);
                if (!isNaN(val)) allX.push(val);
            }
            if (lines[i] === "20" && i + 1 < lines.length) {
                const val = parseFloat(lines[i + 1]);
                if (!isNaN(val)) allY.push(val);
            }
        }
        const count = Math.min(allX.length, allY.length);
        const unique = [];
        for (let i = 0; i < count; i++) {
            const pt = [allX[i], allY[i]];
            if (unique.length === 0 || Math.abs(unique[unique.length - 1][0] - pt[0]) > 0.001 || Math.abs(unique[unique.length - 1][1] - pt[1]) > 0.001) {
                unique.push(pt);
            }
        }
        if (unique.length >= 3) {
            vertices = unique;
        }
    }

    return vertices;
}

function normalizeVertices(vertices) {
    if (vertices.length === 0) return [];
    
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    vertices.forEach(v => {
        if (v[0] < minX) minX = v[0];
        if (v[0] > maxX) maxX = v[0];
        if (v[1] < minY) minY = v[1];
        if (v[1] > maxY) maxY = v[1];
    });
    
    const dx = maxX - minX;
    const dy = maxY - minY;
    const maxSpan = Math.max(dx, dy);
    
    if (maxSpan === 0) {
        return vertices.map(() => [50, 50]);
    }
    
    const scale = 70 / maxSpan;
    const centerShiftX = 50 - (minX + dx / 2) * scale;
    const centerShiftY = 50 - (minY + dy / 2) * scale;
    
    return vertices.map(v => {
        return [
            Math.round((v[0] * scale + centerShiftX) * 10) / 10,
            Math.round((v[1] * scale + centerShiftY) * 10) / 10
        ];
    });
}

function getBuildableArea(shrunk, trees) {
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
                let inAnyTree = false;
                for (let k = 0; k < trees.length; k++) {
                    const t = trees[k];
                    if (t.r > 0 && ((x - t.x) ** 2 + (y - t.y) ** 2) < t.r * t.r) {
                        inAnyTree = true;
                        break;
                    }
                }
                if (!inAnyTree) count++;
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
        this.trees = [{ x: 75, y: 88, r: 12 }];

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

        const isLight = document.documentElement.classList.contains('light');
        const gridColor = isLight ? '#e5e7eb' : '#2d2d35';
        const gridTextColor = isLight ? '#6b7280' : '#5a5a63';
        const labelTextColor = isLight ? '#4b5563' : '#9b9ba4';
        const hoverTextColor = isLight ? '#111827' : '#ffffff';

        // Grid
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;
        for (let i = 0; i <= 100; i += 10) {
            ctx.beginPath(); ctx.moveTo(this.tx(i), this.ty(0)); ctx.lineTo(this.tx(i), this.ty(100)); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(this.tx(0), this.ty(i)); ctx.lineTo(this.tx(100), this.ty(i)); ctx.stroke();

            ctx.fillStyle = gridTextColor;
            ctx.font = '9px monospace';
            
            // X-axis labels
            ctx.textAlign = 'center';
            if(i > 0 && i < 100) ctx.fillText(i + "'", this.tx(i), this.ty(0) + 12);

            // Y-axis labels
            ctx.textAlign = 'right';
            if(i > 0 && i < 100) ctx.fillText(i + "'", this.tx(0) - 8, this.ty(i) + 3);
        }

        // Draw solid X and Y axis lines
        ctx.strokeStyle = isLight ? '#9ca3af' : '#4b5563';
        ctx.lineWidth = 2;
        ctx.beginPath();
        // Y Axis (X = 0)
        ctx.moveTo(this.tx(0), this.ty(0));
        ctx.lineTo(this.tx(0), this.ty(100));
        // X Axis (Y = 0)
        ctx.moveTo(this.tx(0), this.ty(0));
        ctx.lineTo(this.tx(100), this.ty(0));
        ctx.stroke();

        // Buildable Area (Setback Polygon)
        const shrunk = computeSetbackPolygon(this.vertices, this.setback_h, this.setback_v);

        // Main Boundary
        ctx.beginPath();
        this.vertices.forEach((p, i) => i === 0 ? ctx.moveTo(this.tx(p[0]), this.ty(p[1])) : ctx.lineTo(this.tx(p[0]), this.ty(p[1])));
        ctx.closePath();
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Tree Protection Zones
        if (this.trees && this.trees.length > 0) {
            this.trees.forEach((t, idx) => {
                if (t.r > 0) {
                    ctx.beginPath();
                    ctx.arc(this.tx(t.x), this.ty(t.y), t.r * this.scale, 0, Math.PI * 2);
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
                    ctx.fillText(`Tree ${idx + 1}`, this.tx(t.x), this.ty(t.y) + 3);
                }
            });
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

            ctx.fillStyle = labelTextColor;
            ctx.font = '10px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(`V${i}`, this.tx(p[0]), this.ty(p[1]) - 10);

            if (isHovered) {
                ctx.fillStyle = hoverTextColor;
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

    const footprintArea = getBuildableArea(shrunk, window.editor.trees || []);
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

function renderTreesList() {
    const container = document.getElementById('treeListContainer');
    if (!container) return;
    container.innerHTML = '';

    const trees = window.editor.trees || [];
    trees.forEach((t, i) => {
        const item = document.createElement('div');
        item.className = "flex gap-2 items-end border-b border-[#2e2e33]/50 pb-2 last:border-b-0";
        item.innerHTML = `
            <div class="flex-1">
                <label class="block text-[9px] text-zinc-500 mb-0.5">X (ft)</label>
                <input type="number" data-idx="${i}" data-field="x" class="tree-input w-full bg-[#18181b] border border-[#2e2e33] focus:border-indigo-500 rounded px-2 py-1 text-xs outline-none text-zinc-200" value="${t.x}">
            </div>
            <div class="flex-1">
                <label class="block text-[9px] text-zinc-500 mb-0.5">Y (ft)</label>
                <input type="number" data-idx="${i}" data-field="y" class="tree-input w-full bg-[#18181b] border border-[#2e2e33] focus:border-indigo-500 rounded px-2 py-1 text-xs outline-none text-zinc-200" value="${t.y}">
            </div>
            <div class="flex-1">
                <label class="block text-[9px] text-zinc-500 mb-0.5">Radius (ft)</label>
                <input type="number" data-idx="${i}" data-field="r" class="tree-input w-full bg-[#18181b] border border-[#2e2e33] focus:border-indigo-500 rounded px-2 py-1 text-xs outline-none text-zinc-200" value="${t.r}">
            </div>
            <button data-idx="${i}" class="tree-delete text-red-400 hover:text-red-300 font-bold bg-red-500/10 hover:bg-red-500/20 px-2.5 py-1 rounded transition-colors mb-0.5">✕</button>
        `;
        container.appendChild(item);
    });

    // Add listeners
    document.querySelectorAll('.tree-input').forEach(input => {
        input.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            const field = e.target.dataset.field;
            const val = parseFloat(e.target.value) || 0;
            window.editor.trees[idx][field] = val;
            window.editor.draw();
            updateMetrics();
        });
    });

    document.querySelectorAll('.tree-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            window.editor.trees.splice(idx, 1);
            window.editor.draw();
            renderTreesList();
            updateMetrics();
        });
    });
}
const PLANNER_BASE =
    "https://planner-agent-production-898c.up.railway.app/api/v1";

let plannerSessionId = null;
let plannerMode = "chat";
let discoveryPoller = null;
let currentDiscoveryStage = null;
let currentDiscoveryQuestion = null;

const USER_ID = "demo_user";
const CUSTOMER_ID = "demo_user";
// Initializer
document.addEventListener('DOMContentLoaded', () => {

    // 1. Initialize Canvas Editor
    window.editor = new PlotEditor('plotCanvas');
    window.addEventListener('resize', () => window.editor.resize());
    window.editor.onChangeCallback = syncEditorToUiControls;

    syncEditorToUiControls();
    renderTreesList();

    async function startPlannerSession() {
        try {
            const res = await fetch(
                `${PLANNER_BASE}/session/start`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        user_id: USER_ID,
                        customer_id: CUSTOMER_ID
                    })
                }
            );

            const data = await res.json();

            plannerSessionId = data.session_id;
            document.getElementById("plannerStatus").textContent =
                "Brief collection active";
            const chatBox = document.getElementById("chatBox");

            chatBox.innerHTML = "";

            const msg = document.createElement("div");
            msg.className =
                "self-start bg-[#2e2e33] text-zinc-100 px-3 py-2 rounded-lg max-w-[90%]";
            msg.textContent = data.message;

            chatBox.appendChild(msg);
        } catch (err) {
            console.error("Planner start failed", err);
        }
    }

    startPlannerSession();
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

    // Link Tree Add Button
    document.getElementById('btnAddTree').addEventListener('click', () => {
        if (!window.editor.trees) window.editor.trees = [];
        window.editor.trees.push({ x: 50, y: 50, r: 10 });
        window.editor.draw();
        renderTreesList();
        updateMetrics();
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

        if (!text || !plannerSessionId) return;

        const usrDiv = document.createElement('div');
        usrDiv.className =
            "self-end bg-indigo-600 text-white px-3 py-2 rounded-lg max-w-[90%]";
        usrDiv.textContent = text;

        chatBox.appendChild(usrDiv);

        chatInput.value = '';
        chatBox.scrollTop = chatBox.scrollHeight;

        try {

            if(plannerMode === "chat") {
                const res = await fetch(
                    `${PLANNER_BASE}/session/${plannerSessionId}/message`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            user_id: USER_ID,
                            customer_id: CUSTOMER_ID,
                            message: text
                        })
                    }
                );

                const data = await res.json();

                const agtDiv = document.createElement('div');

                agtDiv.className =
                    "self-start bg-[#2e2e33] text-zinc-100 px-3 py-2 rounded-lg max-w-[90%]";

                agtDiv.textContent = data.message;

                chatBox.appendChild(agtDiv);
                chatBox.scrollTop = chatBox.scrollHeight;

                if (data.type === "brief_ready") {

                    plannerMode = "discovery";

                    localStorage.setItem(
                        "plannerBrief",
                        JSON.stringify(data.brief)
                    );

                    startDiscoveryPolling();
                }
            }
            else{
                res = await fetch(
                    `${PLANNER_BASE}/session/${plannerSessionId}/discovery/answer`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            customer_id: CUSTOMER_ID,
                            stage: currentDiscoveryStage,
                            question: currentDiscoveryQuestion,
                            answer: text
                        })
                    }
                );
            }

        } catch (err) {
            console.error(err);
        }
    });

    async function pollDiscovery() {

        if (!plannerSessionId) return;

        try {

            const res = await fetch(
                `${PLANNER_BASE}/session/${plannerSessionId}/discovery`
            );

            const data = await res.json();

            if (data.done) {
                document.getElementById("plannerStatus").textContent =
                    "Design ready";

                document.getElementById("plannerIndicator")
                    .classList.remove("animate-pulse");
                clearInterval(discoveryPoller);

                const doneDiv = document.createElement('div');

                doneDiv.className =
                    "self-start bg-green-600 text-white px-3 py-2 rounded-lg max-w-[90%]";

                doneDiv.textContent =
                    "Design generation completed.";

                chatBox.appendChild(doneDiv);

                return;
            }

            if (data.user_facing_stage_message) {

                const stageDiv = document.createElement('div');

                stageDiv.className =
                    "self-start bg-blue-600/20 text-blue-300 px-3 py-2 rounded-lg max-w-[90%]";

                stageDiv.textContent =
                    data.user_facing_stage_message;

                chatBox.appendChild(stageDiv);
            }

            if (data.question) {
                currentDiscoveryStage = data.stage;
                currentDiscoveryQuestion = data.question;

                const qDiv = document.createElement('div');

                qDiv.className =
                    "self-start bg-[#2e2e33] text-zinc-100 px-3 py-2 rounded-lg max-w-[90%]";

                qDiv.textContent = data.question;

                chatBox.appendChild(qDiv);
            }

            chatBox.scrollTop = chatBox.scrollHeight;

        } catch (err) {
            console.error(err);
        }
    }

    function startDiscoveryPolling() {

        pollDiscovery();

        discoveryPoller = setInterval(
            pollDiscovery,
            5000
        );
    }

    // 4. Submission Logic
    document.getElementById('btnValidate').addEventListener('click', () => {
        window.location.href = '/iteration';
    });

    // 5. DXF File Import Logic
    const dxfInput = document.getElementById('dxfFileInput');
    if (dxfInput) {
        dxfInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = (event) => {
                const text = event.target.result;
                const rawVertices = parseDXF(text);
                if (rawVertices && rawVertices.length >= 3) {
                    const normalized = normalizeVertices(rawVertices);
                    window.editor.vertices = normalized;
                    window.editor.draw();
                    syncEditorToUiControls();
                    alert(`Successfully imported DXF plot boundary with ${normalized.length} vertices!`);
                } else {
                    alert("Could not find a valid closed polyline (boundary) in the DXF file. Ensure it contains a closed LWPOLYLINE entity.");
                }
            };
            reader.readAsText(file);
        });
    }

    // 6. Light / Dark Mode Toggle Logic (Uiverse.io by rishichawda)
    const toggleCheckbox = document.getElementById('toggle');

    if (toggleCheckbox) {
        // Sync checkbox state with current theme on load
        toggleCheckbox.checked = !document.documentElement.classList.contains('light');

        toggleCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                document.documentElement.classList.remove('light');
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                localStorage.setItem('theme', 'light');
            }
            if (window.editor) {
                window.editor.draw();
            }
        });
    }
});