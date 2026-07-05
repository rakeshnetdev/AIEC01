"use client";

import { useState } from "react";
import { Cat } from "lucide-react";

import { Chat } from "@/components/chat";

export default function Page() {
  const [assistantId, setAssistantId] = useState("simple_agent");

  return (
    <main className="flex h-dvh flex-col">
      <header className="border-b bg-background">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Cat className="size-4" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-medium">Cat Health Agent</p>
              <p className="text-xs text-muted-foreground">LangGraph + Next.js</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="assistant-select" className="text-xs text-muted-foreground font-medium">
              Assistant:
            </label>
            <select
              id="assistant-select"
              value={assistantId}
              onChange={(e) => setAssistantId(e.target.value)}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-xs font-medium shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring cursor-pointer hover:bg-accent hover:text-accent-foreground"
            >
              <option value="simple_agent">Simple Agent</option>
              <option value="agent_with_helpfulness">Agent with Helpfulness Check</option>
            </select>
          </div>
        </div>
      </header>

      <Chat key={assistantId} assistantId={assistantId} />
    </main>
  );
}

