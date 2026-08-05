# Weekend Annoying Task Challenge: YouTube Video Summary

🌐 **Idioma:** [English](README.md) \| **Português**

![YouTube Video Summary](images/01.youtube-video-summary-home.png)

![AWS](https://img.shields.io/badge/AWS-Serverless-orange)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-blue)
![Amazon Nova](https://img.shields.io/badge/Amazon%20Nova-Micro-232F3E)
![AWS Lambda](https://img.shields.io/badge/AWS%20Lambda-Function%20URL-orange)
![AWS Amplify](https://img.shields.io/badge/AWS%20Amplify-Hosting-orange)
![React](https://img.shields.io/badge/React-19-61DAFB)
![Python](https://img.shields.io/badge/Python-3.13-green)
![Licença](https://img.shields.io/badge/License-MIT-yellow)

| Propriedade | Valor |
|---|---|
| Região AWS | `us-east-1` |
| Modelo de IA | Amazon Nova Micro |
| Ambiente de execução | Python 3.13 |
| Frontend | React 19 / Vite 8 |
| Backend | AWS Lambda |
| API | AWS Lambda Function URL |
| Infraestrutura como código | AWS SAM / AWS CloudFormation |
| Provedor de transcrição | Supadata |
| Armazenamento do segredo | AWS Systems Manager Parameter Store |
| Hospedagem | AWS Amplify Hosting |

Aplicação serverless com inteligência artificial criada para o **AWS Weekend Challenge: Turn One Annoying Task into an App**.

O YouTube Video Summary recebe uma URL do YouTube, obtém a transcrição disponível, identifica seu idioma original e usa o Amazon Bedrock para gerar um resumo claro e estruturado no mesmo idioma.

A interface da aplicação está disponível em inglês e português do Brasil. O inglês é selecionado por padrão.

---

## Visão e funcionamento da aplicação

Assistir a um vídeo longo no YouTube antes de saber se ele é útil pode consumir um tempo valioso.

A ideia do **YouTube Video Summary** surgiu a partir dos trailers de filmes. Um trailer ajuda alguém a decidir se vale a pena assistir a um filme de duas horas. Eu queria oferecer o mesmo atalho de decisão para vídeos do YouTube.

Em vez de gastar imediatamente 30 minutos ou mais assistindo a um vídeo, o usuário pode primeiro ler um resumo estruturado e decidir se o conteúdo completo é relevante.

O usuário informa a URL de um vídeo público do YouTube. A aplicação obtém a transcrição disponível, identifica seu idioma e gera um resumo nesse mesmo idioma.

![Página inicial da aplicação YouTube Video Summary](images/03.application-home.png)

A aplicação fornece:

- um resumo conciso;
- os principais pontos;
- uma conclusão;
- o idioma detectado na transcrição;
- a quantidade de caracteres da transcrição;
- uma interface em inglês e português do Brasil.

![Resumo de vídeo do YouTube gerado](images/04.application-summary.png)

---

## Como a aplicação foi construída

Comecei definindo a menor arquitetura capaz de atender ao desafio sem adicionar infraestrutura desnecessária.

O frontend foi desenvolvido com **React 19** e **Vite 8**. Ele é hospedado no **AWS Amplify Hosting** e se comunica com o backend por meio de uma **AWS Lambda Function URL**.

![Implantação de produção no AWS Amplify](images/02.amplify-deployment.png)

O backend foi desenvolvido em **Python 3.13** e implantado com o **AWS SAM**. A função Lambda:

1. valida a requisição HTTP;
2. valida a URL do YouTube;
3. obtém a chave de API da Supadata no AWS Systems Manager Parameter Store;
4. solicita a transcrição pública à Supadata;
5. identifica o idioma da transcrição;
6. invoca o Amazon Nova Micro por meio do Amazon Bedrock;
7. retorna o resumo estruturado e a transcrição ao frontend.

### Principais decisões

Escolhi uma arquitetura serverless para reduzir custos, simplificar a implantação e facilitar a remoção do ambiente após o desafio.

O projeto não utiliza:

- Amazon EC2;
- contêineres;
- Elastic Load Balancing;
- Amazon API Gateway;
- banco de dados;
- armazenamento persistente das transcrições;
- simultaneidade provisionada;
- rastreamento ativo do AWS X-Ray.

O Amazon Nova Micro foi escolhido porque é adequado para resumos de texto e contribui para uma arquitetura de menor custo.

A chave de API da Supadata é armazenada como `SecureString` no AWS Systems Manager Parameter Store, em vez de ser inserida no frontend ou enviada ao GitHub.

![Variáveis de ambiente do AWS Lambda](images/06.lambda-environment-variables.png)

A função de execução da Lambda segue o princípio de privilégio mínimo. Ela pode invocar apenas o modelo Amazon Nova Micro selecionado e obter somente o valor necessário no Parameter Store.

### Desafios e como foram resolvidos

#### Obtenção das legendas do YouTube

O primeiro desafio foi obter legendas públicas de maneira confiável a partir de um backend hospedado na nuvem. Abordagens diretas para obter transcrições podem ser bloqueadas ou restringidas, enquanto o fluxo oficial de legendas do YouTube foi desenvolvido para acesso autorizado.

Resolvi esse problema integrando a [Supadata](https://supadata.ai/) como provedora de transcrições.

#### Retorno dos resumos no idioma correto

Outro desafio era que o modelo nem sempre mantinha o idioma da transcrição de maneira consistente.

Atualizei o prompt do backend para definir:

- o idioma de saída obrigatório;
- os títulos obrigatórios;
- as regras exatas de formatação;
- uma temperatura de inferência baixa;
- os requisitos de saída estruturada.

As transcrições em inglês utilizam:

```text
## Summary
## Key points
## Conclusion
```

As transcrições em português utilizam:

```text
## Resumo
## Principais pontos
## Conclusão
```

#### Conexão do Amplify com o backend

O frontend obtém a Lambda Function URL por meio da variável de ambiente do Amplify:

```text
VITE_API_URL
```

![Variáveis de ambiente do AWS Amplify](images/07.amplify-environment-variables.png)

O CORS da Lambda Function URL é restrito ao domínio de produção do Amplify.

![Configuração de CORS da AWS Lambda Function URL](images/05.lambda-cors.png)

#### Controle do tamanho da requisição e do uso do modelo

O MVP limita as transcrições a:

```text
80.000 caracteres
```

A resposta do Amazon Bedrock é limitada a 1.500 tokens de saída, e a temperatura do modelo está configurada como `0.1` para obter resultados mais consistentes.

---

## Serviços AWS utilizados e visão geral da arquitetura

### Serviços AWS

| Serviço AWS | Finalidade |
|---|---|
| AWS Amplify Hosting | Hospeda e implanta o frontend desenvolvido com React e Vite |
| AWS Lambda | Processa a requisição, obtém a transcrição, invoca o Amazon Bedrock e retorna o resultado |
| AWS Lambda Function URL | Fornece o endpoint HTTPS usado pelo frontend |
| Amazon Bedrock | Fornece inferência de IA generativa por meio da API Converse |
| Amazon Nova Micro | Gera o resumo estruturado do vídeo |
| AWS Systems Manager Parameter Store | Armazena a chave de API da Supadata como `SecureString` |
| AWS Identity and Access Management | Fornece permissões de privilégio mínimo para a função de execução da Lambda |
| AWS CloudFormation e AWS SAM | Definem e implantam a infraestrutura do backend |

### Serviço externo

| Serviço | Finalidade |
|---|---|
| Supadata | Obtém a transcrição pública do YouTube e identifica seu idioma |

### Como a aplicação é acionada

A aplicação é acionada quando o usuário:

1. abre a aplicação React hospedada no AWS Amplify;
2. informa uma URL do YouTube;
3. seleciona **Summarize**.

O navegador envia uma requisição HTTPS `POST` para a Lambda Function URL. Essa requisição invoca a função AWS Lambda.

A função Lambda obtém a transcrição por meio da Supadata, envia o texto ao Amazon Nova Micro por meio do Amazon Bedrock e retorna o resumo gerado ao frontend.

### Fluxo da arquitetura

```text
Usuário
  |
  v
Aplicação web React + Vite
  |
  v
AWS Amplify Hosting
  |
  | HTTPS POST
  v
AWS Lambda Function URL
  |
  v
AWS Lambda
  |
  +--> AWS Systems Manager Parameter Store
  |       Chave de API da Supadata
  |
  +--> Supadata
  |       Transcrição do YouTube e idioma
  |
  +--> Amazon Bedrock
          Resumo gerado pelo Amazon Nova Micro

```

### Diagrama da arquitetura

![Arquitetura AWS do YouTube Video Summary](images/08.aws-architecture.png)

---

## Estrutura do repositório

```text
youtube-video-summary/
├── backend/
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package-lock.json
│   ├── package.json
│   └── vite.config.js
├── images/
├── .gitignore
├── LICENSE
├── README.md
├── README.pt-BR.md
├── samconfig.toml
└── template.yaml
```

A infraestrutura do backend é definida no arquivo `template.yaml` e implantada com o AWS SAM. O frontend é uma aplicação Vite separada, localizada no diretório `frontend`.

---

## Implantação e instalação

> [!IMPORTANT]
> Este projeto cria recursos AWS que podem gerar cobranças. A Lambda Function URL utiliza `AuthType: NONE`, o que torna o endpoint acessível publicamente. Implante a aplicação apenas para testes controlados, restrinja o CORS às origens que você controla e remova o ambiente quando ele não for mais necessário.

### Pré-requisitos

Antes de começar, instale ou prepare:

- uma conta AWS;
- uma identidade de administrador capaz de criar uma política IAM, um usuário IAM e uma chave de acesso;
- [AWS CLI versão 2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html);
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html);
- Git;
- Python 3.13;
- Node.js `20.19+` ou `22.12+`, com npm;
- uma conta no GitHub e permissão para acessar o repositório ou seu fork;
- uma conta no [Supadata](https://supadata.ai/) e obtenha uma chave de API;
- permissão para invocar o Amazon Nova Micro na região `us-east-1`.

O arquivo `samconfig.toml` incluído configura a pilha do CloudFormation como `youtube-video-summary` na região `us-east-1` e habilita a resolução automática do bucket S3 usado na implantação.

### 1. Criar um usuário IAM exclusivo para o projeto

Use uma identidade de administrador para criar um usuário IAM exclusivo chamado:

```text
youtube-video-summary
```

Esse usuário será utilizado apenas nos comandos programáticos de implantação e limpeza deste projeto. Não crie chaves de acesso para o usuário raiz da conta AWS.

> [!NOTE]
> Mantenha a chave de acesso protegida, nunca a envie ao GitHub e exclua a chave e o usuário após remover o projeto.

#### Criar a política gerenciada pelo cliente

1. Abra o Console do AWS Identity and Access Management.
2. Copie o ID de 12 dígitos da sua conta AWS no menu da conta.
3. Abra **Políticas** e selecione **Criar política**.
4. Selecione o editor **JSON**.
5. Cole a política abaixo.
6. Substitua todas as ocorrências de `YOUR_AWS_ACCOUNT_ID` pelo ID de 12 dígitos da sua conta AWS, sem hífens.
7. Crie a política com o nome `YouTubeSummarySamIamDeployment`.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ManageProjectLambdaRole",
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:UpdateAssumeRolePolicy",
                "iam:PutRolePolicy",
                "iam:GetRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:ListRolePolicies",
                "iam:ListAttachedRolePolicies",
                "iam:TagRole",
                "iam:UntagRole"
            ],
            "Resource": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/youtube-video-summary-*"
        },
        {
            "Sid": "AttachProjectRolePolicies",
            "Effect": "Allow",
            "Action": [
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy"
            ],
            "Resource": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/youtube-video-summary-*"
        },
        {
            "Sid": "PassProjectRoleToLambda",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:role/youtube-video-summary-*",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "lambda.amazonaws.com"
                }
            }
        },
        {
            "Sid": "ReadDeploymentPolicy",
            "Effect": "Allow",
            "Action": [
                "iam:GetPolicy",
                "iam:GetPolicyVersion",
                "iam:ListPolicyVersions"
            ],
            "Resource": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:policy/YouTubeSummarySamIamDeployment"
        },
        {
            "Sid": "ViewOwnUserPolicies",
            "Effect": "Allow",
            "Action": [
                "iam:GetUser",
                "iam:ListAttachedUserPolicies",
                "iam:ListUserPolicies",
                "iam:GetUserPolicy",
                "iam:ListGroupsForUser"
            ],
            "Resource": "arn:aws:iam::YOUR_AWS_ACCOUNT_ID:user/youtube-video-summary"
        },
        {
            "Sid": "ReadCloudTrailDeploymentEvents",
            "Effect": "Allow",
            "Action": "cloudtrail:LookupEvents",
            "Resource": "*"
        }
    ]
}
```

#### Criar o usuário IAM e anexar as políticas

1. No console do IAM, abra **Usuários** e selecione **Criar usuário**.
2. Informe `youtube-video-summary` como nome do usuário.
3. Não habilite o acesso ao Console de Gerenciamento da AWS para esse usuário.
4. Em permissões, selecione **Anexar políticas diretamente**.
5. Anexe a política gerenciada pela AWS `PowerUserAccess`.
6. Anexe a política gerenciada pelo cliente `YouTubeSummarySamIamDeployment`.
7. Crie o usuário.
8. Abra o novo usuário e selecione **Credenciais de segurança**.
9. Em **Chaves de acesso**, selecione **Criar chave de acesso**.
10. Selecione **Interface de linha de comando (CLI)** como caso de uso.
11. Crie a chave e salve com segurança o **ID da chave de acesso** e a **Chave de acesso secreta**. A chave secreta é exibida apenas uma vez.

A política `PowerUserAccess` fornece acesso amplo aos serviços e recursos AWS, mas não fornece as permissões IAM necessárias para gerenciar a função de execução da Lambda deste projeto. A política `YouTubeSummarySamIamDeployment` fornece apenas as ações IAM adicionais utilizadas por esta implantação do AWS SAM.

### 2. Configurar o profile da AWS CLI para o projeto

Configure um profile nomeado com a chave de acesso criada para o usuário exclusivo:

```bash
aws configure --profile youtube-video-summary
```

Informe:

```text
AWS Access Key ID: YOUR_ACCESS_KEY_ID
AWS Secret Access Key: YOUR_SECRET_ACCESS_KEY
Default region name: us-east-1
Default output format: json
```

Confirme a identidade configurada:

```bash
aws sts get-caller-identity --profile youtube-video-summary
```

Verifique se o ARN retornado contém `user/youtube-video-summary` e se o ID da conta está correto. Os comandos da AWS CLI e do AWS SAM apresentados neste guia informam explicitamente esse profile ao acessar a AWS.

### 3. Criar um fork e clonar o repositório

Crie um fork deste repositório em sua conta do GitHub. Em seguida, clone o seu fork, substituindo SEU_USUARIO pelo seu nome de usuário no GitHub:

```bash
git clone https://github.com/SEU_USUARIO/youtube-video-summary.git
cd youtube-video-summary
```

Confirme que o repositório remoto aponta para o seu fork:

```bash
git remote -v
```

O endereço exibido como origin deverá conter o seu nome de usuário do GitHub.

### 4. Criar uma conta na Supadata e armazenar a chave de API

Esta aplicação utiliza a Supadata para obter a transcrição pública do vídeo do YouTube antes de enviar o texto ao Amazon Bedrock. Crie uma conta na [Supadata](https://supadata.ai/), copie a chave de API da sua conta e armazene-a no AWS Systems Manager Parameter Store:

```bash
aws ssm put-parameter \
  --name "/youtube-summary/supadata-api-key" \
  --value "YOUR_SUPADATA_API_KEY" \
  --type "SecureString" \
  --region "us-east-1" \
  --profile youtube-video-summary
```

Substitua `YOUR_SUPADATA_API_KEY` pela sua chave de API da Supadata. O parâmetro deve existir na região `us-east-1`. Para substituir um valor existente, repita o comando adicionando `--overwrite`.

> [!NOTE]
> Não envie a chave de API da Supadata ao repositório e não a exponha por meio de uma variável de ambiente do Vite.

### 5. Configurar o CORS para o desenvolvimento local

Antes de implantar sua cópia, abra o arquivo `template.yaml` e substitua o domínio atual do Amplify em `AllowOrigins` pela origem local do Vite:

```yaml
Cors:
  AllowOrigins:
    - "http://localhost:5173"
  AllowMethods:
    - POST
  AllowHeaders:
    - content-type
  MaxAge: 600
```

Caso o Vite seja iniciado em outra porta, utilize a origem exata exibida pelo comando `npm run dev`.

### 6. Validar e compilar o backend

Na raiz do repositório, execute:

```bash
sam validate --lint
sam build
```

A opção `--lint` valida o template do AWS SAM com o CloudFormation Linter. A saída da compilação é criada em `.aws-sam/`, que está excluído do Git.

### 7. Implantar o backend

Implante a aplicação:

```bash
sam deploy \
  --stack-name youtube-video-summary \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --profile youtube-video-summary
```

Revise o conjunto de alterações do CloudFormation e confirme a implantação quando solicitado. O AWS SAM cria ou atualiza a pilha `youtube-video-summary` do CloudFormation.

### 8. Obter a Lambda Function URL

Após a conclusão da implantação, obtenha o endpoint a partir da saída do CloudFormation:

```bash
FUNCTION_URL=$(aws cloudformation describe-stacks \
  --stack-name "youtube-video-summary" \
  --region "us-east-1" \
  --query "Stacks[0].Outputs[?OutputKey=='VideoSummaryFunctionUrl'].OutputValue" \
  --output text \
  --profile youtube-video-summary)

echo "$FUNCTION_URL"
```

O valor deverá seguir este formato:

```text
https://<url-id>.lambda-url.us-east-1.on.aws/
```

### 9. Instalar e executar o frontend localmente

Entre no diretório do frontend e crie um arquivo de ambiente local:

```bash
cd frontend
printf 'VITE_API_URL=%s\n' "$FUNCTION_URL" > .env.local
```

Instale as versões exatas das dependências definidas em `package-lock.json` e inicie o Vite:

```bash
npm ci
npm run dev
```

Abra o endereço local exibido pelo Vite, normalmente:

```text
http://localhost:5173
```

Após o teste, pressione `Ctrl+C` no terminal para encerrar o servidor local.

O arquivo `.env.local` está excluído do Git e não deve conter segredos. `VITE_API_URL` é um endpoint público da aplicação, não uma credencial.

### 10. Testar diretamente o backend implantado

Também é possível enviar uma requisição diretamente pelo terminal. Este teste é opcional e serve para verificar o backend sem utilizar o frontend.

```bash
curl -sS -X POST "$FUNCTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Substitua `VIDEO_ID` pelo ID de um vídeo público do YouTube que tenha uma transcrição disponível.

### 11. Implantar o frontend com o AWS Amplify Hosting

Envie as alterações feitas localmente para o seu fork no GitHub:

```bash
git add . 
git commit -m "Configure the application for deployment" 
git push origin main
```

Em seguida, acesse o Console de Gerenciamento da AWS com uma identidade que tenha permissão para criar e configurar aplicações no AWS Amplify Hosting:

1. abra o console do AWS Amplify na região `us-east-1`;
2. selecione **Criar novo aplicativo**;
3. escolha GitHub como provedor do repositório e selecione Avançar;
4. autorize o AWS Amplify a acessar a sua conta do GitHub;
5. selecione o seu fork e a branch main;
6. indique que o repositório é um monorepo;
7. defina a raiz da aplicação como `frontend`;
8. adicione a variável de ambiente `VITE_API_URL` com a Lambda Function URL;
9. crie a aplicação;
10. abra **Hospedagem**, selecione **Configurações de compilação** e escolha **Editar**;
11. substitua a especificação de compilação pela configuração abaixo;
12. salve as configurações e inicie uma nova implantação.

```yaml
version: 1
applications:
  - frontend:
      phases:
        preBuild:
          commands:
            - npm ci --cache .npm --prefer-offline
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: dist
        files:
          - '**/*'
      cache:
        paths:
          - .npm/**/*
    appRoot: frontend
```

Essa especificação de compilação é configurada diretamente no AWS Amplify Hosting e não precisa ser armazenada como um arquivo `amplify.yml` no repositório.

As variáveis de ambiente do Amplify ficam disponíveis durante a compilação. Como o Vite incorpora `VITE_API_URL` ao frontend, inicie uma nova implantação no Amplify após alterar o valor dessa variável.

### 12. Restringir o CORS ao domínio do Amplify

Depois que o Amplify fornecer o domínio de produção, retorne ao arquivo `template.yaml` e substitua a origem local pelo seu domínio do Amplify:

```yaml
Cors:
  AllowOrigins:
    - "https://YOUR_BRANCH.YOUR_APP_ID.amplifyapp.com"
  AllowMethods:
    - POST
  AllowHeaders:
    - content-type
  MaxAge: 600
```

Para manter o acesso local e de produção durante o desenvolvimento, inclua as duas origens exatas:

```yaml
AllowOrigins:
  - "http://localhost:5173"
  - "https://YOUR_BRANCH.YOUR_APP_ID.amplifyapp.com"
```

Retorne à raiz do repositório e implante a atualização do CORS:

```bash
cd ..
sam validate --lint
sam build
sam deploy \
  --stack-name youtube-video-summary \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --profile youtube-video-summary
```

Após confirmar que a atualização foi implantada corretamente, envie a configuração de produção para o seu fork:

```bash
git add template.yaml
git commit -m "Restrict CORS to the Amplify domain"
git push origin main
```

Não utilize `*` em uma implantação pública. O CORS restringe as origens dos navegadores, mas não autentica os clientes nem impede requisições diretas à Function URL pública.

### 13. Testar a aplicação em produção

Abra o domínio do Amplify e confirme se:

- a página é carregada corretamente;
- uma URL válida do YouTube gera um resumo;
- o resumo utiliza o idioma da transcrição;
- URLs inválidas exibem uma mensagem de erro;
- requisições provenientes de uma origem não autorizada no navegador são bloqueadas pelo CORS.

---

## Atualização da aplicação

### Alterações no backend ou na infraestrutura

Utilize este fluxo após alterar:

- `backend/app.py`;
- `backend/requirements.txt`;
- `template.yaml`;
- `samconfig.toml`.

Na raiz do repositório, execute:

```bash
sam validate --lint
sam build
sam deploy \
  --stack-name youtube-video-summary \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --profile youtube-video-summary
```

A implantação atualiza a pilha existente `youtube-video-summary` do CloudFormation.

### Alterações no frontend

Arquivos como `frontend/src/App.jsx`, `frontend/src/App.css` e outros arquivos dentro de `frontend/` não são implantados pelo AWS SAM.

Teste uma alteração no frontend localmente:

```bash
cd frontend
npm ci
npm run dev
```

Após confirmar a alteração, retorne à raiz do repositório, faça o commit e envie a alteração para a branch do GitHub conectada ao AWS Amplify:

```bash
cd ..
git add frontend
git commit -m "Update frontend"
git push
```

O AWS Amplify compila e implanta automaticamente a branch conectada quando as compilações automáticas estão habilitadas. Não é necessário executar `sam build` ou `sam deploy` quando apenas o arquivo `App.jsx` ou outro arquivo do frontend for alterado.

Não envie o arquivo `frontend/.env.local` ao repositório. Caso `VITE_API_URL` seja alterada, atualize seu valor nas variáveis de ambiente do AWS Amplify e inicie uma nova implantação.

---

## Limpeza

Remova o ambiente quando ele não for mais necessário. Mantenha o usuário IAM exclusivo ativo até que todos os comandos de limpeza pela CLI sejam concluídos.

### 1. Excluir a aplicação do AWS SAM

Na raiz do repositório, execute:

```bash
sam delete \
  --stack-name "youtube-video-summary" \
  --region "us-east-1" \
  --profile youtube-video-summary
```

Confirme a exclusão quando solicitado.

O AWS SAM exclui a pilha `youtube-video-summary` do CloudFormation e os recursos gerenciados por ela, incluindo a função Lambda, a Lambda Function URL e a função de execução da Lambda. Não exclua novamente a mesma pilha da aplicação no console do AWS CloudFormation.

### 2. Excluir a aplicação do AWS Amplify

No console do AWS Amplify:

1. abra a aplicação;
2. abra as configurações da aplicação;
3. selecione **Excluir aplicativo**;
4. confirme a exclusão.

Isso remove o frontend hospedado e seu domínio do Amplify.

### 3. Excluir o parâmetro da Supadata

```bash
aws ssm delete-parameter \
  --name "/youtube-summary/supadata-api-key" \
  --region "us-east-1" \
  --profile youtube-video-summary
```

### 4. Excluir o usuário IAM e a política exclusivos

Após excluir os recursos da aplicação, acesse a conta com a identidade de administrador usada para criar o usuário do projeto.

No console do IAM:

1. abra **Usuários** e selecione `youtube-video-summary`;
2. exclua sua chave de acesso;
3. desanexe `PowerUserAccess` e `YouTubeSummarySamIamDeployment`;
4. exclua o usuário `youtube-video-summary`;
5. abra **Políticas** e exclua `YouTubeSummarySamIamDeployment`.

> [!NOTE]
> O AWS SAM pode criar uma pilha compartilhada do CloudFormation chamada `aws-sam-cli-managed-default` para os artefatos de implantação. Ela é separada da pilha da aplicação `youtube-video-summary`. Mantenha essa pilha caso outros projetos do AWS SAM a utilizem ou caso pretenda realizar novas implantações com o AWS SAM. Exclua-a somente após confirmar que ela não é mais necessária para outro projeto.

---

## O que aprendi

Este desafio reforçou a importância de começar com a menor arquitetura necessária para resolver o problema.

Aprendi como:

- implantar um backend em Python com o AWS SAM;
- expor uma função Lambda por meio de uma Lambda Function URL;
- conectar um frontend hospedado no AWS Amplify a um backend serverless;
- configurar corretamente o CORS de produção;
- armazenar com segurança uma chave de API externa no Parameter Store;
- aplicar permissões de privilégio mínimo no IAM;
- invocar o Amazon Nova Micro por meio da API Converse do Amazon Bedrock;
- controlar a saída do modelo usando regras de idioma, títulos fixos, limites de tokens e temperatura baixa;
- desenvolver uma aplicação que não exige banco de dados;
- equilibrar simplicidade, segurança, custo e usabilidade em um projeto de fim de semana.

Também aprendi que a menor arquitetura funcional nem sempre é a primeira arquitetura considerada. Vários serviços e recursos foram removidos intencionalmente porque não eram necessários para o MVP.

O resultado final é uma aplicação serverless focada em resolver uma tarefa repetitiva: decidir se vale a pena assistir a um vídeo do YouTube antes de investir tempo para assisti-lo.

---

## Licença

Este projeto está licenciado sob a Licença MIT. Consulte o arquivo [LICENSE](LICENSE) para obter mais informações.
