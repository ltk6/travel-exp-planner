export default function PlannerLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 pb-24">{children}</main>
  );
}
