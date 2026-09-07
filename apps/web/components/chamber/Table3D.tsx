"use client";

/* The chamber in three dimensions.
 *
 * frameloop="demand" is the important line. A boardroom table is not a game:
 * nothing moves unless a turn arrives or the replay is scrubbed, so rendering
 * sixty times a second would burn a laptop battery to display a still image.
 * The scene re-renders when invalidate() is called and at no other time. The
 * one exception is a seat that is currently speaking, which breathes — and
 * that stops under prefers-reduced-motion.
 *
 * Abstract forms, never avatars, in every variant. Giving the mandates faces
 * would invite a reader to trust them as people, and their expertise is
 * prompt-defined; the interface should not add authority the system lacks.
 *
 * The scene itself lives in scenes.tsx. This file is only the canvas, the
 * camera and the invalidation rule, so a variant cannot change what the
 * chamber SHOWS — only how it looks.
 */

import { Canvas, useThree } from "@react-three/fiber";
import { useEffect } from "react";
import { glow } from "@/lib/chamber";
import { CAMERAS, SCENES, type Variant } from "./scenes";
import type { ChamberEdge } from "./TableSVG";

export function Table3D({
  edges,
  speaking,
  lastSpokeAt,
  activeOrdinal,
  colours,
  reduced,
  variant = "obsidian",
}: {
  edges: ChamberEdge[];
  speaking: string | null;
  lastSpokeAt: Record<string, number>;
  activeOrdinal: number;
  colours: Record<string, string>;
  reduced: boolean;
  variant?: Variant;
}) {
  const Scene = SCENES[variant] ?? SCENES.obsidian;
  const camera = CAMERAS[variant] ?? CAMERAS.obsidian;

  const lit = Object.fromEntries(
    Object.keys(colours).map((seat) => [seat, glow(lastSpokeAt[seat] ?? null, activeOrdinal)]),
  );

  return (
    <Canvas
      frameloop="demand"
      dpr={[1, 1.75]}
      shadows
      camera={{ position: camera.position, fov: camera.fov }}
      gl={{ antialias: true, powerPreference: "low-power" }}
      data-testid="table-3d"
    >
      <CameraAim height={camera.look} />
      <Scene
        edges={edges}
        speaking={speaking}
        lit={lit}
        colours={colours}
        reduced={reduced}
      />
      <Invalidator dep={`${variant}-${speaking}-${activeOrdinal}-${edges.length}`} />
    </Canvas>
  );
}

/** Aim above the table centre so the whole ring fits, rather than the near edge
 *  filling the frame. */
function CameraAim({ height }: { height: number }) {
  const { camera, invalidate } = useThree();
  useEffect(() => {
    camera.lookAt(0, height, 0);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, height, invalidate]);
  return null;
}

/** Re-render exactly when the data changes, and never otherwise. */
function Invalidator({ dep }: { dep: string }) {
  const { invalidate } = useThree();
  useEffect(() => invalidate(), [dep, invalidate]);
  return null;
}
