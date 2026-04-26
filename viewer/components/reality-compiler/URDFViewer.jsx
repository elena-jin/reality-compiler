import { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import URDFLoader from "urdf-loader";
import { RotateCw, Download, MousePointer, Play, Pause, Scan } from "lucide-react";

// Brighter material presets for visibility against dark background
const MATERIAL_MAP = {
  black_anodized: { color: 0x3a3a40, roughness: 0.3, metalness: 0.85 },
  dark_metal: { color: 0x5a5a60, roughness: 0.25, metalness: 0.9 },
  aluminum: { color: 0xd0d0d8, roughness: 0.2, metalness: 0.92 },
  servo_blue: { color: 0x2a3a60, roughness: 0.35, metalness: 0.8 },
  green_pcb: { color: 0x1a7a3e, roughness: 0.6, metalness: 0.1 },
  rubber_black: { color: 0x2a2a2a, roughness: 0.85, metalness: 0.05 },
  carbon_fiber: { color: 0x2a2a30, roughness: 0.2, metalness: 0.7 },
  battery_blue: { color: 0x2a4070, roughness: 0.4, metalness: 0.5 },
  clear: { color: 0xb0b0b8, roughness: 0.1, metalness: 0.3 },
};

export default function URDFViewer({ urdfPath, onPartSelect }) {
  const containerRef = useRef(null);
  const rendererRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const robotRef = useRef(null);
  const pivotRef = useRef(null);
  const frameRef = useRef(null);
  const isDragging = useRef(false);
  const prevMouse = useRef({ x: 0, y: 0 });
  const rotationTarget = useRef({ x: 0.3, y: 0 });
  const autoRotate = useRef(true);
  const zoomRef = useRef(1.0);
  const modelCenterRef = useRef(new THREE.Vector3());
  const modelSizeRef = useRef(0.3);
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());
  const selectedRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [joints, setJoints] = useState([]);
  const [animating, setAnimating] = useState(false);
  const [xrayMode, setXrayMode] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const animTimeRef = useRef(0);
  const originalMaterials = useRef(new Map());

  const handleExportGLB = useCallback(async () => {
    const robot = robotRef.current;
    if (!robot) return;
    const { GLTFExporter } = await import("three/addons/exporters/GLTFExporter.js");
    const exporter = new GLTFExporter();
    exporter.parse(
      robot,
      (result) => {
        const blob = new Blob([result], { type: "application/octet-stream" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "model.glb";
        a.click();
        URL.revokeObjectURL(url);
      },
      (error) => console.error("Export failed:", error),
      { binary: true }
    );
  }, []);

  // Initialize Three.js scene once
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0c0c14);

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.001,
      50
    );
    camera.position.set(0, 0.3, 0.5);
    camera.lookAt(0, 0.12, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 2.0;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    // Stronger lighting for better visibility
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
    keyLight.position.set(1, 2, 1.5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.near = 0.01;
    keyLight.shadow.camera.far = 5;
    keyLight.shadow.camera.left = -1;
    keyLight.shadow.camera.right = 1;
    keyLight.shadow.camera.top = 1;
    keyLight.shadow.camera.bottom = -0.5;
    keyLight.shadow.bias = -0.0002;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x6366f1, 0.5);
    fillLight.position.set(-1, 0.5, -1);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0x06b6d4, 0.4);
    rimLight.position.set(0, -0.5, 2);
    scene.add(rimLight);

    const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
    backLight.position.set(0, 1, -2);
    scene.add(backLight);

    const gridHelper = new THREE.GridHelper(2, 20, 0x1a1a2e, 0x10101a);
    gridHelper.position.y = -0.002;
    gridHelper.material.opacity = 0.4;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(2, 2),
      new THREE.ShadowMaterial({ opacity: 0.15 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    floor.raycast = () => {};
    scene.add(floor);

    const pivotGroup = new THREE.Group();
    scene.add(pivotGroup);
    pivotRef.current = pivotGroup;

    sceneRef.current = scene;
    rendererRef.current = renderer;
    cameraRef.current = camera;

    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
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
      rotationTarget.current.x = Math.max(
        -Math.PI / 3,
        Math.min(Math.PI / 3, rotationTarget.current.x)
      );
      prevMouse.current = { x: e.clientX, y: e.clientY };
    };
    const handleMouseUp = (e) => {
      const wasDrag =
        dragStart &&
        (Math.abs(e.clientX - dragStart.x) > 3 ||
          Math.abs(e.clientY - dragStart.y) > 3);
      isDragging.current = false;
      dragStart = null;
      setTimeout(() => {
        autoRotate.current = true;
      }, 3000);

      if (!wasDrag && robotRef.current) {
        const rect = container.getBoundingClientRect();
        mouseRef.current.x =
          ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouseRef.current.y =
          -((e.clientY - rect.top) / rect.height) * 2 + 1;
        raycasterRef.current.setFromCamera(mouseRef.current, camera);

        const meshes = [];
        robotRef.current.traverse((child) => {
          if (child.isMesh) meshes.push(child);
        });
        const intersects = raycasterRef.current.intersectObjects(
          meshes,
          false
        );

        if (selectedRef.current && selectedRef.current.material) {
          selectedRef.current.material.emissive?.setHex(0x000000);
          if (selectedRef.current.material.emissiveIntensity !== undefined)
            selectedRef.current.material.emissiveIntensity = 0;
          selectedRef.current = null;
        }

        if (intersects.length > 0) {
          const hit = intersects[0].object;
          if (hit.material && hit.material.emissive) {
            hit.material.emissive.setHex(0x6366f1);
            hit.material.emissiveIntensity = 0.4;
          }
          selectedRef.current = hit;

          let linkName = hit.name || "Part";
          let parent = hit.parent;
          while (parent) {
            if (parent.isURDFLink) {
              linkName = parent.name;
              break;
            }
            parent = parent.parent;
          }

          setTooltip({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
            label: linkName
              .replace(/_/g, " ")
              .replace(/link$/, "")
              .trim(),
            category: parent?.isURDFLink ? "URDF Link" : "Mesh",
          });
          if (onPartSelect)
            onPartSelect({ label: linkName, category: "URDF Link" });
        } else {
          setTooltip(null);
          if (onPartSelect) onPartSelect(null);
        }
      }
    };
    const handleWheel = (e) => {
      zoomRef.current = Math.max(
        0.3,
        Math.min(3.0, zoomRef.current + e.deltaY * 0.001)
      );
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
      pivotGroup.rotation.y +=
        (rotationTarget.current.y - pivotGroup.rotation.y) * 0.08;
      pivotGroup.rotation.x +=
        (rotationTarget.current.x - pivotGroup.rotation.x) * 0.08;

      // Camera positioning based on model bounds
      const dist = modelSizeRef.current * zoomRef.current * 2.5;
      const center = modelCenterRef.current;
      camera.position.set(0, center.y + dist * 0.5, dist);
      camera.lookAt(0, center.y, 0);

      if (animating && robotRef.current) {
        animTimeRef.current += 0.02;
        const robot = robotRef.current;
        const t = animTimeRef.current;
        if (robot.joints) {
          const jointNames = Object.keys(robot.joints);
          jointNames.forEach((name, i) => {
            const joint = robot.joints[name];
            if (
              joint.jointType === "revolute" ||
              joint.jointType === "continuous"
            ) {
              const lo = joint.limit?.lower ?? -Math.PI;
              const hi = joint.limit?.upper ?? Math.PI;
              const mid = (lo + hi) / 2;
              const amp = (hi - lo) / 2;
              try {
                joint.setJointValue(mid + amp * Math.sin(t + i * 0.7));
              } catch (e) {
                /* ignore joint errors */
              }
            }
          });
        }
      }

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

  // Load URDF model when path changes
  useEffect(() => {
    if (!urdfPath || !sceneRef.current || !pivotRef.current) return;

    const pivotGroup = pivotRef.current;

    // Clean up previous model
    if (robotRef.current) {
      pivotGroup.remove(robotRef.current);
      robotRef.current = null;
    }

    // Reset state for new model
    setAnimating(false);
    setXrayMode(false);
    setJoints([]);
    setTooltip(null);
    setLoadError(null);
    animTimeRef.current = 0;
    originalMaterials.current.clear();
    if (selectedRef.current) {
      selectedRef.current = null;
    }

    const API_BASE = import.meta.env.VITE_API_URL || "";

    const loader = new URDFLoader();
    loader.packages = "";
    loader.workingPath =
      API_BASE + urdfPath.substring(0, urdfPath.lastIndexOf("/") + 1);

    const manager = new THREE.LoadingManager();

    // Auto-frame the model once all meshes are loaded
    manager.onLoad = () => {
      const robot = robotRef.current;
      if (!robot) return;

      // Apply materials after all meshes are loaded
      robot.traverse((child) => {
        if (child.isMesh && child.material) {
          let parent = child.parent;
          while (parent) {
            if (parent.isURDFLink) {
              const linkName = parent.name;
              const matName = getMatForLink(linkName);
              if (matName && MATERIAL_MAP[matName]) {
                const preset = MATERIAL_MAP[matName];
                child.material = new THREE.MeshPhysicalMaterial({
                  color: preset.color,
                  roughness: preset.roughness,
                  metalness: preset.metalness,
                  clearcoat: preset.metalness > 0.5 ? 0.3 : 0,
                  clearcoatRoughness: 0.4,
                  envMapIntensity: 1.5,
                });
              }
              break;
            }
            parent = parent.parent;
          }
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });

      // Compute bounding box now that meshes are loaded
      const box = new THREE.Box3().setFromObject(robot);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z) || 0.3;

      // Center the robot in the scene
      robot.position.set(-center.x, -center.y + maxDim * 0.5, -center.z);

      modelCenterRef.current.set(0, maxDim * 0.5, 0);
      modelSizeRef.current = maxDim;
      zoomRef.current = 1.0;
    };

    loader.manager = manager;

    loader.loadMeshCb = (path, _manager, done) => {
      const fullPath = path.startsWith("http")
        ? path
        : API_BASE + "/" + path.replace(/^\/+/, "");

      const stlLoader = new THREE.FileLoader(manager);
      stlLoader.setResponseType("arraybuffer");
      stlLoader.load(
        fullPath,
        (data) => {
          try {
            const geometry = parseSTL(data);
            geometry.computeVertexNormals();
            const mesh = new THREE.Mesh(
              geometry,
              new THREE.MeshPhysicalMaterial({
                color: 0x8888aa,
                roughness: 0.3,
                metalness: 0.7,
                clearcoat: 0.2,
                clearcoatRoughness: 0.4,
                envMapIntensity: 1.5,
              })
            );
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            done(mesh);
          } catch (err) {
            console.error("STL parse error:", fullPath, err);
            const fallback = new THREE.Mesh(
              new THREE.BoxGeometry(0.02, 0.02, 0.02),
              new THREE.MeshStandardMaterial({ color: 0xff4444, wireframe: true })
            );
            done(fallback);
          }
        },
        undefined,
        (err) => {
          console.error("Failed to load mesh:", fullPath, err);
          const fallback = new THREE.Mesh(
            new THREE.BoxGeometry(0.02, 0.02, 0.02),
            new THREE.MeshStandardMaterial({ color: 0xff4444, wireframe: true })
          );
          done(fallback);
        }
      );
    };

    const urdfURL = API_BASE + urdfPath;
    fetch(urdfURL)
      .then((r) => {
        if (!r.ok) throw new Error(`URDF fetch failed: ${r.status}`);
        return r.text();
      })
      .then((urdfContent) => {
        let robot;
        try {
          robot = loader.parse(urdfContent);
        } catch (err) {
          console.error("URDF parse error:", err);
          setLoadError("Failed to parse URDF model");
          return;
        }

        // Add robot to scene; materials and framing applied in manager.onLoad
        pivotGroup.add(robot);
        robotRef.current = robot;

        // Build joint list
        const jointList = [];
        if (robot.joints) {
          for (const [name, joint] of Object.entries(robot.joints)) {
            if (
              joint.jointType === "revolute" ||
              joint.jointType === "continuous" ||
              joint.jointType === "prismatic"
            ) {
              jointList.push({
                name,
                type: joint.jointType,
                min: joint.limit?.lower ?? -Math.PI,
                max: joint.limit?.upper ?? Math.PI,
                value: 0,
              });
            }
          }
        }
        setJoints(jointList);
      })
      .catch((err) => {
        console.error("Failed to load URDF:", err);
        setLoadError("Failed to load 3D model");
      });
  }, [urdfPath]);

  const handleJointChange = useCallback((jointName, value) => {
    const robot = robotRef.current;
    if (!robot || !robot.joints || !robot.joints[jointName]) return;
    try {
      robot.joints[jointName].setJointValue(parseFloat(value));
    } catch (e) {
      /* ignore */
    }
    setJoints((prev) =>
      prev.map((j) =>
        j.name === jointName ? { ...j, value: parseFloat(value) } : j
      )
    );
  }, []);

  const toggleAnimation = useCallback(() => {
    setAnimating((prev) => !prev);
  }, []);

  const toggleXray = useCallback(() => {
    setXrayMode((prev) => {
      const newMode = !prev;
      const robot = robotRef.current;
      if (!robot) return newMode;

      robot.traverse((child) => {
        if (child.isMesh && child.material) {
          if (newMode) {
            if (!originalMaterials.current.has(child.uuid)) {
              originalMaterials.current.set(child.uuid, child.material);
            }
            const linkName = _findLinkName(child);
            const xrayColor = _getXrayColor(linkName);
            child.material = new THREE.MeshPhysicalMaterial({
              color: xrayColor,
              transparent: true,
              opacity: 0.35,
              roughness: 0.1,
              metalness: 0.0,
              side: THREE.DoubleSide,
              depthWrite: false,
            });
          } else {
            const original = originalMaterials.current.get(child.uuid);
            if (original) {
              child.material = original;
            }
          }
        }
      });

      // Add/remove wireframe overlay
      if (newMode) {
        robot.traverse((child) => {
          if (child.isMesh && child.geometry) {
            const wireframe = new THREE.LineSegments(
              new THREE.WireframeGeometry(child.geometry),
              new THREE.LineBasicMaterial({
                color: _getXrayWireColor(_findLinkName(child)),
                opacity: 0.6,
                transparent: true,
              })
            );
            wireframe.name = "_xray_wire";
            child.add(wireframe);
          }
        });
      } else {
        const toRemove = [];
        robot.traverse((child) => {
          if (child.name === "_xray_wire") toRemove.push(child);
        });
        toRemove.forEach((w) => w.parent?.remove(w));
      }

      return newMode;
    });
  }, []);

  return (
    <div className="rc-viewer-container">
      <div className="rc-viewer-label">
        <RotateCw size={12} strokeWidth={1.5} />
        <span>URDF Robot Model</span>
      </div>
      <div className="rc-viewer-toolbar">
        <button
          className="rc-viewer-btn"
          onClick={toggleAnimation}
          title={animating ? "Pause Animation" : "Animate Joints"}
        >
          {animating ? <Pause size={14} /> : <Play size={14} />}
          <span>{animating ? "Pause" : "Animate"}</span>
        </button>
        <button
          className={`rc-viewer-btn ${xrayMode ? "rc-viewer-btn-active" : ""}`}
          onClick={toggleXray}
          title="X-Ray / Transparency Mode"
        >
          <Scan size={14} />
          <span>{xrayMode ? "Solid" : "X-Ray"}</span>
        </button>
        <button
          className="rc-viewer-btn"
          onClick={handleExportGLB}
          title="Download 3D Model (GLB)"
        >
          <Download size={14} />
          <span>Export GLB</span>
        </button>
        <div className="rc-viewer-hint">
          <MousePointer size={11} />
          <span>Click parts to inspect</span>
        </div>
      </div>
      <div ref={containerRef} className="rc-viewer-canvas" />
      {loadError && (
        <div className="rc-viewer-error">
          <span>{loadError}</span>
        </div>
      )}
      {tooltip && (
        <div
          className="rc-part-tooltip"
          style={{ left: tooltip.x + 12, top: tooltip.y - 30 }}
        >
          <span className="rc-tooltip-label">{tooltip.label}</span>
          <span className="rc-tooltip-cat">{tooltip.category}</span>
        </div>
      )}
      {joints.length > 0 && (
        <div className="rc-joint-panel">
          <div className="rc-joint-title">Joint Controls</div>
          {joints.map((j) => (
            <div key={j.name} className="rc-joint-row">
              <span className="rc-joint-name">
                {j.name.replace(/_/g, " ")}
              </span>
              <input
                type="range"
                className="rc-joint-slider"
                min={j.min}
                max={j.max}
                step={0.01}
                value={j.value}
                onChange={(e) => handleJointChange(j.name, e.target.value)}
                disabled={animating}
              />
              <span className="rc-joint-value">
                {j.type === "prismatic"
                  ? `${(j.value * 1000).toFixed(0)}mm`
                  : `${((j.value * 180) / Math.PI).toFixed(0)}°`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function getMatForLink(linkName) {
  const l = linkName.toLowerCase();
  if (l.includes("servo") || l.includes("motor")) return "servo_blue";
  if (l.includes("bracket")) return "aluminum";
  if (l.includes("arm") || l.includes("forearm") || l.includes("link"))
    return "aluminum";
  if (l.includes("wrist") && !l.includes("servo")) return "aluminum";
  if (l.includes("gripper_base") || l.includes("housing")) return "dark_metal";
  if (l.includes("gripper") || l.includes("finger") || l.includes("rubber"))
    return "rubber_black";
  if (l.includes("pcb") || l.includes("board") || l.includes("controller"))
    return "green_pcb";
  if (l.includes("prop") || l.includes("carbon")) return "carbon_fiber";
  if (l.includes("battery")) return "battery_blue";
  if (l.includes("sensor") || l.includes("camera")) return "dark_metal";
  if (l.includes("base") || l.includes("plate") || l.includes("turntable"))
    return "black_anodized";
  if (l.includes("wheel") || l.includes("caster")) return "rubber_black";
  if (l.includes("chassis")) return "dark_metal";
  return "aluminum";
}

function _findLinkName(mesh) {
  let parent = mesh.parent;
  while (parent) {
    if (parent.isURDFLink) return parent.name;
    parent = parent.parent;
  }
  return mesh.name || "part";
}

function _getXrayColor(linkName) {
  const l = linkName.toLowerCase();
  if (l.includes("servo") || l.includes("motor")) return 0xff4444;
  if (
    l.includes("bracket") ||
    l.includes("frame") ||
    l.includes("housing") ||
    l.includes("base") ||
    l.includes("chassis")
  )
    return 0x44aaff;
  if (l.includes("finger") || l.includes("gripper") || l.includes("rubber"))
    return 0x44ff88;
  if (
    l.includes("pcb") ||
    l.includes("board") ||
    l.includes("controller") ||
    l.includes("sensor")
  )
    return 0xffcc44;
  if (l.includes("arm") || l.includes("link") || l.includes("forearm"))
    return 0x8888ff;
  if (l.includes("prop") || l.includes("wheel")) return 0xcc88ff;
  if (l.includes("battery")) return 0xff8844;
  return 0x6688cc;
}

function _getXrayWireColor(linkName) {
  const l = linkName.toLowerCase();
  if (l.includes("servo") || l.includes("motor")) return 0xff6666;
  if (l.includes("pcb") || l.includes("board") || l.includes("controller"))
    return 0xffdd66;
  if (l.includes("finger") || l.includes("gripper")) return 0x66ffaa;
  return 0x88aadd;
}

function parseSTL(buffer) {
  try {
    const reader = new DataView(buffer);
    if (buffer.byteLength < 84) {
      return new THREE.BoxGeometry(0.02, 0.02, 0.02);
    }
    const faces = reader.getUint32(80, true);
    const expectedSize = 84 + faces * 50;

    if (faces > 0 && buffer.byteLength >= expectedSize) {
      const vertices = new Float32Array(faces * 9);
      const normals = new Float32Array(faces * 9);

      for (let i = 0; i < faces; i++) {
        const offset = 84 + i * 50;
        const nx = reader.getFloat32(offset, true);
        const ny = reader.getFloat32(offset + 4, true);
        const nz = reader.getFloat32(offset + 8, true);

        for (let j = 0; j < 3; j++) {
          const vOffset = offset + 12 + j * 12;
          vertices[i * 9 + j * 3] = reader.getFloat32(vOffset, true);
          vertices[i * 9 + j * 3 + 1] = reader.getFloat32(vOffset + 4, true);
          vertices[i * 9 + j * 3 + 2] = reader.getFloat32(vOffset + 8, true);

          normals[i * 9 + j * 3] = nx;
          normals[i * 9 + j * 3 + 1] = ny;
          normals[i * 9 + j * 3 + 2] = nz;
        }
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(vertices, 3)
      );
      geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
      return geometry;
    }
  } catch (e) {
    console.error("STL parse error:", e);
  }

  return new THREE.BoxGeometry(0.02, 0.02, 0.02);
}
