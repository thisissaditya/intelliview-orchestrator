import "./globals.css";
import Providers from "./providers";

export const metadata = { title: "AI-Intelliview Orchestrator" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="font-sans">
        <Providers>
          <main className="p-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
