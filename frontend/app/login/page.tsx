import { AuthForm } from "@/components/auth-form";
import { NavBar } from "@/components/nav-bar";

export default function LoginPage() {
  return (
    <>
      <NavBar />
      <main className="mx-auto max-w-5xl px-4 py-16">
        <AuthForm mode="login" />
      </main>
    </>
  );
}
