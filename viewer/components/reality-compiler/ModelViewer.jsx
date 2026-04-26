import { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { RotateCw, Download, MousePointer } from "lucide-react";

const CATEGORY_MATERIALS = {
  electronics: { color: "#1a472a", roughness: 0.6, metalness: 0.1, detail: "pcb" },
  motor: { color: "#8a8a8a", roughness: 0.25, metalness: 0.85 },
  structural: { color: "#e8e0d0", roughness: 0.7, metalness: 0.0, detail: "printed" },
  fastener: { color: "#c0c0c0", roughness: 0.2, metalness: 0.9 },
  sensor: { color: "#2d3748", roughness: 0.4, metalness: 0.3, detail: "sensor" },
  wire: { color: "#cc3333", roughness: 0.6, metalness: 0.3 },
  tube: { color: "#d4d4d8", roughness: 0.5, metalness: 0.0, transparent: true, opacity: 0.6 },
  default: { color: "#6366f1", roughness: 0.35, metalness: 0.15 },
};

function inferCategory(label) {
  if (!label) return "default";
  const l = label.toLowerCase();
  if (/servo|motor|actuator|stepper/.test(l)) return "motor";
  if (/arduino|pcb|board|nano|controller|mosfet|resistor|capacitor/.test(l)) return "electronics";
  if (/screw|bolt|nut|washer|fastener|insert/.test(l)) return "fastener";
  if (/sensor|moisture|capacitive/.test(l)) return "sensor";
  if (/wire|cable|jumper/.test(l)) return "wire";
  if (/tube|tubing|silicone|hose/.test(l)) return "tube";
  if (/printed|3d|pla|petg|enclosure|housing|base|plate|body|tray|pot|finger|grip|frame|bin|shade|stand/.test(l)) return "structural";
  return "default";
}

function createDetailedGeometry(shape, prim) {
  const cat = inferCategory(prim.label);
  switch (shape) {
    case "box": {
      const g = new THREE.BoxGeometry(1, 1, 1, 2, 2, 2);
      if (cat === "electronics") {
        const bevel = new THREE.BoxGeometry(1, 0.08, 1);
        return g;
      }
      return g;
    }
    case "cylinder": {
      const segments = cat === "motor" ? 48 : 32;
      return new THREE.CylinderGeometry(0.5, 0.5, 1, segments);
    }
    case "sphere":
      return new THREE.SphereGeometry(0.5, 48, 48);
    case "cone":
      return new THREE.ConeGeometry(0.5, 1, 32);
    case "torus":
      return new THREE.TorusGeometry(0.4, 0.15, 24, 64);
    default:
      return new THREE.BoxGeometry(1, 1, 1, 2, 2, 2);
  }
}

function createMaterial(prim) {
  const cat = inferCategory(prim.label);
  const preset = CATEGORY_MATERIALS[cat] || CATEGORY_MATERIALS.default;
  const baseColor = prim.color || preset.color;

  const mat = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(baseColor),
    roughness: preset.roughness,
    metalness: preset.metalness,
    clearcoat: cat === "motor" || cat === "fastener" ? 0.3 : 0,
    clearcoatRoughness: 0.4,
    transparent: true,
    opacity: 0,
    envMapIntensity: 1.2,
  });

  if (preset.transparent) {
    mat.transmission = 0.3;
    mat.thickness = 0.5;
  }

  return mat;
}

function createEdgeLines(mesh) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 30);
  const line = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.08 })
  );
  line.position.copy(mesh.position);
  line.rotation.copy(mesh.rotation);
  line.scale.copy(mesh.scale);
  line.raycast = () => {};
  return line;
}

export default function ModelViewer({ model, loading, onPartSelect }) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const groupRef = useRef(null);
  const frameRef = useRef(null);
  const isDragging = useRef(false);
  const prevMouse = useRef({ x: 0, y: 0 });
  const rotationTarget = useRef({ x: 0.3, y: 0 });
  const autoRotate = useRef(true);
  const selectedMeshRef = useRef(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());
  const [selectedPart, setSelectedPart] = useState(null);
  const [tooltip, setTooltip] = useState(null);

  const handleExportGLB = useCallback(async () => {
    const scene = sceneRef.current;
    if (!scene) return;
    const { GLTFExporter } = await import("three/addons/exporters/GLTFExporter.js");
    const exporter = new GLTFExporter();
    const group = groupRef.current;
    if (!group) return;
    exporter.parse(
      group,
      (result) => {
        const blob = new Blob([result], { type: "application/octet-stream" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "reality-compiler-model.glb";
        a.click();
        URL.revokeObjectURL(url);
      },
      (error) => console.error("Export failed:", error),
      { binary: true }
    );
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x08080c);
    scene.fog = new THREE.FogExp2(0x08080c, 0.06);

    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(0, 2.5, 6);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.4;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    const envScene = new THREE.Scene();
    const envLight1 = new THREE.DirectionalLight(0xffffff, 2);
    envLight1.position.set(1, 1, 1);
    envScene.add(envLight1);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.0);
    keyLight.position.set(5, 10, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 30;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x6366f1, 0.4);
    fillLight.position.set(-4, 3, -3);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x06b6d4, 0.3);
    rimLight.position.set(0, -2, 6);
    scene.add(rimLight);

    const bottomLight = new THREE.PointLight(0x6366f1, 0.2, 20);
    bottomLight.position.set(0, -1, 0);
    scene.add(bottomLight);

    const gridHelper = new THREE.GridHelper(12, 24, 0x1a1a2e, 0x10101a);
    gridHelper.position.y = -0.01;
    gridHelper.material.opacity = 0.5;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    const floorGeometry = new THREE.PlaneGeometry(20, 20);
    const floorMaterial = new THREE.ShadowMaterial({ opacity: 0.15 });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    floor.raycast = () => {};
    scene.add(floor);

    const group = new THREE.Group();
    scene.add(group);

    sceneRef.current = scene;
    rendererRef.current = renderer;
    cameraRef.current = camera;
    groupRef.current = group;

    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    let dragStart = null;
    const handleMouseDown = (e) => {
      isDragging.current = true;
      autoRotate.current = false;
      prevMouse.current = { x: e.clientX, y: e.clientY };
      dragStart = { x: e.clientX, y: e.clientY };
    };
    const handleMouseMove = (e) => {
      if (!isDragging.current) return;
      const dx = e.clientX - prevMouse.current.x;
      const dy = e.clientY - prevMouse.current.y;
      rotationTarget.current.y += dx * 0.005;
      rotationTarget.current.x += dy * 0.005;
      rotationTarget.current.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotationTarget.current.x));
      prevMouse.current = { x: e.clientX, y: e.clientY };
    };
    const handleMouseUp = (e) => {
      const wasDrag = dragStart && (Math.abs(e.clientX - dragStart.x) > 3 || Math.abs(e.clientY - dragStart.y) > 3);
      isDragging.current = false;
      dragStart = null;
      setTimeout(() => { autoRotate.current = true; }, 3000);

      if (!wasDrag) {
        const rect = container.getBoundingClientRect();
        mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        raycasterRef.current.setFromCamera(mouseRef.current, camera);
        const meshes = group.children.filter((c) => c.isMesh);
        const intersects = raycasterRef.current.intersectObjects(meshes, false);

        if (selectedMeshRef.current) {
          selectedMeshRef.current.material.emissive.setHex(0x000000);
          selectedMeshRef.current.material.emissiveIntensity = 0;
          selectedMeshRef.current = null;
        }

        if (intersects.length > 0) {
          const hit = intersects[0].object;
          hit.material.emissive.setHex(0x6366f1);
          hit.material.emissiveIntensity = 0.3;
          selectedMeshRef.current = hit;
          const label = hit.userData.label || "Component";
          const cat = hit.userData.category || "Part";
          setSelectedPart({ label, category: cat });
          setTooltip({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
            label,
            category: cat,
          });
          if (onPartSelect) onPartSelect({ label, category: cat });
        } else {
          setSelectedPart(null);
          setTooltip(null);
          if (onPartSelect) onPartSelect(null);
        }
      }
    };
    const handleWheel = (e) => {
      camera.position.z = Math.max(1.5, Math.min(20, camera.position.z + e.deltaY * 0.008));
    };

    container.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    container.addEventListener("wheel", handleWheel, { passive: true });

    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      if (autoRotate.current) {
        rotationTarget.current.y += 0.003;
      }
      group.rotation.y += (rotationTarget.current.y - group.rotation.y) * 0.08;
      group.rotation.x += (rotationTarget.current.x - group.rotation.x) * 0.08;
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      container.removeEventListener("mousedown", handleMouseDown);
      container.removeEventListener("wheel", handleWheel);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  useEffect(() => {
    const group = groupRef.current;
    const camera = cameraRef.current;
    if (!group || !camera) return;

    while (group.children.length > 0) {
      const child = group.children[0];
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
      group.remove(child);
    }
    setSelectedPart(null);
    setTooltip(null);

    if (!model || !model.primitives || model.primitives.length === 0) return;

    model.primitives.forEach((prim, i) => {
      const geometry = createDetailedGeometry(prim.shape || "box", prim);
      const material = createMaterial(prim);

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(prim.position?.x || 0, prim.position?.y || 0, prim.position?.z || 0);
      mesh.rotation.set(prim.rotation?.x || 0, prim.rotation?.y || 0, prim.rotation?.z || 0);
      mesh.scale.set(prim.scale?.x || 1, prim.scale?.y || 1, prim.scale?.z || 1);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.userData.label = prim.label || `Part ${i + 1}`;
      mesh.userData.category = inferCategory(prim.label);
      group.add(mesh);

      const edgeLines = createEdgeLines(mesh);
      group.add(edgeLines);

      const delay = i * 80;
      setTimeout(() => {
        const fadeIn = () => {
          if (material.opacity < 1) {
            material.opacity = Math.min(1, material.opacity + 0.04);
            requestAnimationFrame(fadeIn);
          }
        };
        fadeIn();
      }, delay);
    });

    const dist = model.camera_distance || 5;
    camera.position.set(0, dist * 0.45, dist);
    camera.lookAt(0, 0.5, 0);
    rotationTarget.current = { x: 0.3, y: 0 };
    autoRotate.current = true;
  }, [model]);

  const hasModel = model && model.primitives && model.primitives.length > 0;

  return (
    <div className="rc-viewer-container">
      <div className="rc-viewer-label">
        <RotateCw size={12} strokeWidth={1.5} />
        <span>Concept Model</span>
      </div>
      {hasModel && (
        <div className="rc-viewer-toolbar">
          <button className="rc-viewer-btn" onClick={handleExportGLB} title="Download 3D Model (GLB)">
            <Download size={14} />
            <span>Export GLB</span>
          </button>
          <div className="rc-viewer-hint">
            <MousePointer size={11} />
            <span>Click parts to inspect</span>
          </div>
        </div>
      )}
      <div ref={containerRef} className="rc-viewer-canvas" />
      {tooltip && (
        <div
          className="rc-part-tooltip"
          style={{ left: tooltip.x + 12, top: tooltip.y - 30 }}
        >
          <span className="rc-tooltip-label">{tooltip.label}</span>
          <span className="rc-tooltip-cat">{tooltip.category}</span>
        </div>
      )}
      {!hasModel && !loading && (
        <div className="rc-viewer-empty">
          <div className="rc-viewer-empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <path d="M24 4L44 16V32L24 44L4 32V16L24 4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.3" />
              <path d="M24 4L44 16L24 28L4 16L24 4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.5" />
              <path d="M24 28V44" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
            </svg>
          </div>
          <p className="rc-viewer-empty-text">
            Describe a product idea to generate a 3D concept model
          </p>
        </div>
      )}
    </div>
  );
}
