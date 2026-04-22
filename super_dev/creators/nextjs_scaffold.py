"""
Next.js App Router 脚手架生成器。

当项目使用 Next.js 时，生成正确的 App Router 结构，
而非默认的 React+Vite 结构。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class NextjsScaffoldGenerator:
    """Generate a Next.js 14+ App Router project scaffold."""

    def __init__(self) -> None:
        self._files_written: list[Path] = []

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def generate(
        self,
        project_dir: str | Path,
        project_name: str,
        ui_profile: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Generate a complete Next.js App Router scaffold.

        Args:
            project_dir: Root project directory.
            project_name: Human-readable project name.
            ui_profile: Optional design-token overrides
                        (colors, fonts, border-radius, …).

        Returns:
            List of file paths that were created.
        """
        base = Path(project_dir).resolve() / "output" / "nextjs-scaffold"
        base.mkdir(parents=True, exist_ok=True)

        profile = ui_profile or {}
        self._files_written = []

        self._write(base / "app" / "layout.tsx", self._root_layout(project_name, profile))
        self._write(base / "app" / "page.tsx", self._home_page(project_name))
        self._write(base / "app" / "globals.css", self._globals_css(profile))
        self._write(base / "app" / "api" / "health" / "route.ts", self._health_route())
        self._write(base / "app" / "dashboard" / "layout.tsx", self._dashboard_layout())
        self._write(base / "app" / "dashboard" / "page.tsx", self._dashboard_page())
        self._write(base / "app" / "error.tsx", self._error_boundary())
        self._write(base / "app" / "loading.tsx", self._loading_ui())
        self._write(base / "app" / "not-found.tsx", self._not_found_page())
        self._write(base / "middleware.ts", self._middleware())
        self._write(base / "next.config.ts", self._next_config())
        self._write(
            base / "tailwind.config.ts",
            self.generate_tailwind_config(project_dir, ui_profile=profile),
        )
        self._write(base / "tsconfig.json", self._tsconfig())
        self._write(base / "package.json", self._package_json(project_name))
        self._write(base / ".eslintrc.json", self._eslintrc())
        self._write(base / "lib" / "utils.ts", self._lib_utils())

        return list(self._files_written)

    # ------------------------------------------------------------------
    # tailwind config (also exposed as standalone helper)
    # ------------------------------------------------------------------

    def generate_tailwind_config(
        self,
        project_dir: str | Path,  # noqa: ARG002 – kept for API symmetry
        ui_profile: dict[str, Any] | None = None,
    ) -> str:
        """Return the contents of a complete ``tailwind.config.ts``.

        The config extends the default Tailwind theme with project-specific
        design tokens.  When *ui_profile* is supplied its values override the
        built-in defaults for colors, fonts and border-radius.
        """
        p = ui_profile or {}
        colors = p.get("colors", {})
        fonts = p.get("fonts", {})
        radius = p.get("radius", {})

        def _c(key: str, fallback: str) -> str:
            return str(colors.get(key, fallback))

        def _f(key: str, fallback: str) -> str:
            return str(fonts.get(key, fallback))

        def _r(key: str, fallback: str) -> str:
            return str(radius.get(key, fallback))

        return f"""\
import type {{ Config }} from "tailwindcss";

const config: Config = {{
  content: [
    "./app/**/*.{{js,ts,jsx,tsx,mdx}}",
    "./components/**/*.{{js,ts,jsx,tsx,mdx}}",
    "./lib/**/*.{{js,ts,jsx,tsx,mdx}}",
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: {{
          DEFAULT: "{_c("primary", "#0f172a")}",
          foreground: "{_c("primary_foreground", "#ffffff")}",
        }},
        secondary: {{
          DEFAULT: "{_c("secondary", "#64748b")}",
          foreground: "{_c("secondary_foreground", "#ffffff")}",
        }},
        accent: {{
          DEFAULT: "{_c("accent", "#3b82f6")}",
          foreground: "{_c("accent_foreground", "#ffffff")}",
        }},
        background: "{_c("background", "#ffffff")}",
        foreground: "{_c("foreground", "#0f172a")}",
        muted: {{
          DEFAULT: "{_c("muted", "#f1f5f9")}",
          foreground: "{_c("muted_foreground", "#64748b")}",
        }},
        destructive: {{
          DEFAULT: "{_c("destructive", "#ef4444")}",
          foreground: "{_c("destructive_foreground", "#ffffff")}",
        }},
        border: "{_c("border", "#e2e8f0")}",
        ring: "{_c("ring", "#3b82f6")}",
      }},
      fontFamily: {{
        sans: ["{_f("sans", "Inter")}", "system-ui", "sans-serif"],
        mono: ["{_f("mono", "JetBrains Mono")}", "Menlo", "monospace"],
      }},
      borderRadius: {{
        lg: "{_r("lg", "0.75rem")}",
        md: "{_r("md", "0.5rem")}",
        sm: "{_r("sm", "0.25rem")}",
      }},
    }},
  }},
  plugins: [],
}};

export default config;
"""

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._files_written.append(path)

    # -- app/layout.tsx ------------------------------------------------

    @staticmethod
    def _root_layout(project_name: str, profile: dict[str, Any]) -> str:
        font_family = profile.get("fonts", {}).get("sans", "Inter")
        # Derive a valid JS identifier from the font name
        font_id = font_family.replace(" ", "_").lower()
        font_import = font_family.replace(" ", "_")
        return f"""\
import type {{ Metadata }} from "next";
import {{ {font_import} }} from "next/font/google";
import "./globals.css";

const {font_id} = {font_import}({{ subsets: ["latin"] }});

export const metadata: Metadata = {{
  title: "{project_name}",
  description: "{project_name} — powered by Next.js",
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="zh-CN">
      <body className={{{font_id}.className}}>{{children}}</body>
    </html>
  );
}}
"""

    # -- app/page.tsx --------------------------------------------------

    @staticmethod
    def _home_page(project_name: str) -> str:
        return f"""\
import Link from "next/link";

async function getWelcomeData() {{
  // Replace with your own data source.
  return {{ greeting: "Welcome to {project_name}" }};
}}

export default async function HomePage() {{
  const data = await getWelcomeData();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-4xl font-bold tracking-tight">{{data.greeting}}</h1>
      <p className="max-w-xl text-center text-muted-foreground">
        This is a Next.js App Router project. Edit{" "}
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm">
          app/page.tsx
        </code>{" "}
        to get started.
      </p>
      <div className="flex gap-4">
        <Link
          href="/dashboard"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Go to Dashboard
        </Link>
      </div>
    </main>
  );
}}
"""

    # -- app/globals.css -----------------------------------------------

    @staticmethod
    def _globals_css(profile: dict[str, Any]) -> str:
        colors = profile.get("colors", {})

        def _c(key: str, fallback: str) -> str:
            return str(colors.get(key, fallback))

        return f"""\
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {{
  :root {{
    --background: {_c("background", "#ffffff")};
    --foreground: {_c("foreground", "#0f172a")};
    --primary: {_c("primary", "#0f172a")};
    --primary-foreground: {_c("primary_foreground", "#ffffff")};
    --secondary: {_c("secondary", "#64748b")};
    --secondary-foreground: {_c("secondary_foreground", "#ffffff")};
    --accent: {_c("accent", "#3b82f6")};
    --accent-foreground: {_c("accent_foreground", "#ffffff")};
    --muted: {_c("muted", "#f1f5f9")};
    --muted-foreground: {_c("muted_foreground", "#64748b")};
    --destructive: {_c("destructive", "#ef4444")};
    --destructive-foreground: {_c("destructive_foreground", "#ffffff")};
    --border: {_c("border", "#e2e8f0")};
    --ring: {_c("ring", "#3b82f6")};
    --radius: 0.5rem;
  }}
}}

@layer base {{
  * {{
    border-color: var(--border);
  }}
  body {{
    background-color: var(--background);
    color: var(--foreground);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
}}
"""

    # -- app/api/health/route.ts ---------------------------------------

    @staticmethod
    def _health_route() -> str:
        return """\
import { NextResponse } from "next/server";

export const runtime = "edge";

export async function GET() {
  return NextResponse.json(
    {
      status: "healthy",
      timestamp: new Date().toISOString(),
    },
    { status: 200 },
  );
}
"""

    # -- app/dashboard/layout.tsx --------------------------------------

    @staticmethod
    def _dashboard_layout() -> str:
        return """\
import Link from "next/link";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r bg-muted/40 p-6">
        <nav className="flex flex-col gap-2">
          <Link
            href="/dashboard"
            className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted"
          >
            Overview
          </Link>
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
"""

    # -- app/dashboard/page.tsx ----------------------------------------

    @staticmethod
    def _dashboard_page() -> str:
        return """\
import { Suspense } from "react";

async function getStats() {
  // Replace with your data source.
  return { users: 128, revenue: 45_200, orders: 340 };
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-background p-6 shadow-sm">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight">{String(value)}</p>
    </div>
  );
}

async function StatsGrid() {
  const stats = await getStats();
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <StatCard label="Total Users" value={stats.users} />
      <StatCard label="Revenue" value={`$${stats.revenue.toLocaleString()}`} />
      <StatCard label="Orders" value={stats.orders} />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      <Suspense fallback={<div className="text-muted-foreground">Loading stats...</div>}>
        <StatsGrid />
      </Suspense>
    </div>
  );
}
"""

    # -- app/error.tsx --------------------------------------------------

    @staticmethod
    def _error_boundary() -> str:
        return """\
"use client";

import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4">
      <h2 className="text-xl font-semibold">Something went wrong</h2>
      <p className="text-sm text-muted-foreground">{error.message}</p>
      <button
        onClick={reset}
        className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Try again
      </button>
    </div>
  );
}
"""

    # -- app/loading.tsx ------------------------------------------------

    @staticmethod
    def _loading_ui() -> str:
        return """\
export default function Loading() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
    </div>
  );
}
"""

    # -- app/not-found.tsx ----------------------------------------------

    @staticmethod
    def _not_found_page() -> str:
        return """\
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="text-lg text-muted-foreground">Page not found</p>
      <Link
        href="/"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Back to Home
      </Link>
    </div>
  );
}
"""

    # -- middleware.ts ---------------------------------------------------

    @staticmethod
    def _middleware() -> str:
        return """\
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // Authentication check — replace with your auth logic.
  const token = request.cookies.get("auth-token");

  if (!token && request.nextUrl.pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  const response = NextResponse.next();
  response.headers.set("x-request-id", crypto.randomUUID());
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
"""

    # -- next.config.ts -------------------------------------------------

    @staticmethod
    def _next_config() -> str:
        return """\
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  compress: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.example.com",
      },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
"""

    # -- tsconfig.json --------------------------------------------------

    @staticmethod
    def _tsconfig() -> str:
        return json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2017",
                    "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": True,
                    "noEmit": True,
                    "esModuleInterop": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "jsx": "preserve",
                    "incremental": True,
                    "plugins": [{"name": "next"}],
                    "paths": {"@/*": ["./*"]},
                },
                "include": [
                    "next-env.d.ts",
                    "**/*.ts",
                    "**/*.tsx",
                    ".next/types/**/*.ts",
                ],
                "exclude": ["node_modules"],
            },
            indent=2,
            ensure_ascii=False,
        )

    # -- package.json ---------------------------------------------------

    @staticmethod
    def _package_json(project_name: str) -> str:
        pkg_name = project_name.lower().replace(" ", "-")
        return json.dumps(
            {
                "name": pkg_name,
                "version": "0.1.0",
                "private": True,
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint",
                },
                "dependencies": {
                    "next": "^14.2.0",
                    "react": "^18.3.0",
                    "react-dom": "^18.3.0",
                    "lucide-react": "^0.400.0",
                    "clsx": "^2.1.0",
                    "tailwind-merge": "^2.3.0",
                },
                "devDependencies": {
                    "typescript": "^5.4.0",
                    "@types/node": "^20.12.0",
                    "@types/react": "^18.3.0",
                    "@types/react-dom": "^18.3.0",
                    "tailwindcss": "^3.4.0",
                    "postcss": "^8.4.0",
                    "autoprefixer": "^10.4.0",
                    "eslint": "^8.57.0",
                    "eslint-config-next": "^14.2.0",
                },
            },
            indent=2,
            ensure_ascii=False,
        )

    # -- .eslintrc.json -------------------------------------------------

    @staticmethod
    def _eslintrc() -> str:
        return json.dumps(
            {
                "extends": ["next/core-web-vitals", "next/typescript"],
                "rules": {
                    "@typescript-eslint/no-unused-vars": [
                        "warn",
                        {"argsIgnorePattern": "^_"},
                    ],
                },
            },
            indent=2,
            ensure_ascii=False,
        )

    # -- lib/utils.ts ---------------------------------------------------

    @staticmethod
    def _lib_utils() -> str:
        return """\
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
"""
