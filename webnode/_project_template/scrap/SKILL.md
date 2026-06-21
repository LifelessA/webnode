---
name: anf-website-builder
description: "Build professional websites that don't look AI-generated using the ANIF Framework (Assemble, Normalize, Illustrate, Fill). Use when the user wants to create a website, landing page, or marketing page that looks designer-made. Triggers: 'build me a website', 'create a landing page', 'make a professional site', 'ANF framework', or any request for a polished web page that should not look like typical AI output. Also use when the user complains about generic/ugly AI-generated websites. Do NOT use for: dashboards, admin panels, web apps with complex state, or internal tools — those need different patterns."
metadata:
  mcpmarket-version: 1.0.0
---
# ANIF Website Builder

Build websites that look designer-made by using ACTUAL designer-made components, REAL photography, and researched content. Never hand-write sections from scratch. Never ship a page without visual assets.

**The rule:** If a component exists in a library, use it. If a photo exists for free, download it. If copy can be more specific, make it so.

## The Framework

**A**ssemble — install real components from libraries
**N**ormalize — unify into one cohesive design
**I**llustrate — source and add real visuals to every page
**F**ill — research audience and topic, populate with specific content

## Workflow

### Step 1: Understand the Project

Ask the user (if not already clear):
- What is the product/service/company?
- What sections? (hero, features, pricing, testimonials, FAQ, etc.)
- Design preferences? (dark/light, minimal/bold)
- Reference sites?

### Step 2: Brief — Establish Direction Before Coding

Before installing anything, define the visual and content direction. Write a `brief.md` in the project root:

1. **Target audience** — Who are they? What pain are they escaping? What outcome do they want? (2-3 sentences)
2. **Layout personality** — Dense/editorial (tight spacing, lots of content) OR spacious/minimal (lots of white space) OR hybrid?
3. **Hero composition** — Left-aligned text + right visual OR centered + full-width background OR split-screen?
4. **Brand voice** — Professional/enterprise OR friendly/consumer OR technical/developer?
5. **Competitor reference** (optional) — A real site to benchmark against

This brief guides Normalize and Fill decisions. Skip only if the user has already provided all of this context.

### Step 3: Assemble — Install and Use Real Components

**CRITICAL: Actually install components from libraries. Do NOT hand-write sections.**

Read `references/component-libraries.md` for the full component library list.

**Init project:**
```bash
npx --yes create-next-app@latest <name> --typescript --tailwind --app --src-dir --no-eslint --no-import-alias --use-npm --turbopack --yes
cd <name>
npx --yes shadcn@latest init -d
npm install framer-motion lucide-react
mkdir -p public/images public/videos
```

**For each section, install the actual component:**

#### Hero Section
```bash
npx --yes shadcn@latest add "https://magicui.design/r/animated-gradient-text"
npx --yes shadcn@latest add "https://magicui.design/r/shimmer-button"
npx --yes shadcn@latest add "https://magicui.design/r/particles"
```

#### Features
```bash
npx --yes shadcn@latest add "https://magicui.design/r/bento-grid"
# OR
npx --yes shadcn@latest add "https://magicui.design/r/magic-card"
```

#### Social Proof / Testimonials
```bash
npx --yes shadcn@latest add "https://magicui.design/r/marquee"
```

#### Pricing / FAQ / Navigation
```bash
npx --yes shadcn@latest add card button accordion navigation-menu badge separator
```

#### Animated Elements
```bash
npx --yes shadcn@latest add "https://magicui.design/r/word-rotate"
npx --yes shadcn@latest add "https://magicui.design/r/blur-fade"
```

#### Background Effects
```bash
npx --yes shadcn@latest add "https://magicui.design/r/dot-pattern"
npx --yes shadcn@latest add "https://magicui.design/r/retro-grid"
```

**All components install to `src/components/ui/`.** Import from there:
```tsx
import { BentoGrid, BentoCard } from "@/components/ui/bento-grid";
import { BlurFade } from "@/components/ui/blur-fade";  // named export, NOT default
```

**Stats/metrics:** Use plain `<span>` with specific numbers. Do NOT use NumberTicker — it shows 0 on static renders.

**Sticky header (required):** Every site needs a sticky nav:
```tsx
<nav className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl">
```
Non-sticky headers are an AI-generated tell — every real production site uses sticky navigation.

### Step 4: Normalize — Unify the Design

1. **Typography** — Pick ONE font pairing via `next/font/google`. Never use Inter alone.
2. **Color palette** — NOT indigo/purple/violet. Update CSS variables in `globals.css`.
3. **Light or dark mode** — Match the brand. Customize `:root` or `.dark` CSS variables.
4. **Spacing** — `py-20` or `py-24` sections, `max-w-6xl mx-auto px-6` containers.
5. **Visual rhythm** — At least 3 different background treatments across sections.
6. **Remove AI tells** — No identical grids, no generic words, no round numbers, no default gray palette.
7. **SEO meta** — Add a descriptive `<meta name="description">` in layout.tsx. Use semantic `<h2>`/`<h3>` headings that describe section content (not clever/cute headings that mean nothing to search engines or AI summarizers).

### Step 5: Illustrate — Source Visuals for Every Page

**This step runs PER PAGE.** For each page, analyze every section and determine what visual assets would enhance it. Then find, download, and integrate them.

Read `references/image-sources.md` for the full source list.

**PREFER REAL PHOTOS over flat SVG illustrations.** Unsplash photos score significantly higher on visual richness than generic SVGs. Photos add atmospheric depth that CSS cannot match.

**The process:**

1. **Audit the page** — For each section, determine the visual type needed.
2. **Download photos from Unsplash/Pexels** (free, no API key):
   ```bash
   # Search unsplash.com, get photo ID from URL, download:
   curl -L "https://images.unsplash.com/photo-{ID}?w=800&h=600&fit=crop&q=80" -o public/images/hero.jpg
   ```
   Download 3-5 photos per page matching the product/industry.
3. **Use photos as backgrounds with overlays**, not as standalone images:
   ```tsx
   {/* Hero: full-width photo + gradient overlay */}
   <div className="absolute inset-0">
     <Image src="/images/hero.jpg" alt="" fill className="object-cover" />
     <div className="absolute inset-0 bg-gradient-to-r from-background via-background/95 to-background/70" />
   </div>

   {/* Bento card: photo at low opacity + gradient fade */}
   background: (
     <div className="absolute inset-0 overflow-hidden rounded-xl">
       <Image src="/images/feature.jpg" alt="" fill className="object-cover opacity-20" />
       <div className="absolute inset-0 bg-gradient-to-t from-card via-card/80 to-transparent" />
     </div>
   )
   ```
4. **Supplement with SVGs** from unDraw/DrawKit for specific illustrations where photos don't fit.
5. **Generate CSS backgrounds** — Use gradient blobs (`blur-[120px]`), DotPattern, RetroGrid for section variety.
6. **Video backgrounds (optional, for lifestyle/consumer brands):**
   ```bash
   # Download from coverr.co or mixkit.co (free, no attribution):
   curl -L "<mp4-url>" -o public/videos/hero.mp4
   ```
   ```tsx
   <video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover">
     <source src="/videos/hero.mp4" type="video/mp4" />
   </video>
   <div className="absolute inset-0 bg-background/70" />
   ```
   Best for: lifestyle brands, SaaS with human element. Avoid for: developer tools, enterprise B2B.

**Visual requirements per section type:**

| Section | Must Have | Source |
|---------|----------|--------|
| Hero | Full-width background photo OR video + gradient overlay | Unsplash, Coverr |
| Features | Photo backgrounds on large bento cards at 15-20% opacity | Unsplash |
| How it works | Different component type from features (MagicCard vs BentoGrid) | — |
| Section dividers | Wave or curve SVG between at least 2 sections | getwaves.io |
| CTA section | Background pattern, photo, or gradient mesh | Unsplash, Haikei |
| Testimonials | Colored avatar initials (CSS, no download needed) | CSS |
| Blog index | Card grid with featured images per post | Unsplash per article |

**What NOT to do:**
- Don't skip this step — text-only pages look AI-generated regardless of copy quality
- Don't use tiny Lucide icons as section illustrations — they're for buttons and lists
- Don't hotlink to external URLs — always download to `public/images/`
- Don't use the same illustration twice on one page

### Step 6: Fill — Research and Populate

**Research** the product/industry with WebSearch. Also research the **target audience** — who they are, what language they use, what they fear and want. Refer to the brief from Step 2.

**Content quality rules:**
- Headlines: benefit-driven and specific. Bad: "Everything your app should be." Good: "Ship 3x faster with zero YAML."
- Stats: precise numbers — "14,283" not "14,000+", "2.3s" not "fast"
- Testimonials: include specific claims — "Lost 23kg in 6 months", "integration took 23 minutes"
- FAQ answers: include technical details (encryption type, API name, percentage)
- Banned headline words: "Powerful", "Seamless", "Revolutionary", "Game-changing", "Next-gen", "Cutting-edge"

**GEO (Generative Engine Optimization):**
Sites need to be readable by AI answer engines (ChatGPT, Perplexity, etc.), not just humans:
- Include FAQ entries that directly answer "What is [Product]?" and "How does [Product] work?"
- Use semantic `<h2>`/`<h3>` headings that describe content — not clever/vague headings
- Add an "About [Company]" paragraph visible on the page — AI summarizers scrape this first
- The `<meta name="description">` should be a plain-language summary of the product in one sentence

### Step 7: Review and Polish

Run `npm run dev` and use Playwright to screenshot the result. Check:
- Every section has a visual element (illustration, pattern, or mockup)
- No plain text-on-background sections
- Section backgrounds vary (at least 3 different treatments)
- Features and How-it-works use different component types
- Wave/curve dividers separate at least 2 sections
- Sticky header is present and working
- No overflow or rendering issues

### Step 8: Design System (multi-page sites only)

After page 1 is built and reviewed, extract the design system to `design-system.md`:

```markdown
# Design System

## Colors
- Primary: [value]
- Accent: [value]
- Background: [value]

## Typography
- Heading: [font name], weights [700, 800]
- Body: [font name], weights [400, 500]

## Spacing
- Section padding: py-24
- Container: max-w-6xl mx-auto px-6

## Components used
- Hero: [component names]
- Cards: [component names]
- Animations: [component names]

## Visual patterns
- Background treatment 1: [describe]
- Background treatment 2: [describe]
- Background treatment 3: [describe]
```

For pages 2-N, Claude reads `design-system.md` first and matches the established system. New pages may introduce new layouts but must stay within the defined color + type system. The design system carries across all pages — consistency is what makes a site feel professional.

**Common additional pages:**
- **About page** — Company story, team, values. Use timeline or alternating text+photo layout.
- **Blog index** — Card grid with featured images, category badges, reading time. Use `AspectRatio` from shadcn.
- **Contact page** — Form + map or office photo. Keep minimal.
- **Services/Product pages** — Reuse feature bento pattern with different content per page.

## Important Rules

1. **ALWAYS install components from libraries** — never hand-write what a library provides.
2. **ALWAYS illustrate** — every page needs real photos (Unsplash) or SVGs. Text-only = AI-looking.
3. **Never use Tailwind's default indigo/purple** — pick a unique brand color.
4. **Never use Inter as the only font** — always add a heading font.
5. **Test by viewing the result** — use Playwright to screenshot, don't guess.
6. **Per-page illustration** — run the Illustrate step for every page, not just once per site.
7. **Never use `BlurFade` with `inView` prop** — it uses IntersectionObserver which causes sections to be invisible in screenshots and static renders. Use `BlurFade` with `delay` only.
8. **Never use `NumberTicker`** — it animates from 0 and shows 0 in screenshots. Use plain text spans.
9. **Card contrast on dark themes** — use solid `bg-card` not transparent `bg-white/5`. Glass effects need at least 8-10% opacity to be visible.
10. **Sticky header always** — use `sticky top-0 z-50 backdrop-blur-xl bg-background/80`.
