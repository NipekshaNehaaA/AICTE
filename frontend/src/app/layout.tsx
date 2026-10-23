import type { Metadata } from 'next';
import './globals.css';
import { AppProvider } from '@/lib/app-context';
import { AppShell } from '@/components/layout/AppShell';

export const metadata: Metadata = {
  title: 'AICTE Approval & Compliance Automation System',
  description:
    'Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#FAFAFA] text-ink min-h-screen">
        <AppProvider>
          <AppShell>{children}</AppShell>
        </AppProvider>
      </body>
    </html>
  );
}
