import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Hardware Price Tracker",
  description: "Отслеживание цен на компьютерное железо",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>

        {/* Навигация */}
        <nav className="border-b border-gray-800 bg-gray-900">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">

              {/* Лого */}
              <Link href="/" className="flex items-center gap-2 font-semibold text-white">
                <span className="text-blue-400">⚡</span>
                <span>HardwareTracker</span>
              </Link>

              {/* Навигационные ссылки */}
              <div className="flex items-center gap-1">
                <Link
                  href="/"
                  className="px-3 py-1.5 rounded-md text-sm text-gray-300 hover:text-white hover:bg-gray-800 transition-colors"
                >
                  Dashboard
                </Link>
                <Link
                  href="/monitor"
                  className="px-3 py-1.5 rounded-md text-sm text-gray-300 hover:text-white hover:bg-gray-800 transition-colors"
                >
                  ETL Monitor
                </Link>
              </div>

            </div>
          </div>
        </nav>

        {/* Контент страницы */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>

      </body>
    </html>
  );
}
