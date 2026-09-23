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
  /** `extras` carrega os campos que só existem para quem declara ser menor de
   *  idade (`menorDeIdade`, `responsavelNome`, `responsavelWhatsapp`) e a
   *  origem de aquisição (`origem`, de `lib/campanha.origemParaEnvio` —
   *  `{utm_source, campanha_id, ...}` ou `{}`). Um objeto e não parâmetros
   *  posicionais: a assinatura já tinha cinco, e a sexta posição seria o
   *  ponto em que alguém passa o cupom no lugar do telefone do responsável
   *  sem o compilador dizer nada. */
  const signup = async (name, email, password, whatsapp, promoCode, extras = {}) => {
    const { data } = await api.post("/auth/signup", {
      name, email, password,
      whatsapp: whatsapp?.trim(),
      promo_code: promoCode?.trim() || undefined,
      menor_de_idade: Boolean(extras.menorDeIdade),
      responsavel_nome: extras.responsavelNome?.trim() || undefined,
      responsavel_whatsapp: extras.responsavelWhatsapp?.trim() || undefined,
      ...extras.origem,
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
   * formulário nenhum para preencher. Quem entrar assim informa o número na
   * primeira tela que precisa dele (hoje, a lista de espera da mentoria).
   */
  const loginGoogle = async (promoCode, whatsapp, extras = {}) => {
    const idToken = await entrarComGoogle();
    const { data } = await api.post("/auth/google", {
      id_token: idToken,
      promo_code: promoCode?.trim() || undefined,
      whatsapp: whatsapp?.trim() || undefined,
      menor_de_idade: Boolean(extras.menorDeIdade),
      responsavel_nome: extras.responsavelNome?.trim() || undefined,
      responsavel_whatsapp: extras.responsavelWhatsapp?.trim() || undefined,
      origem: extras.origem && Object.keys(extras.origem).length ? extras.origem : undefined,
    });
    localStorage.setItem("sapiens_token", data.token);
    setUser(data.user);
    // O ÚNICO dos três que não devolve só o usuário. O botão do Google entra
    // E cadastra pela mesma porta, e o `user` devolvido é igual nos dois
    // casos — `conta_criada` (ver `backend/auth.py`) é a única forma de o
    // frontend saber que acabou de nascer uma conta. Quem usa é o rastreio de
    // aquisição, que só pode contar `Lead` em cadastro de verdade.
    return { user: data.user, contaCriada: Boolean(data.conta_criada) };
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
