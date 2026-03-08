'use client';

import { Header } from '@/components/organisms/Header';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container py-8">
        {children}
      </main>
      <footer className="border-t border-border/50 py-6 mt-auto">
        <div className="container text-center text-sm text-muted-foreground">
          {/* <p>Shortify - AI 영상 하이라이트 추출 서비스</p> */}
        </div>
      </footer>
    </div>
  );
}
