import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'NyayaConnect - Vernacular Legal Advisor & Lawyer Marketplace',
  description: 'Inclusive Vernacular Access to Indian Constitutional Justice & Transparent Legal Counsel'
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', backgroundColor: '#f8fafc', color: '#0f172a' }}>
        {children}
      </body>
    </html>
  );
}
