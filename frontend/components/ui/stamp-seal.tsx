"use client";

import { motion, useReducedMotion } from "framer-motion";

/**
 * The one signature element this design system is built around (HANDOFF.md
 * §4): a circular brass "seal" that snaps onto a document with a slight
 * overshoot. Used in the landing hero (on the ledger-card mockup, scale +
 * rotate on load) and reused as-is — not reinvented — for each completed
 * stage in the filing-history timeline (§3d), where it plays on scroll into
 * view instead of on page load.
 *
 * Respects prefers-reduced-motion: when the user has that set, Framer
 * Motion's useReducedMotion() short-circuits the entrance animation to a
 * static final state rather than skipping rendering entirely.
 */
export function StampSeal({
  size = 88,
  label = "TAXFLOW",
  sublabel = "VERIFIED",
  delay = 0,
  className,
}: {
  size?: number;
  label?: string;
  sublabel?: string;
  delay?: number;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={className}
      initial={reduceMotion ? false : { scale: 1.7, rotate: -22, opacity: 0 }}
      whileInView={{ scale: 1, rotate: -8, opacity: 1 }}
      viewport={{ once: true, amount: 0.7 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : { duration: 0.6, delay, ease: [0.34, 1.56, 0.64, 1] }
      }
      aria-hidden="true"
    >
      <circle cx="50" cy="50" r="47" style={{ fill: "var(--brass)" }} />
      <circle
        cx="50"
        cy="50"
        r="47"
        style={{ fill: "none", stroke: "var(--bg)", strokeWidth: 1.5 }}
        strokeDasharray="3 2.5"
      />
      <circle
        cx="50"
        cy="50"
        r="37"
        style={{ fill: "none", stroke: "var(--bg)", strokeWidth: 1.25 }}
      />
      <text
        x="50"
        y="46"
        textAnchor="middle"
        fontSize="10.5"
        style={{ fill: "var(--bg)", fontFamily: "var(--font-plex-mono)" }}
        letterSpacing="0.5"
      >
        {label}
      </text>
      <text
        x="50"
        y="60"
        textAnchor="middle"
        fontSize="7"
        style={{ fill: "var(--bg)", fontFamily: "var(--font-plex-mono)" }}
        letterSpacing="1.5"
      >
        {sublabel}
      </text>
    </motion.svg>
  );
}
