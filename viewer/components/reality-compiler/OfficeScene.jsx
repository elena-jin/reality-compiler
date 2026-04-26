import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

const TEAM_MEMBERS = [
  {
    name: "David Gelberg",
    role: "Founder, Unicorn Mafia",
    subtitle: "No10 Innovation Fellow | AI Builder",
    color: "#6366f1",
    position: { x: -3, y: 0, z: 1 },
    advice: "Raise the bar locally and ambition compounds. When you build in a community of elite developers, execution speed 10x's. Ship fast, get feedback, iterate — that's how you build something real.",
  },
  {
    name: "Charlie Cheesman",
    role: "Co-Founder, 60x.ai",
    subtitle: "Founded Unicorn Mafia | Ex-EY Parthenon",
    color: "#10b981",
    position: { x: 2, y: 0, z: -2 },
    advice: "Every large enterprise knows they need AI. Almost none know how to deploy it. Bridge the gap between strategy and engineering — understand how enterprise processes actually work, then automate them.",
  },
  {
    name: "Fergus McKenzie-Wilson",
    role: "Co-Founder, 60x.ai",
    subtitle: "Serial Entrepreneur | Exited Founder",
    color: "#f59e0b",
    position: { x: -1, y: 0, z: -3 },
    advice: "Pioneered Multi-Agent AI early. Start building before the market is ready — being early is better than being on time. Co-founded Hydra Drones at university and exited. Build, prove, exit, repeat.",
  },
  {
    name: "Alex Choi",
    role: "Founding Engineer, 60x.ai",
    subtitle: "Full Stack & AI | Hackathon Winner",
    color: "#06b6d4",
    position: { x: 3.5, y: 0, z: 2 },
    advice: "Be a jack of all trades — AI/ML, frontend, backend, mobile. The best founding engineers are the ones who can ship an entire product end-to-end. Win hackathons, build in public, ship relentlessly.",
  },
  {
    name: "Theo",
    role: "Core Contributor, Unicorn Mafia",
    subtitle: "Community Builder | Developer",
    color: "#ec4899",
    position: { x: 0.5, y: 0, z: 3 },
    advice: "The community is everything. Devs helping devs ship — that's the core principle. Build alongside others, share what you learn, and always contribute back to the ecosystem that helped you grow.",
  },
];

function createFurniture(scene) {
  const woodMat = new THREE.MeshPhysicalMaterial({
    color: 0x8b6914, roughness: 0.65, metalness: 0.05,
  });
  const darkWoodMat = new THREE.MeshPhysicalMaterial({
    color: 0x5c3a1e, roughness: 0.7, metalness: 0.05,
  });
  const fabricMat = new THREE.MeshPhysicalMaterial({
    color: 0x3a5a3a, roughness: 0.85, metalness: 0,
  });
  const couchMat = new THREE.MeshPhysicalMaterial({
    color: 0x4a6741, roughness: 0.8, metalness: 0,
  });
  const metalMat = new THREE.MeshPhysicalMaterial({
    color: 0x888888, roughness: 0.3, metalness: 0.8,
  });
  const whiteMat = new THREE.MeshPhysicalMaterial({
    color: 0xeeeeee, roughness: 0.5, metalness: 0.1,
  });
  const screenMat = new THREE.MeshPhysicalMaterial({
    color: 0x111111, roughness: 0.1, metalness: 0.2, emissive: 0x222244, emissiveIntensity: 0.3,
  });
  const carpetMat = new THREE.MeshPhysicalMaterial({
    color: 0x8b7355, roughness: 0.95, metalness: 0,
  });
  const brickMat = new THREE.MeshPhysicalMaterial({
    color: 0xb07050, roughness: 0.9, metalness: 0,
  });

  const deskTop = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.06, 1.0), darkWoodMat);
  deskTop.position.set(-3, 0.75, -3.5);
  deskTop.castShadow = true;
  deskTop.receiveShadow = true;
  scene.add(deskTop);

  for (let dx of [-1.1, 1.1]) {
    for (let dz of [-0.4, 0.4]) {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.75, 8), metalMat);
      leg.position.set(-3 + dx, 0.375, -3.5 + dz);
      leg.castShadow = true;
      scene.add(leg);
    }
  }

  const monitor = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.45, 0.03), screenMat);
  monitor.position.set(-3, 1.22, -3.7);
  monitor.castShadow = true;
  scene.add(monitor);

  const monitorStand = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.2, 8), metalMat);
  monitorStand.position.set(-3, 0.88, -3.65);
  scene.add(monitorStand);

  const keyboard = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.015, 0.14), new THREE.MeshPhysicalMaterial({ color: 0x333333, roughness: 0.4, metalness: 0.5 }));
  keyboard.position.set(-3, 0.79, -3.3);
  scene.add(keyboard);

  const chairSeat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.06, 0.5), fabricMat);
  chairSeat.position.set(-3, 0.45, -2.8);
  chairSeat.castShadow = true;
  scene.add(chairSeat);

  const chairBack = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.6, 0.06), fabricMat);
  chairBack.position.set(-3, 0.75, -3.03);
  chairBack.castShadow = true;
  scene.add(chairBack);

  const couchBase = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.4, 0.9), couchMat);
  couchBase.position.set(2, 0.3, -3.8);
  couchBase.castShadow = true;
  couchBase.receiveShadow = true;
  scene.add(couchBase);

  const couchBack = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.5, 0.15), couchMat);
  couchBack.position.set(2, 0.65, -4.2);
  couchBack.castShadow = true;
  scene.add(couchBack);

  for (let dx of [-0.85, 0.85]) {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.35, 0.9), couchMat);
    arm.position.set(2 + dx, 0.5, -3.8);
    arm.castShadow = true;
    scene.add(arm);
  }

  for (let i = 0; i < 3; i++) {
    const cushion = new THREE.Mesh(
      new THREE.BoxGeometry(0.6, 0.12, 0.35),
      new THREE.MeshPhysicalMaterial({ color: i === 1 ? 0x6366f1 : 0x4a6741, roughness: 0.85 })
    );
    cushion.position.set(2 + (i - 1) * 0.65, 0.56, -3.65);
    cushion.rotation.x = -0.1;
    scene.add(cushion);
  }

  const coffeeTable = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.04, 0.6), woodMat);
  coffeeTable.position.set(2, 0.35, -3.0);
  coffeeTable.castShadow = true;
  coffeeTable.receiveShadow = true;
  scene.add(coffeeTable);

  for (let dx of [-0.4, 0.4]) {
    for (let dz of [-0.25, 0.25]) {
      const tleg = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.35, 8), darkWoodMat);
      tleg.position.set(2 + dx, 0.175, -3.0 + dz);
      scene.add(tleg);
    }
  }

  const mug = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.035, 0.08, 16), whiteMat);
  mug.position.set(2.2, 0.41, -3.0);
  scene.add(mug);

  const mugHandle = new THREE.Mesh(new THREE.TorusGeometry(0.025, 0.006, 8, 16, Math.PI), whiteMat);
  mugHandle.position.set(2.24, 0.41, -3.0);
  mugHandle.rotation.y = Math.PI / 2;
  scene.add(mugHandle);

  for (let i = 0; i < 3; i++) {
    const book = new THREE.Mesh(
      new THREE.BoxGeometry(0.15, 0.03 + i * 0.008, 0.22),
      new THREE.MeshPhysicalMaterial({
        color: [0x2d3748, 0x744210, 0x1a365d][i], roughness: 0.7,
      })
    );
    book.position.set(1.7, 0.39 + i * 0.035, -3.05);
    book.rotation.y = 0.15 * (i - 1);
    scene.add(book);
  }

  const shelfGroup = new THREE.Group();
  for (let j = 0; j < 3; j++) {
    const shelf = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.03, 0.25), woodMat);
    shelf.position.set(0, 1.2 + j * 0.55, 0);
    shelf.castShadow = true;
    shelf.receiveShadow = true;
    shelfGroup.add(shelf);

    const numBooks = 4 + Math.floor(Math.random() * 4);
    let bx = -0.6;
    for (let b = 0; b < numBooks; b++) {
      const bw = 0.04 + Math.random() * 0.06;
      const bh = 0.2 + Math.random() * 0.15;
      const bookMesh = new THREE.Mesh(
        new THREE.BoxGeometry(bw, bh, 0.16),
        new THREE.MeshPhysicalMaterial({
          color: new THREE.Color().setHSL(Math.random(), 0.4 + Math.random() * 0.3, 0.3 + Math.random() * 0.2),
          roughness: 0.7,
        })
      );
      bookMesh.position.set(bx + bw / 2, 1.2 + j * 0.55 + bh / 2 + 0.015, 0);
      shelfGroup.add(bookMesh);
      bx += bw + 0.01;
    }
  }
  shelfGroup.position.set(4.5, 0, 0);
  scene.add(shelfGroup);

  const carpet = new THREE.Mesh(new THREE.PlaneGeometry(3, 2.5), carpetMat);
  carpet.rotation.x = -Math.PI / 2;
  carpet.position.set(0.5, 0.01, 0);
  carpet.receiveShadow = true;
  scene.add(carpet);

  const brickWall = new THREE.Mesh(new THREE.PlaneGeometry(12, 4), brickMat);
  brickWall.position.set(0, 2, -5);
  brickWall.receiveShadow = true;
  scene.add(brickWall);

  for (let side of [-1, 1]) {
    const wall = new THREE.Mesh(
      new THREE.PlaneGeometry(10, 4),
      new THREE.MeshPhysicalMaterial({ color: 0xf0ead6, roughness: 0.85 })
    );
    wall.rotation.y = side * Math.PI / 2;
    wall.position.set(side * 5.5, 2, 0);
    wall.receiveShadow = true;
    scene.add(wall);
  }

  const windowFrame = new THREE.Mesh(
    new THREE.BoxGeometry(2.5, 2, 0.05),
    new THREE.MeshPhysicalMaterial({
      color: 0xaaccee,
      roughness: 0.1,
      metalness: 0.1,
      transparent: true,
      opacity: 0.25,
      transmission: 0.6,
    })
  );
  windowFrame.position.set(-5.45, 2.2, -1);
  scene.add(windowFrame);

  for (let wy of [-1, 0, 1]) {
    const wBar = new THREE.Mesh(
      new THREE.BoxGeometry(2.5, 0.03, 0.06),
      new THREE.MeshPhysicalMaterial({ color: 0xdddddd, roughness: 0.3, metalness: 0.6 })
    );
    wBar.position.set(-5.43, 2.2 + wy * 0.65, -1);
    scene.add(wBar);
  }

  const plant = new THREE.Group();
  const pot = new THREE.Mesh(
    new THREE.CylinderGeometry(0.12, 0.1, 0.2, 16),
    new THREE.MeshPhysicalMaterial({ color: 0x8b4513, roughness: 0.8 })
  );
  pot.position.set(0, 0.1, 0);
  plant.add(pot);

  for (let l = 0; l < 5; l++) {
    const leaf = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 8, 8),
      new THREE.MeshPhysicalMaterial({ color: 0x228b22, roughness: 0.7 })
    );
    const angle = (l / 5) * Math.PI * 2;
    leaf.position.set(Math.cos(angle) * 0.1, 0.3 + l * 0.04, Math.sin(angle) * 0.1);
    leaf.scale.set(1, 0.5, 0.8);
    plant.add(leaf);
  }
  plant.position.set(4.5, 0, 3);
  scene.add(plant);

  const whiteboardFrame = new THREE.Mesh(
    new THREE.BoxGeometry(2.0, 1.2, 0.04),
    new THREE.MeshPhysicalMaterial({ color: 0xfafafa, roughness: 0.3, metalness: 0.1 })
  );
  whiteboardFrame.position.set(0, 2.2, -4.95);
  scene.add(whiteboardFrame);

  const wbBorder = new THREE.Mesh(
    new THREE.BoxGeometry(2.1, 1.3, 0.03),
    new THREE.MeshPhysicalMaterial({ color: 0x888888, roughness: 0.3, metalness: 0.6 })
  );
  wbBorder.position.set(0, 2.2, -4.97);
  scene.add(wbBorder);
}

function createCharacter(member, scene, characters) {
  const group = new THREE.Group();
  const col = new THREE.Color(member.color);

  const bodyGeo = new THREE.CapsuleGeometry(0.2, 0.6, 8, 16);
  const bodyMat = new THREE.MeshPhysicalMaterial({
    color: col, roughness: 0.5, metalness: 0.1, clearcoat: 0.2,
  });
  const body = new THREE.Mesh(bodyGeo, bodyMat);
  body.position.y = 0.7;
  body.castShadow = true;
  group.add(body);

  const headGeo = new THREE.SphereGeometry(0.16, 24, 24);
  const headMat = new THREE.MeshPhysicalMaterial({
    color: 0xf0d0b0, roughness: 0.6, metalness: 0,
  });
  const head = new THREE.Mesh(headGeo, headMat);
  head.position.y = 1.25;
  head.castShadow = true;
  group.add(head);

  const hairGeo = new THREE.SphereGeometry(0.14, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2);
  const hairMat = new THREE.MeshPhysicalMaterial({
    color: 0x2c1810, roughness: 0.8,
  });
  const hair = new THREE.Mesh(hairGeo, hairMat);
  hair.position.y = 1.3;
  hair.rotation.x = -0.15;
  group.add(hair);

  for (let side of [-1, 1]) {
    const armGeo = new THREE.CapsuleGeometry(0.06, 0.4, 4, 8);
    const arm = new THREE.Mesh(armGeo, bodyMat);
    arm.position.set(side * 0.3, 0.8, 0);
    arm.rotation.z = side * 0.15;
    arm.castShadow = true;
    group.add(arm);
  }

  const legMat = new THREE.MeshPhysicalMaterial({
    color: 0x2d3748, roughness: 0.7,
  });
  for (let side of [-1, 1]) {
    const legGeo = new THREE.CapsuleGeometry(0.07, 0.4, 4, 8);
    const leg = new THREE.Mesh(legGeo, legMat);
    leg.position.set(side * 0.1, 0.25, 0);
    leg.castShadow = true;
    group.add(leg);
  }

  const labelCanvas = document.createElement("canvas");
  labelCanvas.width = 256;
  labelCanvas.height = 64;
  const ctx = labelCanvas.getContext("2d");
  ctx.fillStyle = "rgba(0,0,0,0)";
  ctx.fillRect(0, 0, 256, 64);
  ctx.font = "bold 22px Inter, sans-serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.fillText(member.name, 128, 30);
  ctx.font = "14px Inter, sans-serif";
  ctx.fillStyle = member.color;
  ctx.fillText(member.role, 128, 52);

  const labelTexture = new THREE.CanvasTexture(labelCanvas);
  const labelMat = new THREE.SpriteMaterial({ map: labelTexture, transparent: true, opacity: 0.9 });
  const label = new THREE.Sprite(labelMat);
  label.position.y = 1.65;
  label.scale.set(1.5, 0.4, 1);
  group.add(label);

  group.position.set(member.position.x, member.position.y, member.position.z);
  group.userData = { member, isCharacter: true };

  body.userData = { member, isCharacter: true };
  head.userData = { member, isCharacter: true };

  scene.add(group);
  characters.push(group);
}

function createUnicornMafiaLogo(scene) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#0a0a0f";
  ctx.fillRect(0, 0, 512, 256);

  ctx.strokeStyle = "#6366f1";
  ctx.lineWidth = 2;
  ctx.strokeRect(10, 10, 492, 236);

  ctx.font = "bold 52px Inter, Arial, sans-serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.fillText("UNICORN", 256, 100);

  ctx.font = "bold 52px Inter, Arial, sans-serif";
  ctx.fillStyle = "#6366f1";
  ctx.fillText("MAFIA", 256, 160);

  ctx.font = "16px Inter, Arial, sans-serif";
  ctx.fillStyle = "#888888";
  ctx.fillText("London's Elite Developer Community", 256, 210);

  const texture = new THREE.CanvasTexture(canvas);
  const logoMat = new THREE.MeshBasicMaterial({ map: texture, transparent: true });
  const logoMesh = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.2), logoMat);
  logoMesh.position.set(0, 3.5, -4.93);
  scene.add(logoMesh);

  const neonBar = new THREE.Mesh(
    new THREE.BoxGeometry(2.6, 0.02, 0.02),
    new THREE.MeshBasicMaterial({ color: 0x6366f1 })
  );
  neonBar.position.set(0, 2.85, -4.92);
  scene.add(neonBar);

  const neonLight = new THREE.PointLight(0x6366f1, 0.5, 5);
  neonLight.position.set(0, 3.2, -4.5);
  scene.add(neonLight);
}

export default function OfficeScene() {
  const containerRef = useRef(null);
  const [hoveredMember, setHoveredMember] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1510);

    const camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(0, 3, 8);
    camera.lookAt(0, 1.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight(0xffeedd, 0.4);
    scene.add(ambient);

    const warmKey = new THREE.DirectionalLight(0xffddaa, 0.9);
    warmKey.position.set(-4, 6, 3);
    warmKey.castShadow = true;
    warmKey.shadow.mapSize.set(2048, 2048);
    warmKey.shadow.bias = -0.0001;
    scene.add(warmKey);

    const coolFill = new THREE.DirectionalLight(0xaaccff, 0.3);
    coolFill.position.set(4, 4, -2);
    scene.add(coolFill);

    const windowLight = new THREE.SpotLight(0xffeedd, 0.8, 15, Math.PI / 4, 0.5);
    windowLight.position.set(-5, 4, -1);
    windowLight.target.position.set(0, 0, 0);
    windowLight.castShadow = true;
    scene.add(windowLight);
    scene.add(windowLight.target);

    const deskLamp = new THREE.PointLight(0xffcc88, 0.6, 4);
    deskLamp.position.set(-3, 1.2, -3.2);
    deskLamp.castShadow = true;
    scene.add(deskLamp);

    const accentLight = new THREE.PointLight(0x6366f1, 0.3, 8);
    accentLight.position.set(0, 3, -4);
    scene.add(accentLight);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(12, 10),
      new THREE.MeshPhysicalMaterial({
        color: 0x3a2a1a, roughness: 0.75, metalness: 0.05,
      })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    const ceiling = new THREE.Mesh(
      new THREE.PlaneGeometry(12, 10),
      new THREE.MeshPhysicalMaterial({ color: 0xf5f0e8, roughness: 0.9 })
    );
    ceiling.rotation.x = Math.PI / 2;
    ceiling.position.y = 4;
    scene.add(ceiling);

    createFurniture(scene);
    createUnicornMafiaLogo(scene);

    const characters = [];
    TEAM_MEMBERS.forEach((member) => createCharacter(member, scene, characters));

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const rotTarget = { x: 0.3, y: 0 };
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };
    let dragStart = null;

    const handleMouseDown = (e) => {
      isDragging = true;
      prevMouse = { x: e.clientX, y: e.clientY };
      dragStart = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      let foundMember = null;
      for (const charGroup of characters) {
        const meshes = charGroup.children.filter((c) => c.isMesh);
        const intersects = raycaster.intersectObjects(meshes, false);
        if (intersects.length > 0) {
          foundMember = charGroup.userData.member;
          break;
        }
      }

      if (foundMember) {
        setHoveredMember(foundMember);
        setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
        container.style.cursor = "pointer";
      } else {
        setHoveredMember(null);
        container.style.cursor = isDragging ? "grabbing" : "grab";
      }

      if (isDragging) {
        const dx = e.clientX - prevMouse.x;
        const dy = e.clientY - prevMouse.y;
        rotTarget.y += dx * 0.004;
        rotTarget.x += dy * 0.004;
        rotTarget.x = Math.max(-0.5, Math.min(0.8, rotTarget.x));
        prevMouse = { x: e.clientX, y: e.clientY };
      }
    };

    const handleMouseUp = () => {
      isDragging = false;
      dragStart = null;
      container.style.cursor = "grab";
    };

    const handleWheel = (e) => {
      camera.position.z = Math.max(3, Math.min(15, camera.position.z + e.deltaY * 0.008));
    };

    container.addEventListener("mousedown", handleMouseDown);
    container.addEventListener("mousemove", handleMouseMove);
    container.addEventListener("mouseup", handleMouseUp);
    container.addEventListener("wheel", handleWheel, { passive: true });

    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    let frame;
    const pivotPoint = new THREE.Vector3(0, 1.5, 0);
    const animate = () => {
      frame = requestAnimationFrame(animate);
      const radius = camera.position.distanceTo(pivotPoint);
      const targetTheta = rotTarget.y;
      const targetPhi = rotTarget.x;
      camera.position.x = pivotPoint.x + radius * Math.sin(targetTheta) * Math.cos(targetPhi);
      camera.position.y = pivotPoint.y + radius * Math.sin(targetPhi);
      camera.position.z = pivotPoint.z + radius * Math.cos(targetTheta) * Math.cos(targetPhi);
      camera.lookAt(pivotPoint);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", handleResize);
      container.removeEventListener("mousedown", handleMouseDown);
      container.removeEventListener("mousemove", handleMouseMove);
      container.removeEventListener("mouseup", handleMouseUp);
      container.removeEventListener("wheel", handleWheel);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className="rc-office-scene">
      <div ref={containerRef} className="rc-office-canvas" />
      {hoveredMember && (
        <div
          className="rc-member-tooltip"
          style={{
            left: Math.min(tooltipPos.x + 16, window.innerWidth - 360),
            top: tooltipPos.y - 20,
          }}
        >
          <div className="rc-member-name" style={{ color: hoveredMember.color }}>
            {hoveredMember.name}
          </div>
          <div className="rc-member-role">{hoveredMember.role}</div>
          <div className="rc-member-subtitle">{hoveredMember.subtitle}</div>
          <div className="rc-member-advice">
            <span className="rc-advice-label">Advice:</span>
            <p>{hoveredMember.advice}</p>
          </div>
        </div>
      )}
      <div className="rc-office-info">
        <span>Unicorn Mafia HQ — London</span>
        <span className="rc-office-hint">Drag to look around · Scroll to zoom · Hover characters for advice</span>
      </div>
    </div>
  );
}
