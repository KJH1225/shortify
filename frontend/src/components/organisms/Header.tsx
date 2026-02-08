'use client';

import Link from 'next/link';
import { Github, History } from 'lucide-react';
import { Logo } from '@/components/atoms/Logo';
import { Button } from '@/components/ui/button';

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <Logo />
        <nav className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/history">
              <History className="h-4 w-4 mr-1" />
              히스토리
            </Link>
          </Button>
          <Button variant="ghost" size="icon" asChild>
            <a href="https://github.com/KJH1225/shortify" target="_blank" rel="noopener noreferrer">
              <Github className="h-5 w-5" />
            </a>
          </Button>
        </nav>
      </div>
    </header>
  );
}
