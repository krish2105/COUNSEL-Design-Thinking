"use client";

/* The chamber in three dimensions.
 *
 * frameloop="demand" is the important line. A boardroom table is not a game:
 * nothing moves unless a turn arrives or the replay is scrubbed, so rendering
 * sixty times a second would burn a laptop battery to display a still image.
 * The scene re-renders when invalidate() is called and at no other time.
 *
 * Abstract forms, not avatars. Five columns of light around a ring. Giving the
 * mandates faces would invite a reader to trust them as people, and their
 * expertise is prompt-defined — the interface should not add authority the
 * system does not have.
 */

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { SEATS, arcPoints, glow, seatXZ, type Seat } from "@/lib/chamber";
import type { ChamberEdge } from "./TableSVG";

const R = 3.4;

function Seat({
  seat,
  colour,
  lit,
  speaking,
  reduced,
}: {
  seat: Seat;
  colour: string;
  lit: number;
  speaking: boolean;
  reduced: boolean;
}) {
  const [x, z] = seatXZ(seat, R);
  const mesh = useRef<THREE.Mesh>(null);
  const { invalidate } = useThree();

  /* The only thing that animates, and only while a seat is actually speaking:
     a slow breath on the emissive intensity. Under reduced motion it holds at
     full instead, so the speaker is still identifiable without pulsing. */
  useFrame(({ clock }) => {
    if (!mesh.current || !speaking || reduced) return;
    const m = mesh.current.material as THREE.MeshStandardMaterial;
    m.emissiveIntensity = 1.1 + Math.sin(clock.elapsedTime * 2.2) * 0.35;
    invalidate();
  });

  const height = 0.5 + lit * 0.9;

  return (
    <group position={[x, height / 2, z]}>
      <mesh ref={mesh} castShadow>
        <cylinderGeometry args={[0.24, 0.3, height, 6]} />
        <meshStandardMaterial
          color={colour}
          emissive={colour}
          emissiveIntensity={speaking && reduced ? 1.3 : 0.15 + lit * 1.0}
          roughness={0.55}
          metalness={0.1}
        />
      </mesh>
      {lit > 0.02 ? (
        <pointLight color={colour} intensity={lit * 2.2} distance={3.2} position={[0, 0.3, 0]} />
      ) : null}
    </group>
  );
}

function Edge({ from, to, colour }: { from: Seat; to: Seat; colour: string }) {
  const geometry = useMemo(() => {
    const pts = arcPoints(from, to, R * 0.9).map(
      ([x, z], i, all) =>
        // Bowed upward as well as inward, so an edge reads as an argument
        // travelling across the table rather than a line drawn on it.
        new THREE.Vector3(x, 0.42 + Math.sin((i / (all.length - 1)) * Math.PI) * 0.5, z),
    );
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [from, to]);

  useEffect(() => () => geometry.dispose(), [geometry]);

  return (
    <primitive
      object={new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: colour, transparent: true, opacity: 0.5 }))}
    />
  );
}

function Table() {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <ringGeometry args={[R * 0.55, R * 1.12, 64]} />
        <meshStandardMaterial color="#2b2f3d" roughness={0.85} metalness={0.05} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <circleGeometry args={[R * 0.55, 48]} />
        <meshStandardMaterial color="#171a24" roughness={1} />
      </mesh>
    </group>
  );
}

export function Table3D({
  edges,
  speaking,
  lastSpokeAt,
  activeOrdinal,
  colours,
  reduced,
}: {
  edges: ChamberEdge[];
  speaking: string | null;
  lastSpokeAt: Record<string, number>;
  activeOrdinal: number;
  colours: Record<string, string>;
  reduced: boolean;
}) {
  const unique = Array.from(
    new Map(edges.map((e) => [`${e.from_seat}-${e.to_seat}`, e])).values(),
  ).filter((e) => SEATS.includes(e.from_seat as Seat) && SEATS.includes(e.to_seat as Seat));

  return (
    <Canvas
      /* Renders on demand only: a still table does not need sixty frames a second. */
      frameloop="demand"
      dpr={[1, 1.75]}
      shadows
      camera={{ position: [0, 6.4, 7.8], fov: 40 }}
      gl={{ antialias: true, powerPreference: "low-power" }}
      data-testid="table-3d"
    >
      <color attach="background" args={["#0d1018"]} />
      <CameraAim />
      <fog attach="fog" args={["#0d1018", 9, 17]} />
      <ambientLight intensity={0.22} />
      <directionalLight position={[3, 7, 4]} intensity={0.5} castShadow />

      <Table />
      {unique.map((e) => (
        <Edge
          key={`${e.from_seat}-${e.to_seat}`}
          from={e.from_seat as Seat}
          to={e.to_seat as Seat}
          colour={colours[e.from_seat] ?? "#8890a8"}
        />
      ))}
      {SEATS.map((seat) => (
        <Seat
          key={seat}
          seat={seat}
          colour={colours[seat] ?? "#8890a8"}
          lit={glow(lastSpokeAt[seat] ?? null, activeOrdinal)}
          speaking={speaking === seat}
          reduced={reduced}
        />
      ))}
      <Invalidator dep={`${speaking}-${activeOrdinal}-${unique.length}`} />
    </Canvas>
  );
}

/** Look slightly above the table centre so all five seats and the ring fit,
 *  rather than the near edge filling the frame. */
function CameraAim() {
  const { camera, invalidate } = useThree();
  useEffect(() => {
    camera.lookAt(0, 0.4, 0);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, invalidate]);
  return null;
}

/** Re-render exactly when the data changes, and never otherwise. */
function Invalidator({ dep }: { dep: string }) {
  const { invalidate } = useThree();
  useEffect(() => invalidate(), [dep, invalidate]);
  return null;
}
