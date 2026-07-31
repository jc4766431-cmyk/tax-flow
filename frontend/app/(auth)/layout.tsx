export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="ledger-rule flex min-h-screen items-center justify-center bg-[var(--bg)] px-4 py-12">
      {children}
    </div>
  );
}
