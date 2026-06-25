import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { ScrollState } from '../scroll/useScrollProgress';
import { smoothstep } from '../scroll/useScrollProgress';

interface RepositoryGraphProps {
  scrollState: ScrollState;
}

// Node type definitions for the knowledge graph
type NodeType = 'module' | 'service' | 'function' | 'api' | 'database';

interface GraphNode {
  position: THREE.Vector3;
  type: NodeType;
  cluster: number;
  layerY: number; // Y position when reorganized into architecture layers
}

const NODE_COLORS: Record<NodeType, THREE.Color> = {
  module:   new THREE.Color('#6ee7c0'),
  service:  new THREE.Color('#7da8ff'),
  function: new THREE.Color('#e0e4ea'),
  api:      new THREE.Color('#f2d06b'),
  database: new THREE.Color('#c084fc'),
};

const NODE_COUNT = 180;
const EDGE_COUNT = 280;

/**
 * Generate pre-computed graph node positions using organic clustering.
 */
function generateGraphNodes(): GraphNode[] {
  const nodes: GraphNode[] = [];
  const types: NodeType[] = ['module', 'service', 'function', 'api', 'database'];
  const clusterCount = 6;

  // Generate cluster centers
  const clusterCenters: THREE.Vector3[] = [];
  for (let c = 0; c < clusterCount; c++) {
    const angle = (c / clusterCount) * Math.PI * 2;
    const r = 3.5 + Math.random() * 1.5;
    clusterCenters.push(new THREE.Vector3(
      Math.cos(angle) * r,
      (Math.random() - 0.5) * 3,
      Math.sin(angle) * r
    ));
  }

  for (let i = 0; i < NODE_COUNT; i++) {
    const cluster = i % clusterCount;
    const center = clusterCenters[cluster];
    const spread = 1.2 + Math.random() * 0.8;

    const pos = new THREE.Vector3(
      center.x + (Math.random() - 0.5) * spread * 2,
      center.y + (Math.random() - 0.5) * spread * 1.5,
      center.z + (Math.random() - 0.5) * spread * 2
    );

    const type = types[i % types.length];

    // Architecture layer Y positions for Scene 5
    const layerMap: Record<NodeType, number> = {
      api:      3.5,
      service:  1.5,
      function: 0,
      module:  -1.5,
      database: -3.5,
    };

    nodes.push({
      position: pos,
      type,
      cluster,
      layerY: layerMap[type] + (Math.random() - 0.5) * 0.5,
    });
  }

  return nodes;
}

/**
 * Generate edges between nodes (connection pairs).
 */
function generateEdges(nodes: GraphNode[]): [number, number][] {
  const edges: [number, number][] = [];
  const used = new Set<string>();

  // Intra-cluster connections
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (edges.length >= EDGE_COUNT) break;
      const key = `${i}-${j}`;
      if (used.has(key)) continue;

      const dist = nodes[i].position.distanceTo(nodes[j].position);
      const sameCluster = nodes[i].cluster === nodes[j].cluster;

      if (sameCluster && dist < 2.5 && Math.random() > 0.4) {
        edges.push([i, j]);
        used.add(key);
      } else if (!sameCluster && dist < 4.5 && Math.random() > 0.85) {
        edges.push([i, j]);
        used.add(key);
      }
    }
  }

  return edges;
}

/**
 * Scenes 2-5 — The Repository Knowledge Graph.
 *
 * Scene 2: Nodes emerge from center (monolith position), expand outward
 * Scene 3: Edges connect, clusters form, metrics appear
 * Scene 4: Highlight node, ripple propagation
 * Scene 5: Reorganize into architecture layers
 */
export function RepositoryGraph({ scrollState }: RepositoryGraphProps) {
  const instancedRef = useRef<THREE.InstancedMesh>(null);
  const edgesRef = useRef<THREE.LineSegments>(null);
  const rippleRef = useRef<THREE.Mesh>(null);

  const { graphNodes, edges } = useMemo(() => {
    const graphNodes = generateGraphNodes();
    const edges = generateEdges(graphNodes);
    return { graphNodes, edges };
  }, []);

  // Temporary objects for instanced mesh updates
  const tempObject = useMemo(() => new THREE.Object3D(), []);
  const tempColor = useMemo(() => new THREE.Color(), []);

  const scene2 = scrollState.sceneProgressArray[1]; // Awakening
  const scene3 = scrollState.sceneProgressArray[2]; // Universe
  const scene4 = scrollState.sceneProgressArray[3]; // Impact
  const scene5 = scrollState.sceneProgressArray[4]; // Architecture
  const scene6 = scrollState.sceneProgressArray[5]; // Intelligence Core

  // Visibility: appear in scene 2, gone in scene 6+
  const graphVisible = scene2 > 0.01 && scene6 < 0.95;
  const collapseProgress = smoothstep(0, 0.8, scene6);

  // Edge line positions
  const edgePositions = useMemo(() => {
    return new Float32Array(edges.length * 6);
  }, [edges]);

  useFrame(() => {
    if (!instancedRef.current || !graphVisible) return;

    const emerge = smoothstep(0, 0.8, scene2);
    const connect = smoothstep(0, 0.6, scene3);
    const reorganize = smoothstep(0, 0.7, scene5);
    const collapse = collapseProgress;

    for (let i = 0; i < NODE_COUNT; i++) {
      const node = graphNodes[i];
      const baseColor = NODE_COLORS[node.type];

      // Emerge: nodes expand from center
      const emergeScale = smoothstep(0, 1, emerge - (i / NODE_COUNT) * 0.3);

      // Target position: original organic position or architecture-reorganized
      let tx = node.position.x;
      let ty = node.position.y;
      let tz = node.position.z;

      // Scene 5: reorganize into horizontal architecture layers
      if (reorganize > 0) {
        const layerX = node.position.x * 0.8;
        const layerZ = node.position.z * 0.4;
        tx = THREE.MathUtils.lerp(tx, layerX, reorganize);
        ty = THREE.MathUtils.lerp(ty, node.layerY, reorganize);
        tz = THREE.MathUtils.lerp(tz, layerZ, reorganize);
      }

      // Scene 6: collapse inward toward center
      if (collapse > 0) {
        tx = THREE.MathUtils.lerp(tx, 0, collapse);
        ty = THREE.MathUtils.lerp(ty, 0, collapse);
        tz = THREE.MathUtils.lerp(tz, 0, collapse);
      }

      // Apply emerge transition (from center outward)
      const x = tx * emergeScale;
      const y = ty * emergeScale;
      const z = tz * emergeScale;

      const nodeScale = emergeScale * 0.06 * (1 - collapse * 0.7);

      tempObject.position.set(x, y, z);
      tempObject.scale.setScalar(nodeScale);
      tempObject.updateMatrix();
      instancedRef.current.setMatrixAt(i, tempObject.matrix);

      // Color: highlight some nodes in scene 4 (impact)
      if (scene4 > 0.1 && i % 7 === 0) {
        const impactIntensity = smoothstep(0, 0.5, scene4 - (i / NODE_COUNT) * 0.4);
        tempColor.copy(baseColor).lerp(new THREE.Color('#ff6b5a'), impactIntensity * 0.7);
      } else if (reorganize > 0 && node.type === 'database' && node.cluster % 3 === 0) {
        // Scene 5: highlight violations
        tempColor.copy(baseColor).lerp(new THREE.Color('#ff6b5a'), reorganize * 0.6);
      } else {
        tempColor.copy(baseColor);
      }
      instancedRef.current.setColorAt(i, tempColor);
    }

    instancedRef.current.instanceMatrix.needsUpdate = true;
    if (instancedRef.current.instanceColor) {
      instancedRef.current.instanceColor.needsUpdate = true;
    }

    // Update edges
    if (edgesRef.current && connect > 0) {
      const edgePosArr = edgesRef.current.geometry.getAttribute('position') as THREE.BufferAttribute;
      const arr = edgePosArr.array as Float32Array;

      for (let e = 0; e < edges.length; e++) {
        const [a, b] = edges[e];
        const nA = graphNodes[a];
        const nB = graphNodes[b];

        const edgeEmerge = smoothstep(0, 1, connect - (e / edges.length) * 0.5);

        // Get current positions (using same logic as nodes)
        let ax = nA.position.x, ay = nA.position.y, az = nA.position.z;
        let bx = nB.position.x, by = nB.position.y, bz = nB.position.z;

        if (reorganize > 0) {
          ax = THREE.MathUtils.lerp(ax, nA.position.x * 0.8, reorganize);
          ay = THREE.MathUtils.lerp(ay, nA.layerY, reorganize);
          az = THREE.MathUtils.lerp(az, nA.position.z * 0.4, reorganize);
          bx = THREE.MathUtils.lerp(bx, nB.position.x * 0.8, reorganize);
          by = THREE.MathUtils.lerp(by, nB.layerY, reorganize);
          bz = THREE.MathUtils.lerp(bz, nB.position.z * 0.4, reorganize);
        }

        if (collapse > 0) {
          ax = THREE.MathUtils.lerp(ax, 0, collapse);
          ay = THREE.MathUtils.lerp(ay, 0, collapse);
          az = THREE.MathUtils.lerp(az, 0, collapse);
          bx = THREE.MathUtils.lerp(bx, 0, collapse);
          by = THREE.MathUtils.lerp(by, 0, collapse);
          bz = THREE.MathUtils.lerp(bz, 0, collapse);
        }

        const emerge2 = smoothstep(0, 0.8, scene2);

        const e6 = e * 6;
        arr[e6]     = ax * emerge2 * edgeEmerge;
        arr[e6 + 1] = ay * emerge2 * edgeEmerge;
        arr[e6 + 2] = az * emerge2 * edgeEmerge;
        arr[e6 + 3] = bx * emerge2 * edgeEmerge;
        arr[e6 + 4] = by * emerge2 * edgeEmerge;
        arr[e6 + 5] = bz * emerge2 * edgeEmerge;
      }

      edgePosArr.needsUpdate = true;
    }

    // Impact ripple ring
    if (rippleRef.current) {
      const rippleActive = scene4 > 0.1 && scene4 < 0.95;
      rippleRef.current.visible = rippleActive;
      if (rippleActive) {
        const rippleScale = smoothstep(0.1, 0.9, scene4) * 12;
        rippleRef.current.scale.setScalar(rippleScale);
        const mat = rippleRef.current.material as THREE.MeshBasicMaterial;
        mat.opacity = (1 - smoothstep(0.5, 1, scene4)) * 0.3;
      }
    }
  });

  if (!graphVisible) return null;

  return (
    <group>
      {/* Node instances */}
      <instancedMesh
        ref={instancedRef}
        args={[undefined, undefined, NODE_COUNT]}
        frustumCulled={false}
      >
        <sphereGeometry args={[1, 12, 12]} />
        <meshStandardMaterial
          roughness={0.3}
          metalness={0.5}
          transparent
          opacity={0.9}
          toneMapped={false}
        />
      </instancedMesh>

      {/* Edges */}
      <lineSegments ref={edgesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[edgePositions, 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color="#6ee7c0"
          transparent
          opacity={0.12}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>

      {/* Impact ripple ring (Scene 4) */}
      <mesh ref={rippleRef} rotation-x={Math.PI / 2} visible={false}>
        <ringGeometry args={[0.95, 1, 64]} />
        <meshBasicMaterial
          color="#6ee7c0"
          transparent
          opacity={0.3}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}
