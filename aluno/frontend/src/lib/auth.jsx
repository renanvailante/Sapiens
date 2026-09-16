import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";
import { entrarComGoogle } from "./firebase";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("sapiens_token", data.token);
    setUser(data.user);
    return data.user;
  };
  const signup = async (name, email, password, whatsapp, promoCode) => {
    const { data } = await api.post("/auth/signup", {
      name, email, password,
      whatsapp: whatsapp?.trim(),
      promo_code: promoCode?.trim() || undefined,
    });
    localStorage.setItem("sapiens_token", data.token);
    setUser(data.user);
    return data.user;
  };
  /**
   * Login com Google: o Firebase autentica, o backend verifica o ID token e
   * emite a MESMA sessão do fluxo de e-mail/senha. Daqui para a frente não há
   * diferença — o resto do app não sabe por qual porta a pessoa entrou.
   * `promoCode` e `whatsapp` só importam se essa for a primeira vez da conta —
   * o backend ignora os dois campos quando a conta já existe. O WhatsApp é
   * opcional aqui (diferente do cadastro por e-mail, onde é obrigatório):
   * este botão também cria conta a partir da tela de LOGIN, onde não há
   * formulário nenhum para preencher. Quem entrar assim é convidado a
   * informar o número depois, pelo cartão `PedirWhatsApp`.
   */
  const loginGoogle = async (promoCode, whatsapp) => {
    const idToken = await entrarComGoogle();
    const { data } = await api.post("/auth/google", {
      id_token: idToken,
      promo_code: promoCode?.trim() || undefined,
      whatsapp: whatsapp?.trim() || undefined,
    });
    localStorage.setItem("sapiens_token", data.token);
    setUser(data.user);
    return data.user;
  };
  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("sapiens_token");
    setUser(null);
  };
  return (
    <AuthCtx.Provider value={{ user, loading, login, signup, loginGoogle, logout, refresh: checkAuth, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
