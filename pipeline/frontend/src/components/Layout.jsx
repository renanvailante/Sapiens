import Sidebar from "./Sidebar";
import { Toaster } from "sonner";

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 min-w-0" data-testid="main-content">
        {children}
      </main>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "white",
            color: "#09090B",
            border: "1px solid #E4E4E7",
            borderRadius: "2px",
          },
        }}
      />
    </div>
  );
}
