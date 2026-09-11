import "./globals.css";

export const metadata = { title: "AI-Intelliview Orchestrator" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="font-sans">
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
