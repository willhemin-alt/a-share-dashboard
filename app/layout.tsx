import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "A股策略看板",
  description: "A股市场、科技热点、重点关注股与模拟账户的每日策略看板。",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
