import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';

const editorial = localFont({
  src: './fonts/CormorantGaramond.ttf',
  variable: '--font-editorial',
  weight: '300 700',
  display: 'swap',
  fallback: ['Georgia', 'serif'],
});
const interfaceFont = localFont({
  src: './fonts/DMSans.ttf',
  variable: '--font-interface',
  weight: '100 1000',
  display: 'swap',
  fallback: ['Arial', 'sans-serif'],
});

export const metadata: Metadata = {
  title: 'ShiftWatch · ML monitoring workbench',
  description:
    'Explore reproducible model evaluations, dataset drift, and feature distributions. A Python ML experiment with an interactive report viewer.',
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${editorial.variable} ${interfaceFont.variable}`}>
        {children}
      </body>
    </html>
  );
}
