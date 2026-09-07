# ShiftWatch design system

The dashboard applies the editorial and cosmic design language in the supplied Comet reference specification to a working ML report viewer.

## Applied visual system

- White canvas (`#ffffff`), deep green-black text (`#091717`), warm ivory cards (`#fbfaf4`, `#f6f5ee`), and teal accents (`#21808d`).
- Light, high-contrast serif display typography; restrained sans-serif controls and body copy; uppercase monospaced metadata.
- Floating navigation controls, capsule actions with concentric outlines and icon discs, inset highlights, and diffuse shadows.
- Rounded 24px feature and metric cards, a 48px dark teal distribution panel, and a warm ivory footer.
- Thin orbital geometry and one original, stippled planetary accent, clipped inside a noninteractive decorative layer.
- Responsive 24px mobile gutters, wrapping controls, stacked analytical panels, keyboard focus indicators, and reduced-motion support.

These styles adapt the reference to the existing dashboard. The ML workflow, data, controls, and report contract are preserved. Comet-specific landing-page sections, brand assets, video, download actions, and FAQs are not part of ShiftWatch.

## Typography and licensing

The proprietary typefaces named in the reference are not included. The implementation self-hosts **Cormorant Garamond** at light display weights and **DM Sans** for the interface. Both are distributed under the SIL Open Font License; original license files are stored with the fonts in `app/fonts/`.

- [Cormorant Garamond source](https://github.com/google/fonts/tree/main/ofl/cormorantgaramond)
- [DM Sans source](https://github.com/google/fonts/tree/main/ofl/dmsans)

The font files are compiled with the app's asset pipeline so both the root-hosted preview and GitHub Pages can serve them without third-party font requests.

## Original artwork

`assets/layered-sphere.png` was generated with the built-in image-generation tool, in one new-generation call. It is a transparent, 1254 × 1254 PNG; the native output and alpha are preserved. The exact generation prompt is stored in [planet-artwork-prompt.txt](planet-artwork-prompt.txt). It is original decorative artwork, not a copy of the Comet brand or product imagery.

The accent is hidden from assistive technology and cannot intercept pointer events. The visible data chart remains a semantic SVG with actual numerical values and descriptive labels.
