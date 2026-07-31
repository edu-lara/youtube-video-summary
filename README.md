# Weekend Annoying Task Challenge: YouTube Video Summary

🌐 **Language:** **English** \| [Português](README.pt-BR.md)

![YouTube Video Summary](images/01.youtube-video-summary-home.png)

![AWS](https://img.shields.io/badge/AWS-Serverless-orange)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-blue)
![Amazon Nova](https://img.shields.io/badge/Amazon%20Nova-Micro-232F3E)
![AWS Lambda](https://img.shields.io/badge/AWS%20Lambda-Function%20URL-orange)
![AWS Amplify](https://img.shields.io/badge/AWS%20Amplify-Hosting-orange)
![React](https://img.shields.io/badge/React-19-61DAFB)
![Python](https://img.shields.io/badge/Python-3.13-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

| Property | Value |
|---|---|
| AWS Region | `us-east-1` |
| AI Model | Amazon Nova Micro |
| Runtime | Python 3.13 |
| Frontend | React 19 / Vite 8 |
| Backend | AWS Lambda |
| API | AWS Lambda Function URL |
| Infrastructure as Code | AWS SAM / AWS CloudFormation |
| Transcript Provider | Supadata |
| Secret Storage | AWS Systems Manager Parameter Store |
| Hosting | AWS Amplify Hosting |

AI-powered serverless application built for the **AWS Weekend Challenge: Turn One Annoying Task into an App**.

YouTube Video Summary accepts a YouTube URL, retrieves the available transcript, identifies its original language, and uses Amazon Bedrock to generate a clear, structured summary in that same language.

The interface is available in English and Brazilian Portuguese. English is selected by default.

> [!NOTE]
> The production environment is temporary and will be removed after the challenge publication to avoid unnecessary AWS costs.

---

## Vision & What the App Does

Watching a long YouTube video before knowing whether it is useful can waste valuable time.

The idea for **YouTube Video Summary** came from movie trailers. A trailer helps someone decide whether a two-hour movie is worth watching. I wanted the same decision shortcut for YouTube videos.

Instead of immediately spending 30 minutes or more watching a video, the user can first read a structured summary and decide whether the full content is relevant.

The user pastes a public YouTube URL. The application retrieves the available transcript, identifies its language, and generates a summary in that same language.

The application provides:

- a concise summary;
- the main points;
- a conclusion;
- the detected transcript language;
- the transcript character count;
- access to the complete transcript;
- an interface in English and Brazilian Portuguese.

---

## How I Built It

I started by defining the smallest architecture that could satisfy the challenge without adding unnecessary infrastructure.

The frontend was built with **React 19** and **Vite 8**. It is hosted with **AWS Amplify Hosting** and communicates with the backend through an **AWS Lambda Function URL**.

The backend was developed in **Python 3.13** and deployed with **AWS SAM**. The Lambda function:

1. validates the HTTP request;
2. validates the YouTube URL;
3. retrieves the Supadata API key from AWS Systems Manager Parameter Store;
4. requests the public transcript from Supadata;
5. identifies the transcript language;
6. invokes Amazon Nova Micro through Amazon Bedrock;
7. returns the structured summary and transcript to the frontend.

### Key decisions

I chose a serverless architecture to reduce cost, simplify deployment, and make the environment easy to remove after the challenge.

The project does not use:

- Amazon EC2;
- containers;
- Elastic Load Balancing;
- Amazon API Gateway;
- a database;
- persistent transcript storage;
- provisioned concurrency;
- active AWS X-Ray tracing.

Amazon Nova Micro was selected because it is appropriate for text summarization and supports a lower-cost architecture.

The Supadata API key is stored as a `SecureString` in AWS Systems Manager Parameter Store instead of being placed in the frontend or committed to GitHub.

The Lambda execution role follows least-privilege principles. It can invoke only the selected Amazon Nova Micro model and retrieve only the required Parameter Store value.

### Challenges and how I solved them

#### Retrieving YouTube captions

The first challenge was obtaining public captions reliably from a cloud-hosted backend. Direct transcript approaches can be blocked or restricted, while the official YouTube captions workflow is designed around authorized access.

I solved this by integrating Supadata as the transcript provider.

#### Returning summaries in the correct language

The model did not always preserve the transcript language consistently.

I updated the backend prompt to define:

- the mandatory output language;
- mandatory headings;
- exact formatting rules;
- low inference temperature;
- structured output requirements.

English transcripts now use:

```text
## Summary
## Key points
## Conclusion
```

Portuguese transcripts use:

```text
## Resumo
## Principais pontos
## Conclusão
```

#### Connecting Amplify to the backend

The frontend reads the Lambda Function URL from the Amplify environment variable:

```text
VITE_API_URL
```

CORS on the Lambda Function URL is restricted to the production Amplify domain.

#### Controlling request size and model usage

The MVP limits transcripts to:

```text
80,000 characters
```

The Amazon Bedrock response is limited to 1,500 output tokens, and the model temperature is set to `0.1` for more consistent results.

---

## AWS Services Used / Architecture Overview

### AWS services

| AWS Service | Purpose |
|---|---|
| AWS Amplify Hosting | Hosts and deploys the React and Vite frontend |
| AWS Lambda | Processes the request, retrieves the transcript, invokes Amazon Bedrock, and returns the result |
| AWS Lambda Function URL | Provides the HTTPS endpoint used by the frontend |
| Amazon Bedrock | Provides generative AI inference through the Converse API |
| Amazon Nova Micro | Generates the structured video summary |
| AWS Systems Manager Parameter Store | Stores the Supadata API key as a `SecureString` |
| Amazon CloudWatch Logs | Stores Lambda execution logs |
| AWS Identity and Access Management | Provides least-privilege permissions for the Lambda execution role |
| AWS CloudFormation and AWS SAM | Define and deploy the backend infrastructure |

### External service

| Service | Purpose |
|---|---|
| Supadata | Retrieves the public YouTube transcript and identifies its language |

### How the application is triggered

The application is triggered when the user:

1. opens the React application hosted on AWS Amplify;
2. enters a YouTube URL;
3. selects **Summarize**.

The browser sends an HTTPS `POST` request to the Lambda Function URL. This request invokes the AWS Lambda function.

The Lambda function retrieves the transcript through Supadata, sends it to Amazon Nova Micro through Amazon Bedrock, and returns the generated summary to the frontend.

### Architecture flow

```text
User
  |
  v
React + Vite web application
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
  |       Supadata API key
  |
  +--> Supadata
  |       YouTube transcript and language
  |
  +--> Amazon Bedrock
          Amazon Nova Micro summary

AWS Lambda
  |
  v
Amazon CloudWatch Logs
```

### Architecture diagram

![YouTube Video Summary AWS Architecture](images/08.aws-architecture.png)

---

## What I Learned

This challenge reinforced the importance of starting with the minimum architecture required to solve the problem.

I learned how to:

- deploy a Python backend with AWS SAM;
- expose a Lambda function through a Lambda Function URL;
- connect an AWS Amplify frontend to a serverless backend;
- configure production CORS correctly;
- store an external API key securely in Parameter Store;
- apply least-privilege IAM permissions;
- invoke Amazon Nova Micro through the Amazon Bedrock Converse API;
- control model output using language rules, fixed headings, token limits, and low temperature;
- design an application that does not require a database;
- balance simplicity, security, cost, and usability in a weekend project.

I also learned that the smallest working architecture is not always the first architecture considered. Several services and features were intentionally removed because they were not required for the MVP.

The final result is a focused serverless application that solves one repetitive task: deciding whether a YouTube video is worth watching before investing the time to watch it.

---

## Link to Repo

[edu-lara/youtube-video-summary](https://github.com/edu-lara/youtube-video-summary)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
