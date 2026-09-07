"use client";

/* Four scenes, one table.
 *
 * Every variant draws the SAME data — five fixed seats, edges derived from the
 * transcript, glow from speaking recency — and differs only in material,
 * light and form. Sharing the geometry helpers below is what keeps that
 * honest: a variant cannot accidentally show more or less than the record.
 *
 * All four are dimensional. The failure they replace was five faceted prisms
 * on a black disc under flat light: no reflection, no shadow, no atmosphere,
 * and saturated primaries fighting a restrained palette.
 */

import { ContactShadows, MeshReflectorMaterial } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { SEATS, arcPoints, seatXZ, type Seat } from "@/lib/chamber";

export type Variant = "obsidian" | "architect" | "candlelit" | "orrery";

export const R = 3.4;

export type SceneProps = {
  edges: { from_seat: string; to_seat: string }[];
  speaking: string | null;
  lit: Record<string, number>;
  colours: Record<string, string>;
  reduced: boolean;
};

/* ── shared helpers ─────────────────────────────────────────────────────── */

function useArc(from: Seat, to: Seat, radius: number, lift: number, rise: number) {
  return useMemo(() => {
    const pts = arcPoints(from, to, radius).map(
      ([x, z], i, all) =>
        new THREE.Vector3(x, lift + Math.sin((i / (all.length - 1)) * Math.PI) * rise, z),
    );
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [from, to, radius, lift, rise]);
}

function Arc({
  from,
  to,
  colour,
  radius = R * 0.9,
  lift = 0.12,
  rise = 0.5,
  opacity = 0.55,
}: {
  from: Seat;
  to: Seat;
  colour: string;
  radius?: number;
  lift?: number;
  rise?: number;
  opacity?: number;
}) {
  const geometry = useArc(from, to, radius, lift, rise);
  const material = useMemo(
    () => new THREE.LineBasicMaterial({ color: colour, transparent: true, opacity }),
    [colour, opacity],
  );
  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);
  return <primitive object={new THREE.Line(geometry, material)} />;
}

function Arcs(props: SceneProps & { radius?: number; lift?: number; rise?: number; opacity?: number }) {
  const unique = Array.from(
    new Map(props.edges.map((e) => [`${e.from_seat}-${e.to_seat}`, e])).values(),
  ).filter((e) => SEATS.includes(e.from_seat as Seat) && SEATS.includes(e.to_seat as Seat));
  return (
    <>
      {unique.map((e) => (
        <Arc
          key={`${e.from_seat}-${e.to_seat}`}
          from={e.from_seat as Seat}
          to={e.to_seat as Seat}
          colour={props.colours[e.from_seat] ?? "#8890a8"}
          radius={props.radius}
          lift={props.lift}
          rise={props.rise}
          opacity={props.opacity}
        />
      ))}
    </>
  );
}

/** A slow breath on whoever is speaking. The only animation in any scene, and
 *  it stops entirely under reduced motion. */
function useBreath(active: boolean, reduced: boolean, apply: (v: number) => void) {
  const { invalidate } = useThree();
  useFrame(({ clock }) => {
    if (!active || reduced) return;
    apply(1 + Math.sin(clock.elapsedTime * 2.1) * 0.3);
    invalidate();
  });
}

/* ── 1. Obsidian Council ────────────────────────────────────────────────── */
/* Slender monoliths of dark glass lit from within, standing on a polished slab
 * that reflects them. The reflection is what makes it read as a place rather
 * than a diagram: the colour doubles downward and the eye gets a floor. */

function ObsidianSeat({ seat, colour, lit, speaking, reduced }: {
  seat: Seat; colour: string; lit: number; speaking: boolean; reduced: boolean;
}) {
  const [x, z] = seatXZ(seat, R);
  const mat = useRef<THREE.MeshStandardMaterial>(null);
  useBreath(speaking, reduced, (v) => {
    if (mat.current) mat.current.emissiveIntensity = 1.6 * v;
  });
  const height = 1.5 + lit * 0.9;

  return (
    <group position={[x, height / 2, z]}>
      <mesh castShadow>
        <boxGeometry args={[0.34, height, 0.34]} />
        <meshStandardMaterial
          ref={mat}
          color="#0a0c12"
          emissive={colour}
          emissiveIntensity={speaking && reduced ? 2.0 : 0.28 + lit * 1.3}
          roughness={0.12}
          metalness={0.45}
        />
      </mesh>
      {/* A cap, so a monolith reads as a solid object catching the key light
          rather than a coloured rectangle. */}
      <mesh position={[0, height / 2 + 0.02, 0]}>
        <boxGeometry args={[0.38, 0.04, 0.38]} />
        <meshStandardMaterial color="#c3cade" roughness={0.22} metalness={0.95} />
      </mesh>
      {lit > 0.03 ? (
        <pointLight color={colour} intensity={lit * 3.2} distance={4.5} position={[0, 0.2, 0]} />
      ) : null}
    </group>
  );
}

export function ObsidianScene(props: SceneProps) {
  return (
    <>
      <color attach="background" args={["#07080c"]} />
      <fog attach="fog" args={["#07080c", 10, 22]} />
      <ambientLight intensity={0.3} />
      <spotLight
        position={[0, 13, 3]}
        angle={0.95}
        penumbra={1}
        intensity={90}
        color="#cfd6ea"
        castShadow
      />
      <directionalLight position={[-6, 5, 6]} intensity={0.35} color="#7d8dc0" />

      {/* The floor the monoliths stand on. Its base colour has to be light
          enough to catch the key light: at #0b0d14 the reflector rendered as
          pure black and the monoliths read as bars floating in a void, which
          is exactly how the first two attempts failed. The reflections are the
          point of this variant, and a reflection needs something to sit on. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <circleGeometry args={[R * 1.55, 96]} />
        <MeshReflectorMaterial
          blur={[300, 100]}
          resolution={1024}
          mixBlur={0.9}
          mixStrength={28}
          roughness={0.55}
          depthScale={0.9}
          minDepthThreshold={0.3}
          maxDepthThreshold={1.2}
          color="#39405a"
          metalness={0.7}
          mirror={0}
        />
      </mesh>

      {/* Table edge and inner well, so the slab's extent reads as an object. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.006, 0]}>
        <ringGeometry args={[R * 1.5, R * 1.56, 96]} />
        <meshStandardMaterial color="#8d97b8" roughness={0.28} metalness={0.92} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
        <ringGeometry args={[R * 0.44, R * 0.48, 96]} />
        <meshStandardMaterial color="#5a6486" roughness={0.35} metalness={0.85} />
      </mesh>

      <Arcs {...props} radius={R * 0.92} lift={0.5} rise={0.85} opacity={0.6} />
      {SEATS.map((seat) => (
        <ObsidianSeat
          key={seat}
          seat={seat}
          colour={props.colours[seat] ?? "#8890a8"}
          lit={props.lit[seat] ?? 0}
          speaking={props.speaking === seat}
          reduced={props.reduced}
        />
      ))}
    </>
  );
}

/* ── 2. The Architect's Model ───────────────────────────────────────────── */
/* A scale model on a desk. Bone-white matte table, seats as machined pins,
 * soft contact shadows, near-orthographic. Quiet and made. */

function Pin({ seat, colour, lit, speaking, reduced }: {
  seat: Seat; colour: string; lit: number; speaking: boolean; reduced: boolean;
}) {
  const [x, z] = seatXZ(seat, R * 0.86);
  const head = useRef<THREE.MeshStandardMaterial>(null);
  useBreath(speaking, reduced, (v) => {
    if (head.current) head.current.emissiveIntensity = 0.9 * v;
  });
  const height = 0.9 + lit * 0.55;

  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, height / 2, 0]} castShadow>
        <cylinderGeometry args={[0.032, 0.045, height, 20]} />
        <meshStandardMaterial color="#9aa1b2" roughness={0.35} metalness={0.75} />
      </mesh>
      <mesh position={[0, height + 0.09, 0]} castShadow>
        <sphereGeometry args={[0.115, 28, 20]} />
        <meshStandardMaterial
          ref={head}
          color={colour}
          emissive={colour}
          emissiveIntensity={speaking && reduced ? 1.1 : 0.12 + lit * 0.7}
          roughness={0.42}
          metalness={0.05}
        />
      </mesh>
    </group>
  );
}

export function ArchitectScene(props: SceneProps) {
  return (
    <>
      <color attach="background" args={["#12141c"]} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 9, 5]} intensity={1.5} castShadow />
      <directionalLight position={[-5, 4, -3]} intensity={0.28} color="#aab4d0" />

      <mesh receiveShadow>
        <cylinderGeometry args={[R * 1.15, R * 1.15, 0.09, 80]} />
        <meshStandardMaterial color="#ded8c9" roughness={1} metalness={0} />
      </mesh>
      {/* A bevel at the rim: a disc with a hard edge reads as a printed circle,
          a bevelled one reads as a machined object. */}
      <mesh position={[0, 0.045, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[R * 1.15, 0.045, 10, 96]} />
        <meshStandardMaterial color="#cfc8b6" roughness={0.88} metalness={0.05} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.051, 0]}>
        <ringGeometry args={[R * 0.52, R * 0.55, 80]} />
        <meshStandardMaterial color="#b8b1a0" roughness={1} />
      </mesh>

      <ContactShadows position={[0, 0.055, 0]} opacity={0.42} scale={12} blur={2.4} far={4} />

      <Arcs {...props} radius={R * 0.86} lift={1.15} rise={0.42} opacity={0.5} />
      {SEATS.map((seat) => (
        <Pin
          key={seat}
          seat={seat}
          colour={props.colours[seat] ?? "#8890a8"}
          lit={props.lit[seat] ?? 0}
          speaking={props.speaking === seat}
          reduced={props.reduced}
        />
      ))}
    </>
  );
}

/* ── 3. The Candlelit Chamber ───────────────────────────────────────────── */
/* A dark table in an unlit room, five tapers, one per seat. The speaking seat's
 * flame stands up; the rest gutter. The most human of the four. */

function Taper({ seat, colour, lit, speaking, reduced }: {
  seat: Seat; colour: string; lit: number; speaking: boolean; reduced: boolean;
}) {
  const [x, z] = seatXZ(seat, R * 0.82);
  const flame = useRef<THREE.Mesh>(null);
  const light = useRef<THREE.PointLight>(null);
  const { invalidate } = useThree();

  useFrame(({ clock }) => {
    if (reduced || !flame.current || !light.current) return;
    // Guttering: fast small flicker, bigger when this seat is speaking.
    const t = clock.elapsedTime;
    const flicker = 1 + Math.sin(t * 11 + SEATS.indexOf(seat)) * 0.06 + Math.sin(t * 3.7) * 0.04;
    const scale = (speaking ? 1.5 : 0.8 + lit * 0.4) * flicker;
    flame.current.scale.set(scale * 0.7, scale, scale * 0.7);
    light.current.intensity = (speaking ? 5.5 : 1.1 + lit * 2.4) * flicker;
    invalidate();
  });

  const wax = 0.55 + lit * 0.25;

  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, wax / 2, 0]} castShadow>
        <cylinderGeometry args={[0.075, 0.085, wax, 20]} />
        <meshStandardMaterial color="#f4ecd8" roughness={0.78} emissive="#2a1f12" emissiveIntensity={0.35} />
      </mesh>
      <mesh ref={flame} position={[0, wax + 0.13, 0]}>
        <sphereGeometry args={[0.07, 18, 14]} />
        <meshBasicMaterial color={speaking ? "#ffd9a0" : colour} />
      </mesh>
      <pointLight
        ref={light}
        color={speaking ? "#ffc978" : colour}
        intensity={speaking ? 5.5 : 1.1 + lit * 2.4}
        distance={5.5}
        decay={2}
        position={[0, wax + 0.16, 0]}
        castShadow
      />
    </group>
  );
}

export function CandlelitScene(props: SceneProps) {
  return (
    <>
      <color attach="background" args={["#08070a"]} />
      <fog attach="fog" args={["#08070a", 7, 16]} />
      <ambientLight intensity={0.16} color="#4a3d33" />
      <directionalLight position={[0, 6, 5]} intensity={0.22} color="#8fa0c4" />

      <mesh receiveShadow>
        <cylinderGeometry args={[R * 1.18, R * 1.18, 0.12, 80]} />
        <meshStandardMaterial color="#2a1d14" roughness={0.62} metalness={0.08} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.062, 0]}>
        <ringGeometry args={[R * 0.5, R * 0.53, 80]} />
        <meshStandardMaterial color="#4a3524" roughness={0.5} metalness={0.2} />
      </mesh>

      <Arcs {...props} radius={R * 0.82} lift={0.78} rise={0.5} opacity={0.42} />
      {SEATS.map((seat) => (
        <Taper
          key={seat}
          seat={seat}
          colour={props.colours[seat] ?? "#8890a8"}
          lit={props.lit[seat] ?? 0}
          speaking={props.speaking === seat}
          reduced={props.reduced}
        />
      ))}
    </>
  );
}

/* ── 4. The Orrery ──────────────────────────────────────────────────────── */
/* The table as a precision mechanism: concentric brass rings, seats as
 * gimballed markers set into them, arcs travelling between. Scrubbing the
 * replay should feel like winding it. */

function OrreryMarker({ seat, colour, lit, speaking, reduced }: {
  seat: Seat; colour: string; lit: number; speaking: boolean; reduced: boolean;
}) {
  const [x, z] = seatXZ(seat, R * 0.98);
  const mat = useRef<THREE.MeshStandardMaterial>(null);
  useBreath(speaking, reduced, (v) => {
    if (mat.current) mat.current.emissiveIntensity = 1.5 * v;
  });

  return (
    <group position={[x, 0.34, z]}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.19, 0.028, 12, 28]} />
        <meshStandardMaterial color="#b08a4a" roughness={0.28} metalness={0.95} />
      </mesh>
      <mesh>
        <icosahedronGeometry args={[0.115, 1]} />
        <meshStandardMaterial
          ref={mat}
          color={colour}
          emissive={colour}
          emissiveIntensity={speaking && reduced ? 1.8 : 0.2 + lit * 1.1}
          roughness={0.3}
          metalness={0.4}
        />
      </mesh>
      {lit > 0.03 ? (
        <pointLight color={colour} intensity={lit * 2.4} distance={3.4} />
      ) : null}
    </group>
  );
}

function Ring({ radius, tube, colour, spin = 0, reduced }: {
  radius: number; tube: number; colour: string; spin?: number; reduced?: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const { invalidate } = useThree();
  useFrame(({ clock }) => {
    if (!ref.current || !spin || reduced) return;
    // A mechanism that is running, not posed. Only while someone is speaking.
    ref.current.rotation.z = clock.elapsedTime * spin;
    invalidate();
  });
  return (
    <mesh ref={ref} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[radius, tube, 14, 128]} />
      <meshStandardMaterial color={colour} roughness={0.24} metalness={0.98} />
    </mesh>
  );
}

export function OrreryScene(props: SceneProps) {
  return (
    <>
      <color attach="background" args={["#0a0b10"]} />
      <fog attach="fog" args={["#0a0b10", 11, 24]} />
      <ambientLight intensity={0.2} />
      <directionalLight position={[5, 8, 4]} intensity={1.1} color="#ffe9c4" />
      <pointLight position={[0, 1.4, 0]} intensity={5} distance={8} color="#c9a35e" />

      <group position={[0, 0.34, 0]}>
        <Ring radius={R * 1.06} tube={0.035} colour="#c49a52" />
        <Ring
          radius={R * 0.78}
          tube={0.024}
          colour="#a37e44"
          spin={props.speaking ? 0.06 : 0}
          reduced={props.reduced}
        />
        <Ring
          radius={R * 0.5}
          tube={0.018}
          colour="#7d6236"
          spin={props.speaking ? -0.1 : 0}
          reduced={props.reduced}
        />
      </group>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <circleGeometry args={[R * 0.42, 56]} />
        <meshStandardMaterial color="#16181f" roughness={0.35} metalness={0.6} />
      </mesh>

      <Arcs {...props} radius={R * 0.98} lift={0.34} rise={0.72} opacity={0.62} />
      {SEATS.map((seat) => (
        <OrreryMarker
          key={seat}
          seat={seat}
          colour={props.colours[seat] ?? "#8890a8"}
          lit={props.lit[seat] ?? 0}
          speaking={props.speaking === seat}
          reduced={props.reduced}
        />
      ))}
    </>
  );
}

export const SCENES: Record<Variant, (p: SceneProps) => React.ReactElement> = {
  obsidian: ObsidianScene,
  architect: ArchitectScene,
  candlelit: CandlelitScene,
  orrery: OrreryScene,
};

/** Camera per variant: each scene reads best from a different distance. */
export const CAMERAS: Record<Variant, { position: [number, number, number]; fov: number; look: number }> = {
  obsidian: { position: [0, 6.6, 13.2], fov: 30, look: 0.7 },
  architect: { position: [0, 7.4, 7.4], fov: 30, look: 0.5 },
  candlelit: { position: [0, 3.4, 8.2], fov: 36, look: 0.7 },
  orrery: { position: [0, 5.4, 8.6], fov: 34, look: 0.5 },
};
