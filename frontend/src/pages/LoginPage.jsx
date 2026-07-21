import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [tab, setTab] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const res = tab === "login"
      ? await login(email, password)
      : await register(name, email, password);
    setBusy(false);
    if (!res.ok) toast.error(res.error || "Falha");
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2" data-testid="login-page">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 border-r border-border bg-[hsl(0_0%_98%)]">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
            Ecossistema Sapiens
          </div>
          <h1 className="mt-3 text-4xl leading-none">Sapiens Dashboard</h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-md">
            Camada de observabilidade pedagógica. Visualiza dados já processados por
            sistemas externos de análise cognitiva.
          </p>
        </div>
        <div className="space-y-3 max-w-md">
          <InfoRow label="Não classifica" value="Nenhuma inferência ou diagnóstico é gerado pela ferramenta." />
          <InfoRow label="Não completa dados" value='Campos ausentes são exibidos como "Sem dado".' />
          <InfoRow label="Agregações" value="Somente soma, contagem, média, percentual, ordenação e filtro." />
          <InfoRow label="Versionamento" value="Toda visualização exibe a versão da taxonomia utilizada." />
        </div>
        <div className="font-mono text-[10px] text-muted-foreground uppercase tracking-widest">
          v0.1 · MVP · Uso interno
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm border border-border p-8">
          <div className="lg:hidden mb-6">
            <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              Ecossistema Sapiens
            </div>
            <h1 className="text-2xl">Sapiens Dashboard</h1>
          </div>

          <Tabs value={tab} onValueChange={setTab} data-testid="auth-tabs">
            <TabsList className="grid grid-cols-2 w-full h-9">
              <TabsTrigger value="login" data-testid="tab-login">Entrar</TabsTrigger>
              <TabsTrigger value="register" data-testid="tab-register">Registrar</TabsTrigger>
            </TabsList>

            <form onSubmit={submit} className="mt-6 space-y-4">
              <TabsContent value="register" className="mt-0 space-y-4">
                <Field label="Nome">
                  <Input
                    data-testid="register-name-input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required={tab === "register"}
                    placeholder="Ex: Maria Souza"
                  />
                </Field>
              </TabsContent>

              <Field label="Email">
                <Input
                  data-testid="auth-email-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="admin@sapiens.edu"
                  autoComplete="email"
                />
              </Field>
              <Field label="Senha">
                <Input
                  data-testid="auth-password-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  autoComplete={tab === "login" ? "current-password" : "new-password"}
                />
              </Field>

              <Button
                data-testid="auth-submit-btn"
                type="submit"
                disabled={busy}
                className="w-full bg-[hsl(214_100%_34%)] hover:bg-[hsl(214_100%_28%)] text-white h-10"
              >
                {busy ? "Aguarde..." : tab === "login" ? "Entrar" : "Criar conta"}
              </Button>
            </form>
          </Tabs>

          <div className="mt-6 pt-6 border-t border-border text-xs text-muted-foreground font-mono">
            Conta de demonstração: <span className="text-foreground">admin@sapiens.edu</span> / <span className="text-foreground">admin123</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="border-l-2 border-[hsl(214_100%_34%)] pl-3">
      <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="text-sm text-foreground">{value}</div>
    </div>
  );
}
