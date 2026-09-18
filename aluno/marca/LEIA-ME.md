# Marca do Sapiens — arquivos de alta resolução

Gerados em 2026-09-16 a partir da **mesma geometria** de
`aluno/frontend/src/components/BrandMark.jsx`. Se a marca mudar lá, estes
arquivos precisam ser regerados — eles não são a fonte da verdade, são uma
exportação dela.

## O que usar

| Situação | Arquivo |
|---|---|
| Qualquer coisa que aceite vetor (impressão, Figma, slide) | `sapiens-lockup.svg` / `sapiens-simbolo.svg` |
| Símbolo sobre fundo escuro | `sapiens-simbolo-{512,1024,2048,4096}.png` |
| Símbolo sobre fundo claro / papel | `sapiens-simbolo-fundo-claro-2048.png` |
| Marca + palavra, fundo escuro | `sapiens-lockup-{2048,4096}.png` |
| Marca + palavra, fundo claro | `sapiens-lockup-fundo-claro-{2048,4096}.png` |
| Capa / slide pronto | `sapiens-lockup-fundo-escuro-2560.png` |
| Ícone de aplicativo | `sapiens-icone-app-1024.png` |
| Símbolo com auréola (destaque) | `sapiens-simbolo-halo-2048.png` |

**Os PNGs transparentes de fundo escuro têm a palavra em BRANCO** — eles somem
sobre papel branco. Para fundo claro existe a variante navy.

## Duas coisas que quem regerar precisa saber

1. **O degradê da massa exige `gradientUnits="userSpaceOnUse"`.** Sem isso ele
   é recalculado na caixa de cada círculo e a marca lê como bolhas de sabão
   empilhadas, não como um cérebro.
2. **A largura do lockup foi MEDIDA no pixel, não estimada.** A primeira
   exportação cortou o "s" final de "Sapiens" porque usou uma largura de texto
   estimada. O `letter-spacing` é `-0.045em` (`-3.375` em unidades do viewBox
   de 100) e a tinta da palavra termina em x=389.5.

A renderização usou a **Manrope ExtraBold**, que não está instalada nesta
máquina — ela foi baixada para uma pasta local e apontada por um
`fontconfig` temporário só durante a exportação.
