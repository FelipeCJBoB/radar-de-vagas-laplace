# Limites e termos de uso

Leia antes de colocar o monitor para rodar. Isto é orientação prática, não aconselhamento jurídico.

## Uso pessoal e de baixo volume

O monitor foi feito para **uma pessoa buscar vaga para si**. Ele roda a cada poucos dias, faz um
punhado de requisições por rodada (com pausas entre elas) e não tenta contornar limite nem bloqueio.
Mantenha assim:

- **Não aumente a frequência** além de uma rodada a cada poucos dias.
- **Não use proxy rotativo** nem artifício para contornar limite ou bloqueio. Se uma fonte responde
  429 ("muitas requisições"), o coletor espera e tenta de novo; se continuar, pause.
- **Não redistribua** as vagas coletadas nem monte um serviço em cima delas. O conteúdo dos anúncios
  é das empresas e das plataformas.
- **Não faça login** nem automatize candidaturas. O monitor lê só o que está aberto.

## Termos de uso das plataformas

LinkedIn, Indeed e Gupy têm termos próprios, e **alguns restringem coleta automatizada**. Este
projeto usa endpoints públicos que as próprias páginas de busca usam, mas isso **não é uma
permissão** de ninguém. Quem roda o monitor é quem responde pelo uso. Se você não quer esse risco:

- desligue a fonte em `config.yaml` (`fontes.<nome>.ativo: false`) ou use `--skip`;
- ou use só a Gupy, um portal de vagas de empresas com busca pública (confira os termos dela).

## As fontes não são oficiais e vão quebrar

Nenhuma das três oferece uma API pública estável para isto. A Gupy já mudou de endereço uma vez e
passou dias respondendo 404. Quando acontecer:

- o relatório e as notificações avisam ("fonte com zero vagas");
- o modelo tem um teste diário que abre uma issue quando uma fonte muda;
- você atualiza pelo [guia 08](08-atualizar-do-modelo.md).

## Só Brasil

A Gupy é brasileira, e as buscas do Indeed e do LinkedIn estão configuradas para o Brasil. O
catálogo de cidades e regiões é o do IBGE. Outro país exigiria fontes e geografia novas.

## Cobertura

As três fontes cobrem bem **escritório, tecnologia e empresas médias e grandes**. Cobrem mal
**vagas operacionais, de saúde, de comércio e de pequenas empresas**, que se anunciam em outros
canais. O monitor mostra o que as fontes têm; ele não cria vagas que elas não têm.

## Dados pessoais (LGPD)

- O **seu** currículo e o **seu** perfil são dados pessoais seus. Você decide onde guardá-los; veja
  o [guia 06](06-privacidade.md).
- O monitor **anonimiza localmente** o currículo antes de enviá-lo a uma IA e só envia depois que
  você aprova o texto. Mesmo assim, confira: nomes de empresas e escolas podem permanecer
  (`init --ocultar`).
- O Gemini gratuito pode usar o que recebe para treinar. Se isso não serve, use o Claude pela API
  ou o modo manual, sem IA.
- Os relatórios têm **anúncios públicos** e a **nota que o monitor deu para você**. Em repositório
  público, isso revela o seu perfil: use repositório privado.
- Não coloque no repositório dados pessoais de **terceiros** (colegas, indicações, contatos).

## Sem garantias

O monitor pode deixar de trazer uma vaga boa, trazer uma ruim ou parar de funcionar. Ele ajuda a
encontrar vagas; não substitui olhar os sites, a rede de contatos e o seu julgamento. A licença
([MIT](../LICENSE)) é **sem garantia**.
