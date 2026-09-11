"use client";

import { SWRConfig } from "swr";
import { swrFetcher } from "@/lib/fetcher";

export default function Providers({ children }) {
  return <SWRConfig value={{ fetcher: swrFetcher }}>{children}</SWRConfig>;
}