'use client';

import Link from 'next/link';
import { Zap } from 'lucide-react';

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500">
        <Zap className="h-5 w-5 text-white" />
      </div>
      <span className="text-xl font-bold bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
        Shortify
      </span>
    </Link>
  );
}
