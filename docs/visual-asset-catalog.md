# Visual asset catalog

Created 2026-10-13 using the built-in image generator. All nine final images are stored in `frontend/public/assets/` and served by Next.js at `/assets/<filename>`.

## Inventory

| File | Purpose | Dimensions | Format | Transparent | File size | Status |
|---|---|---|---|---|---|---|
| [category-luxury.webp](../frontend/public/assets/category-luxury.webp) | Luxury category — generic executive sedan | 1024 × 1024 | WebP | Yes | 55,138 B (53.8 KiB) | AI-generated |
| [category-suv.webp](../frontend/public/assets/category-suv.webp) | SUV category — tall practical midsize SUV | 1024 × 1024 | WebP | Yes | 68,100 B (66.5 KiB) | AI-generated |
| [category-electric.webp](../frontend/public/assets/category-electric.webp) | Electric category — aerodynamic fastback with a closed grille | 1024 × 1024 | WebP | Yes | 59,066 B (57.7 KiB) | AI-generated |
| [category-economy.webp](../frontend/public/assets/category-economy.webp) | Economy category — compact five-door hatchback | 1024 × 1024 | WebP | Yes | 58,934 B (57.6 KiB) | AI-generated |
| [concierge-emblem.webp](../frontend/public/assets/concierge-emblem.webp) | Custom AI concierge brand emblem | 512 × 512 | WebP | Yes | 19,578 B (19.1 KiB) | AI-generated |
| [hero-route-pattern.webp](../frontend/public/assets/hero-route-pattern.webp) | Decorative hero background with quiet travel routes | 1920 × 1080 | WebP | No | 8,932 B (8.7 KiB) | AI-generated |
| [testimonial-01.webp](../frontend/public/assets/testimonial-01.webp) | Synthetic testimonial-avatar placeholder — portrait 1 | 512 × 512 | WebP | No | 27,116 B (26.5 KiB) | AI-generated |
| [testimonial-02.webp](../frontend/public/assets/testimonial-02.webp) | Synthetic testimonial-avatar placeholder — portrait 2 | 512 × 512 | WebP | No | 25,822 B (25.2 KiB) | AI-generated |
| [testimonial-03.webp](../frontend/public/assets/testimonial-03.webp) | Synthetic testimonial-avatar placeholder — portrait 3 | 512 × 512 | WebP | No | 20,976 B (20.5 KiB) | AI-generated |

**Total:** 343,662 bytes (335.6 KiB / 0.344 MB). Each image is below 300 KB; the complete set is below 2 MB.

## Visual system and usage

- The car category assets share a front three-quarter view, dark layered illustration finish, warm neutral highlights, restrained blue accents, and matching transparent padding. They depict categories, not identifiable brands or actual inventory.
- The custom concierge emblem is an abstract conversation mark with transparent negative space. Use it as branding imagery; functional controls and spec icons continue to use Phosphor Icons.
- The hero route pattern is a wide decorative background with a quiet warm surface and sparse route curves. It is not a seamless repeating tile. Keep foreground text and controls as live UI.
- The three portraits are unused and excluded from the current frontend direction at the user's request. Retained files depict fictional generated people; no customer identity, endorsement, review, or testimonial claim is attached. Do not display them in the application.
- Follow `design.md` for surrounding surfaces, typography, and layout. Raster illustrations include tonal detail and antialiasing derived from the declared palette; portrait skin tones remain natural. These images do not define additional UI color tokens.
- Keep car illustrations and the emblem contained within their canvases to preserve their padding; do not crop their silhouettes. Portraits are square with centered faces suitable for circular display. Provide meaningful localized alt text when an image communicates content; use empty alt text for purely decorative images.

## Export and verification

- Converted selected generated images to WebP at quality 86 and effort 6 with full alpha quality. No EXIF or source metadata is included.
- Car artwork is fitted to an 850px inner box on a 1024px square transparent canvas. The emblem is fitted to a 432px inner box on a 512px square transparent canvas. The hero and portraits are resized to their listed final dimensions.
- Decoded every final file and confirmed WebP format, exact dimensions, byte budgets, and opaque versus transparent status. All five transparent assets contain both fully transparent and fully opaque pixels.
- Visually inspected the final exports together, car thumbnails, the emblem at 32px, and portraits at 48px. Checked for clipped subjects, obvious generation artifacts, unwanted text, badges, logos, and watermarks.
- Page components and styles were not edited during asset generation. The subsequent car-rental frontend redesign uses the category artwork, hero pattern, and concierge emblem favicon. Vehicle cards explicitly label category artwork when a fleet photo has not been supplied.

## Generation prompt set

Each asset was generated in a separate built-in image-generator call. SUV, electric, and economy generation used the luxury illustration as a visual style reference. The selected emblem is a fresh generation; earlier emblem variants were discarded after edge inspection. The exact selected prompts follow.

### category-luxury.webp

```text
Create one production-ready category illustration for a premium car rental SaaS, category LUXURY. Output a single isolated generic executive sedan, full vehicle visible, on a genuinely transparent background. Square canvas, with generous consistent padding; front three-quarter view facing right, car occupying about 75% width. Style: sophisticated editorial vector-like digital illustration, crisp flat layered shapes, clean contour lines, mechanically believable proportions and wheels; no photorealism, no 3D render, no gradients, no cast shadow, no floor, no frame. Bento Quiet identity palette only: ink #1a1d24, warm surface #f4f3ef, accent blue #3552d4, muted #6b6f78, hairline #dcdad4. Use an ink executive sedan body, cream highlights, dark windows and wheels, very restrained blue detail. This is category artwork, not a specific brand or fleet car. No logos, no badges, no text, no letters, no license-plate characters, no watermarks. Refined calm aesthetic; silhouette must remain recognizable at thumbnail size. Intended final size 1024 by 1024 pixels.
```

### category-suv.webp

```text
Use the referenced image ONLY as the style, palette, framing, angle and illustration-finish reference. Create one NEW matching category illustration for SUV: a generic tall midsize SUV, with an upright roof, substantial ground clearance, two visible wheels and a confident practical silhouette. Single isolated full vehicle, genuinely transparent background, square canvas, front three-quarter view facing right. Keep generous padding, match the reference's approximate on-canvas scale and clean editorial layered illustration treatment. Not a photograph or a 3D render. Palette restricted to ink #1a1d24, warm surface #f4f3ef, accent blue #3552d4, muted #6b6f78 and hairline #dcdad4. Ink car body with cream highlights and small blue accents. Mechanically believable anatomy, consistent wheels and perspective. No logos, text, brand badges, license-plate characters, floor, cast shadow, gradient background or extra objects. Target 1024x1024. Preserve transparent alpha.
```

### category-electric.webp

```text
Use the referenced image ONLY as the style, palette, framing, angle and illustration-finish reference. Create one NEW matching category illustration for ELECTRIC: a generic electric car: a sleek compact four-door fastback with a smooth closed grille, modest aerodynamic wheels, and blue accent details; no charging cable or props. Single isolated full vehicle, genuinely transparent background, square canvas, front three-quarter view facing right. Keep generous padding, match the reference's approximate on-canvas scale and clean editorial layered illustration treatment. Not a photograph or a 3D render. Palette restricted to ink #1a1d24, warm surface #f4f3ef, accent blue #3552d4, muted #6b6f78 and hairline #dcdad4. Ink car body with cream highlights and small blue accents. Mechanically believable anatomy, consistent wheels and perspective. No logos, text, brand badges, license-plate characters, floor, cast shadow, gradient background or extra objects. Target 1024x1024. Preserve transparent alpha.
```

### category-economy.webp

```text
Use the referenced image ONLY as the style, palette, framing, angle and illustration-finish reference. Create one NEW matching category illustration for ECONOMY: a generic compact five-door economy hatchback with a shorter wheelbase, economical small body, clear practical silhouette and simpler wheels. Single isolated full vehicle, genuinely transparent background, square canvas, front three-quarter view facing right. Keep generous padding, match the reference's approximate on-canvas scale and clean editorial layered illustration treatment. Not a photograph or a 3D render. Palette restricted to ink #1a1d24, warm surface #f4f3ef, accent blue #3552d4, muted #6b6f78 and hairline #dcdad4. Ink car body with cream highlights and small blue accents. Mechanically believable anatomy, consistent wheels and perspective. No logos, text, brand badges, license-plate characters, floor, cast shadow, gradient background or extra objects. Target 1024x1024. Preserve transparent alpha.
```

### concierge-emblem.webp

```text
Generate a fresh single abstract AI concierge emblem, centered on a truly transparent square canvas. A SIMPLE FLAT SILHOUETTE: two clean rounded conversation-shaped arcs interlocking into a compact circular mark, with a small open diamond of negative space at the center. Only two uniform solid fill colors: blue #3552d4 and ink #1a1d24. This is a calm premium car-rental brand illustration that should be readable at 32px. No internal white shapes: all openings are transparent. Crisp smooth vector-like edges, substantial geometry, simple memorable shape. No hairline strokes, sparkles floating outside, gradients, grain, shadows, lighting, texture, 3D, letters, numbers, text, faces, characters, robot, branding, watermark or background. Flat print-ready graphic, not a rendered object. Generous clear padding. Intended final 512x512 PNG/WebP cutout.
```

### hero-route-pattern.webp

```text
Create one wide understated hero BACKGROUND graphic for a premium car-rental SaaS using the Bento Quiet identity. Wide 16:9 landscape composition, intended final 1920x1080. Uniform warm off-white background EXACTLY #f4f3ef. Very sparse elegant abstract travel-route curves: a few slender hairline #dcdad4 paths, rounded route bends, a few understated endpoints, and one restrained blue #3552d4 route accent. Large uninterrupted negative space across the composition for future headline and booking controls. Do not draw cars, people, text, maps with labels, logos, UI panels, cards or icons. Flat minimal editorial geometry, quiet architectural feel, clean smooth lines. No gradients, dark patches, shadows, grain, texture, glow or watermark. This should feel like subtle stationery for the existing system, never compete with the foreground UI.
```

### testimonial-01.webp

```text
Generate one photoreal editorial customer-avatar portrait for a premium bilingual car-rental platform. Subject: a fictional person, a woman in her early 30s with medium brown skin, dark shoulder-length hair and a warm relaxed smile, wearing a simple charcoal crew-neck top. Square composition, head and upper shoulders visible, face centered and looking into the camera; ample safe crop around the head for future circular avatar use. Soft natural studio lighting, true skin texture, realistic eyes and teeth, authentic approachable expression, restrained retouching, no glamour or plastic skin. Uniform warm off-white background matching #f4f3ef, very soft separation without dramatic shadows. Neutral wardrobe, natural skin tones, visually calm Bento Quiet identity. Intended final 512x512; should remain recognizable at 48px. No text, logos, accessories with branding, watermark, testimonial copy or implied real identity. Single person only.
```

### testimonial-02.webp

```text
Generate one photoreal editorial customer-avatar portrait for a premium bilingual car-rental platform. Subject: a fictional person, a man in his early 40s with light olive skin, short dark hair, subtle stubble and a friendly natural smile, wearing a simple muted gray collared shirt. Square composition, head and upper shoulders visible, face centered and looking into the camera; ample safe crop around the head for future circular avatar use. Soft natural studio lighting, true skin texture, realistic eyes and teeth, authentic approachable expression, restrained retouching, no glamour or plastic skin. Uniform warm off-white background matching #f4f3ef, very soft separation without dramatic shadows. Neutral wardrobe, natural skin tones, visually calm Bento Quiet identity. Intended final 512x512; should remain recognizable at 48px. No text, logos, accessories with branding, watermark, testimonial copy or implied real identity. Single person only.
```

### testimonial-03.webp

```text
Generate one photoreal editorial customer-avatar portrait for a premium bilingual car-rental platform. Subject: a fictional person, a woman in her late 40s with East Asian features, light-medium skin, short dark hair, a calm genuine smile, wearing a simple cream linen blouse. Square composition, head and upper shoulders visible, face centered and looking into the camera; ample safe crop around the head for future circular avatar use. Soft natural studio lighting, true skin texture, realistic eyes and teeth, authentic approachable expression, restrained retouching, no glamour or plastic skin. Uniform warm off-white background matching #f4f3ef, very soft separation without dramatic shadows. Neutral wardrobe, natural skin tones, visually calm Bento Quiet identity. Intended final 512x512; should remain recognizable at 48px. No text, logos, accessories with branding, watermark, testimonial copy or implied real identity. Single person only.
```
