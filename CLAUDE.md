# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mars is a Next.js 16 web application with React 19 and TypeScript, serving as a component showcase using shadcn UI components built on Base UI React primitives with Tailwind CSS v4.

## Development Commands

```bash
npm run dev      # Start dev server at http://localhost:3000
npm run build    # Production build
npm run lint     # Run ESLint
```

## Architecture

### Stack
- Next.js 16 (App Router)
- React 19 with TypeScript 5
- Tailwind CSS v4 with CSS variables for theming
- Base UI React for headless components
- Class Variance Authority (CVA) for component variants
- HugeIcons for icons

### Directory Structure
- `app/` - Next.js App Router pages and layouts
- `components/ui/` - Reusable shadcn UI components (button, card, select, etc.)
- `components/` - Page-specific components
- `lib/utils.ts` - `cn()` utility for Tailwind class merging

### Component Patterns
- Use `cn()` from `@/lib/utils` for conditional className merging
- Define variants with CVA (class-variance-authority)
- Add `data-slot` attributes for semantic element identification
- Support size variants (sm, default, lg) where appropriate

### Styling
- All styling via Tailwind utility classes
- Theme colors defined as CSS variables in `globals.css`
- Dark mode supported via CSS variable switching

### Path Aliases
- `@/*` - Project root
- `@/components` - Components directory
- `@/ui` - UI components (`components/ui/`)
- `@/lib/utils` - Utilities
