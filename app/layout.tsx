import type { Metadata } from 'next';
import './globals.css';

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
      <body>{children}</body>
    </html>
  );
}
